"""
Smart scheduler service for outreach automation.
Implements intelligent scheduling, rate limiting, and anti-detection strategies.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class ActionType(StrEnum):
    """Types of outreach actions."""
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    DM = "dm"
    LIKE = "like"
    COMMENT = "comment"
    VIEW_PROFILE = "view_profile"
    SCROLL = "scroll"


class AccountAgeCategory(StrEnum):
    """Sub-account age categories for warming strategy."""
    NEW = "new"        # < 7 days
    WARMING = "warming"  # 7-30 days
    MATURE = "mature"    # > 30 days


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for an action type."""
    action_type: ActionType
    hourly_limit: int
    daily_limit: int
    min_interval_seconds: int
    max_interval_seconds: int
    # Adjust limits based on account age
    new_account_multiplier: float = 0.3
    warming_account_multiplier: float = 0.6

    def get_limit_for_age(self, age_category: AccountAgeCategory, period: str = "daily") -> int:
        """Get adjusted limit based on account age."""
        base = self.daily_limit if period == "daily" else self.hourly_limit
        if age_category == AccountAgeCategory.NEW:
            return int(base * self.new_account_multiplier)
        elif age_category == AccountAgeCategory.WARMING:
            return int(base * self.warming_account_multiplier)
        return base

    def get_random_interval(self) -> int:
        """Get random delay between actions."""
        return random.randint(self.min_interval_seconds, self.max_interval_seconds)  # noqa: S311


@dataclass
class ScheduledAction:
    """A scheduled outreach action."""
    id: str
    action_type: ActionType
    account_id: str
    target_id: str
    scheduled_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    executed_at: datetime | None = None
    status: str = "pending"  # pending, executing, completed, failed, cancelled
    error_message: str | None = None


@dataclass
class AccountScheduleState:
    """Scheduling state for a sub-account."""
    account_id: str
    age_category: AccountAgeCategory
    timezone: str = "UTC"
    # Current counters
    hourly_actions: dict[ActionType, int] = field(default_factory=dict)
    daily_actions: dict[ActionType, int] = field(default_factory=dict)
    last_action_at: dict[ActionType, datetime] = field(default_factory=dict)
    # Reset times
    hourly_reset_at: datetime = field(default_factory=datetime.now)
    daily_reset_at: datetime = field(default_factory=datetime.now)
    # Cooling state
    is_cooling: bool = False
    cooling_until: datetime | None = None
    cooling_reason: str | None = None

    def get_next_available_time(
        self, action_type: ActionType, config: RateLimitConfig
    ) -> datetime:
        """Calculate next available time for an action."""
        now = datetime.now()
        # Check if account is cooling
        if self.is_cooling and self.cooling_until and self.cooling_until > now:
            return self.cooling_until
        # Check last action time for interval
        last_action = self.last_action_at.get(action_type)
        if last_action:
            min_next = last_action + timedelta(seconds=config.min_interval_seconds)
            if min_next > now:
                return min_next
        return now


class SmartSchedulerService:
    """
    Intelligent scheduler for outreach automation.
    Implements anti-detection strategies and rate limiting.
    """

    # Default rate limits per platform
    DEFAULT_LIMITS = {
        "instagram": {
            ActionType.FOLLOW: RateLimitConfig(
                ActionType.FOLLOW, hourly_limit=20, daily_limit=100,
                min_interval_seconds=60, max_interval_seconds=300,
            ),
            ActionType.UNFOLLOW: RateLimitConfig(
                ActionType.UNFOLLOW, hourly_limit=30, daily_limit=150,
                min_interval_seconds=30, max_interval_seconds=120,
            ),
            ActionType.DM: RateLimitConfig(
                ActionType.DM, hourly_limit=10, daily_limit=50,
                min_interval_seconds=120, max_interval_seconds=600,
            ),
            ActionType.LIKE: RateLimitConfig(
                ActionType.LIKE, hourly_limit=50, daily_limit=300,
                min_interval_seconds=10, max_interval_seconds=60,
            ),
        },
        "x": {
            ActionType.FOLLOW: RateLimitConfig(
                ActionType.FOLLOW, hourly_limit=30, daily_limit=200,
                min_interval_seconds=30, max_interval_seconds=180,
            ),
            ActionType.DM: RateLimitConfig(
                ActionType.DM, hourly_limit=20, daily_limit=100,
                min_interval_seconds=60, max_interval_seconds=300,
            ),
            ActionType.LIKE: RateLimitConfig(
                ActionType.LIKE, hourly_limit=100, daily_limit=500,
                min_interval_seconds=5, max_interval_seconds=30,
            ),
        },
    }

    # Work hours by timezone (localized working hours)
    WORK_HOURS = {"start": 8, "end": 22}  # 8 AM to 10 PM local time

    def __init__(self):
        self._account_states: dict[str, AccountScheduleState] = {}
        self._action_queue: list[ScheduledAction] = []
        self._rate_limits: dict[str, dict[ActionType, RateLimitConfig]] = dict(self.DEFAULT_LIMITS)

    def register_account(
        self,
        account_id: str,
        created_at: datetime | None = None,
        timezone: str = "UTC",
    ) -> AccountScheduleState:
        """Register a sub-account for scheduling."""
        age_category = self._calculate_age_category(created_at)
        state = AccountScheduleState(
            account_id=account_id,
            age_category=age_category,
            timezone=timezone,
        )
        self._account_states[account_id] = state
        logger.info("Registered account %s (age: %s)", account_id, age_category)
        return state

    def _calculate_age_category(self, created_at: datetime | None) -> AccountAgeCategory:
        """Calculate account age category."""
        if not created_at:
            return AccountAgeCategory.MATURE
        age_days = (datetime.now() - created_at).days
        if age_days < 7:
            return AccountAgeCategory.NEW
        elif age_days < 30:
            return AccountAgeCategory.WARMING
        return AccountAgeCategory.MATURE

    def get_account_state(self, account_id: str) -> AccountScheduleState | None:
        """Get scheduling state for an account."""
        return self._account_states.get(account_id)

    def can_execute_action(
        self,
        account_id: str,
        action_type: ActionType,
        platform: str = "instagram",
    ) -> tuple[bool, str | None]:
        """Check if an account can execute an action now."""
        state = self._account_states.get(account_id)
        if not state:
            return False, "Account not registered"

        now = datetime.now()

        # Check cooling status
        if state.is_cooling:
            if state.cooling_until and state.cooling_until > now:
                return False, f"Account cooling until {state.cooling_until}"
            state.is_cooling = False
            state.cooling_until = None

        # Get rate limit config
        limits = self._rate_limits.get(platform, {})
        config = limits.get(action_type)
        if not config:
            return True, None  # No limit configured

        # Reset counters if needed
        self._reset_counters_if_needed(state, now)

        # Check hourly limit
        hourly_count = state.hourly_actions.get(action_type, 0)
        hourly_limit = config.get_limit_for_age(state.age_category, "hourly")
        if hourly_count >= hourly_limit:
            return False, f"Hourly limit reached ({hourly_count}/{hourly_limit})"

        # Check daily limit
        daily_count = state.daily_actions.get(action_type, 0)
        daily_limit = config.get_limit_for_age(state.age_category, "daily")
        if daily_count >= daily_limit:
            return False, f"Daily limit reached ({daily_count}/{daily_limit})"

        # Check minimum interval
        last_action = state.last_action_at.get(action_type)
        if last_action:
            elapsed = (now - last_action).total_seconds()
            if elapsed < config.min_interval_seconds:
                return False, f"Min interval not met ({elapsed:.0f}s < {config.min_interval_seconds}s)"

        return True, None

    def _reset_counters_if_needed(self, state: AccountScheduleState, now: datetime) -> None:
        """Reset hourly/daily counters if time window passed."""
        # Reset hourly
        if now >= state.hourly_reset_at + timedelta(hours=1):
            state.hourly_actions = {}
            state.hourly_reset_at = now.replace(minute=0, second=0, microsecond=0)

        # Reset daily
        if now >= state.daily_reset_at + timedelta(days=1):
            state.daily_actions = {}
            state.daily_reset_at = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def record_action(
        self,
        account_id: str,
        action_type: ActionType,
        success: bool = True,
    ) -> None:
        """Record an executed action to update counters."""
        state = self._account_states.get(account_id)
        if not state:
            return

        now = datetime.now()
        state.last_action_at[action_type] = now

        if success:
            state.hourly_actions[action_type] = state.hourly_actions.get(action_type, 0) + 1
            state.daily_actions[action_type] = state.daily_actions.get(action_type, 0) + 1

    def set_account_cooling(
        self,
        account_id: str,
        duration_minutes: int = 30,
        reason: str | None = None,
    ) -> None:
        """Put an account in cooling mode."""
        state = self._account_states.get(account_id)
        if state:
            state.is_cooling = True
            state.cooling_until = datetime.now() + timedelta(minutes=duration_minutes)
            state.cooling_reason = reason
            logger.warning("Account %s set to cooling for %smin: %s", account_id, duration_minutes, reason)

    def get_recommended_delay(
        self,
        action_type: ActionType,
        platform: str = "instagram",
    ) -> int:
        """Get recommended random delay for an action."""
        limits = self._rate_limits.get(platform, {})
        config = limits.get(action_type)
        if config:
            return config.get_random_interval()
        return random.randint(30, 120)  # noqa: S311

    def schedule_action(
        self,
        action_id: str,
        action_type: ActionType,
        account_id: str,
        target_id: str,
        payload: dict[str, Any] | None = None,
        scheduled_at: datetime | None = None,
        priority: int = 0,
    ) -> ScheduledAction:
        """Schedule an action for later execution."""
        if not scheduled_at:
            scheduled_at = datetime.now()

        action = ScheduledAction(
            id=action_id,
            action_type=action_type,
            account_id=account_id,
            target_id=target_id,
            scheduled_at=scheduled_at,
            payload=payload or {},
            priority=priority,
        )
        self._action_queue.append(action)
        # Sort by priority (desc) and scheduled time (asc)
        self._action_queue.sort(key=lambda a: (-a.priority, a.scheduled_at))
        return action

    def get_pending_actions(
        self,
        account_id: str | None = None,
        action_type: ActionType | None = None,
        limit: int = 100,
    ) -> list[ScheduledAction]:
        """Get pending actions from the queue."""
        now = datetime.now()
        actions = [
            a for a in self._action_queue
            if a.status == "pending" and a.scheduled_at <= now
        ]
        if account_id:
            actions = [a for a in actions if a.account_id == account_id]
        if action_type:
            actions = [a for a in actions if a.action_type == action_type]
        return actions[:limit]

    def is_within_work_hours(self, timezone: str = "UTC") -> bool:
        """Check if current time is within work hours for a timezone."""
        try:
            tz = ZoneInfo(timezone)
            local_now = datetime.now(tz)
            return self.WORK_HOURS["start"] <= local_now.hour < self.WORK_HOURS["end"]
        except Exception:
            return True

    def get_next_work_window_start(self, timezone: str = "UTC") -> datetime:
        """Get the start of the next work window for a timezone."""
        try:
            tz = ZoneInfo(timezone)
            local_now = datetime.now(tz)
            if local_now.hour >= self.WORK_HOURS["end"]:
                # Next day
                next_start = local_now.replace(
                    hour=self.WORK_HOURS["start"], minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
            elif local_now.hour < self.WORK_HOURS["start"]:
                # Today
                next_start = local_now.replace(
                    hour=self.WORK_HOURS["start"], minute=0, second=0, microsecond=0
                )
            else:
                # Already in work hours
                return datetime.now()
            return next_start.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        except Exception:
            return datetime.now()

    def add_humanization_actions(
        self,
        account_id: str,
        main_action: ScheduledAction,
    ) -> list[ScheduledAction]:
        """Add humanization actions before/after main action."""
        humanization_actions = []
        base_time = main_action.scheduled_at

        # Add scroll/view actions before main action
        scroll_action = ScheduledAction(
            id=f"{main_action.id}_pre_scroll",
            action_type=ActionType.SCROLL,
            account_id=account_id,
            target_id=main_action.target_id,
            scheduled_at=base_time - timedelta(seconds=random.randint(5, 15)),  # noqa: S311
            priority=main_action.priority - 1,
        )
        humanization_actions.append(scroll_action)

        # Maybe add a view_profile action
        if random.random() < 0.7:  # noqa: S311 - non-cryptographic use
            view_action = ScheduledAction(
                id=f"{main_action.id}_pre_view",
                action_type=ActionType.VIEW_PROFILE,
                account_id=account_id,
                target_id=main_action.target_id,
                scheduled_at=base_time - timedelta(seconds=random.randint(2, 8)),  # noqa: S311
                priority=main_action.priority - 1,
            )
            humanization_actions.append(view_action)

        return humanization_actions

    def get_account_stats(self, account_id: str, platform: str = "instagram") -> dict[str, Any]:
        """Get scheduling stats for an account."""
        state = self._account_states.get(account_id)
        if not state:
            return {"error": "Account not registered"}

        limits = self._rate_limits.get(platform, {})
        stats: dict[str, Any] = {
            "account_id": account_id,
            "age_category": state.age_category,
            "is_cooling": state.is_cooling,
            "cooling_until": state.cooling_until.isoformat() if state.cooling_until else None,
            "actions": {},
        }

        for action_type in ActionType:
            config = limits.get(action_type)
            if config:
                hourly_limit = config.get_limit_for_age(state.age_category, "hourly")
                daily_limit = config.get_limit_for_age(state.age_category, "daily")
                stats["actions"][action_type.value] = {
                    "hourly_used": state.hourly_actions.get(action_type, 0),
                    "hourly_limit": hourly_limit,
                    "daily_used": state.daily_actions.get(action_type, 0),
                    "daily_limit": daily_limit,
                }

        return stats


def create_smart_scheduler_service() -> SmartSchedulerService:
    """Factory function to create SmartSchedulerService."""
    return SmartSchedulerService()
