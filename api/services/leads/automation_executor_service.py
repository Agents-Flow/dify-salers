"""
Automation executor service for outreach operations.
Orchestrates follow, unfollow, DM, and engagement actions with anti-detection measures.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class ExecutionStatus(StrEnum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    ACCOUNT_BLOCKED = "account_blocked"


class ActionResult(StrEnum):
    """Individual action result."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RATE_LIMITED = "rate_limited"
    TARGET_NOT_FOUND = "target_not_found"
    ALREADY_FOLLOWING = "already_following"
    PRIVATE_ACCOUNT = "private_account"


@dataclass
class ExecutionContext:
    """Context for task execution."""
    account_id: str
    profile_id: str  # Anti-detect browser profile
    proxy_config: dict[str, Any] | None = None
    ws_endpoint: str | None = None  # Browser WebSocket endpoint
    platform: str = "instagram"
    session_started_at: datetime | None = None


@dataclass
class ActionLog:
    """Log entry for an executed action."""
    id: str
    action_type: str
    target_id: str
    result: ActionResult
    executed_at: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchExecutionResult:
    """Result of a batch execution."""
    task_id: str
    total_actions: int
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    rate_limited: int = 0
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    action_logs: list[ActionLog] = field(default_factory=list)
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "total_actions": self.total_actions,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "rate_limited": self.rate_limited,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success_rate": self.successful / self.total_actions if self.total_actions > 0 else 0,
        }


class AutomationExecutorService:
    """
    Service for executing outreach automation tasks.
    Integrates with anti-detect browser, proxy, and scheduler services.
    """

    # Humanization settings
    MIN_ACTION_DELAY = 2  # seconds
    MAX_ACTION_DELAY = 8
    SCROLL_PROBABILITY = 0.7
    PROFILE_VIEW_PROBABILITY = 0.8
    TYPING_SIMULATION = True

    def __init__(
        self,
        browser_service=None,
        proxy_service=None,
        scheduler_service=None,
    ):
        self.browser_service = browser_service
        self.proxy_service = proxy_service
        self.scheduler_service = scheduler_service
        self._active_contexts: dict[str, ExecutionContext] = {}

    async def start_session(
        self,
        account_id: str,
        profile_id: str,
        browser_provider: str = "multilogin",
    ) -> ExecutionContext:
        """Start an automation session for an account."""
        context = ExecutionContext(
            account_id=account_id,
            profile_id=profile_id,
            session_started_at=datetime.now(),
        )

        # Get proxy for this account
        if self.proxy_service:
            proxy = self.proxy_service.get_account_proxy(account_id)
            if proxy:
                context.proxy_config = proxy.to_playwright_config()

        # Start browser session
        if self.browser_service:
            try:
                from .antidetect_browser_service import BrowserProvider
                provider = BrowserProvider(browser_provider)
                session = await self.browser_service.start_automation_session(
                    profile_id, provider
                )
                context.ws_endpoint = session.ws_endpoint
            except Exception as e:
                logger.warning("Failed to start browser session: %s", e)

        self._active_contexts[account_id] = context
        logger.info("Started automation session for account %s", account_id)
        return context

    async def stop_session(self, account_id: str) -> bool:
        """Stop an automation session."""
        context = self._active_contexts.pop(account_id, None)
        if not context:
            return False

        if self.browser_service and context.profile_id:
            try:
                from .antidetect_browser_service import BrowserProvider
                await self.browser_service.stop_automation_session(
                    context.profile_id, BrowserProvider.MULTILOGIN
                )
            except Exception as e:
                logger.warning("Failed to stop browser session: %s", e)

        logger.info("Stopped automation session for account %s", account_id)
        return True

    async def execute_follow(
        self,
        context: ExecutionContext,
        target_username: str,
        humanize: bool = True,
    ) -> ActionLog:
        """Execute a follow action with humanization."""
        start_time = datetime.now()
        action_id = f"follow_{target_username}_{start_time.timestamp()}"

        try:
            # Check rate limits
            if self.scheduler_service:
                from .smart_scheduler_service import ActionType
                can_execute, reason = self.scheduler_service.can_execute_action(
                    context.account_id, ActionType.FOLLOW, context.platform
                )
                if not can_execute:
                    return ActionLog(
                        id=action_id,
                        action_type="follow",
                        target_id=target_username,
                        result=ActionResult.RATE_LIMITED,
                        error_message=reason,
                    )

            # Humanization: view profile first
            if humanize and random.random() < self.PROFILE_VIEW_PROBABILITY:  # noqa: S311
                await self._simulate_profile_view(context, target_username)

            # Humanization: random delay
            if humanize:
                delay = random.uniform(self.MIN_ACTION_DELAY, self.MAX_ACTION_DELAY)  # noqa: S311
                await asyncio.sleep(delay)

            # Execute follow (mock implementation - would use Playwright in production)
            success = await self._perform_follow_action(context, target_username)

            duration = int((datetime.now() - start_time).total_seconds() * 1000)

            if success:
                # Record successful action
                if self.scheduler_service:
                    from .smart_scheduler_service import ActionType
                    self.scheduler_service.record_action(
                        context.account_id, ActionType.FOLLOW, success=True
                    )
                return ActionLog(
                    id=action_id,
                    action_type="follow",
                    target_id=target_username,
                    result=ActionResult.SUCCESS,
                    duration_ms=duration,
                )
            else:
                return ActionLog(
                    id=action_id,
                    action_type="follow",
                    target_id=target_username,
                    result=ActionResult.FAILED,
                    duration_ms=duration,
                    error_message="Follow action failed",
                )

        except Exception as e:
            logger.exception("Error executing follow action")
            return ActionLog(
                id=action_id,
                action_type="follow",
                target_id=target_username,
                result=ActionResult.FAILED,
                error_message=str(e),
            )

    async def execute_unfollow(
        self,
        context: ExecutionContext,
        target_username: str,
        humanize: bool = True,
    ) -> ActionLog:
        """Execute an unfollow action."""
        start_time = datetime.now()
        action_id = f"unfollow_{target_username}_{start_time.timestamp()}"

        try:
            if humanize:
                delay = random.uniform(self.MIN_ACTION_DELAY, self.MAX_ACTION_DELAY)  # noqa: S311
                await asyncio.sleep(delay)

            success = await self._perform_unfollow_action(context, target_username)
            duration = int((datetime.now() - start_time).total_seconds() * 1000)

            return ActionLog(
                id=action_id,
                action_type="unfollow",
                target_id=target_username,
                result=ActionResult.SUCCESS if success else ActionResult.FAILED,
                duration_ms=duration,
            )

        except Exception as e:
            logger.exception("Error executing unfollow action")
            return ActionLog(
                id=action_id,
                action_type="unfollow",
                target_id=target_username,
                result=ActionResult.FAILED,
                error_message=str(e),
            )

    async def execute_dm(
        self,
        context: ExecutionContext,
        target_username: str,
        message: str,
        humanize: bool = True,
    ) -> ActionLog:
        """Execute a DM action with typing simulation."""
        start_time = datetime.now()
        action_id = f"dm_{target_username}_{start_time.timestamp()}"

        try:
            # Check rate limits
            if self.scheduler_service:
                from .smart_scheduler_service import ActionType
                can_execute, reason = self.scheduler_service.can_execute_action(
                    context.account_id, ActionType.DM, context.platform
                )
                if not can_execute:
                    return ActionLog(
                        id=action_id,
                        action_type="dm",
                        target_id=target_username,
                        result=ActionResult.RATE_LIMITED,
                        error_message=reason,
                    )

            # Humanization: typing simulation delay
            if humanize and self.TYPING_SIMULATION:
                typing_time = len(message) * 0.05  # 50ms per character
                typing_time += random.uniform(1, 3)  # noqa: S311
                await asyncio.sleep(min(typing_time, 10))  # Max 10 seconds

            success = await self._perform_dm_action(context, target_username, message)
            duration = int((datetime.now() - start_time).total_seconds() * 1000)

            if success:
                if self.scheduler_service:
                    from .smart_scheduler_service import ActionType
                    self.scheduler_service.record_action(
                        context.account_id, ActionType.DM, success=True
                    )
                return ActionLog(
                    id=action_id,
                    action_type="dm",
                    target_id=target_username,
                    result=ActionResult.SUCCESS,
                    duration_ms=duration,
                    metadata={"message_length": len(message)},
                )
            else:
                return ActionLog(
                    id=action_id,
                    action_type="dm",
                    target_id=target_username,
                    result=ActionResult.FAILED,
                    duration_ms=duration,
                    error_message="DM action failed",
                )

        except Exception as e:
            logger.exception("Error executing DM action")
            return ActionLog(
                id=action_id,
                action_type="dm",
                target_id=target_username,
                result=ActionResult.FAILED,
                error_message=str(e),
            )

    async def execute_batch_follow(
        self,
        task_id: str,
        account_id: str,
        target_usernames: list[str],
        delay_range: tuple[int, int] = (60, 180),
    ) -> BatchExecutionResult:
        """Execute batch follow operations with delays."""
        result = BatchExecutionResult(
            task_id=task_id,
            total_actions=len(target_usernames),
        )

        context = self._active_contexts.get(account_id)
        if not context:
            result.status = ExecutionStatus.FAILED
            result.error_message = "No active session for account"
            return result

        result.status = ExecutionStatus.RUNNING

        for i, username in enumerate(target_usernames):
            # Execute follow
            action_log = await self.execute_follow(context, username)
            result.action_logs.append(action_log)

            # Update counters
            if action_log.result == ActionResult.SUCCESS:
                result.successful += 1
            elif action_log.result == ActionResult.RATE_LIMITED:
                result.rate_limited += 1
                # Stop if rate limited
                result.status = ExecutionStatus.RATE_LIMITED
                break
            elif action_log.result == ActionResult.SKIPPED:
                result.skipped += 1
            else:
                result.failed += 1

            # Delay between actions (except for last one)
            if i < len(target_usernames) - 1:
                delay = random.randint(*delay_range)  # noqa: S311
                await asyncio.sleep(delay)

        result.completed_at = datetime.now()
        if result.status == ExecutionStatus.RUNNING:
            result.status = ExecutionStatus.COMPLETED

        logger.info(
            "Batch follow completed: %d/%d successful",
            result.successful, result.total_actions
        )
        return result

    async def execute_batch_dm(
        self,
        task_id: str,
        account_id: str,
        targets: list[dict[str, str]],  # [{"username": "...", "message": "..."}]
        delay_range: tuple[int, int] = (120, 300),
    ) -> BatchExecutionResult:
        """Execute batch DM operations."""
        result = BatchExecutionResult(
            task_id=task_id,
            total_actions=len(targets),
        )

        context = self._active_contexts.get(account_id)
        if not context:
            result.status = ExecutionStatus.FAILED
            result.error_message = "No active session for account"
            return result

        result.status = ExecutionStatus.RUNNING

        for i, target in enumerate(targets):
            action_log = await self.execute_dm(
                context, target["username"], target["message"]
            )
            result.action_logs.append(action_log)

            if action_log.result == ActionResult.SUCCESS:
                result.successful += 1
            elif action_log.result == ActionResult.RATE_LIMITED:
                result.rate_limited += 1
                result.status = ExecutionStatus.RATE_LIMITED
                break
            else:
                result.failed += 1

            if i < len(targets) - 1:
                delay = random.randint(*delay_range)  # noqa: S311
                await asyncio.sleep(delay)

        result.completed_at = datetime.now()
        if result.status == ExecutionStatus.RUNNING:
            result.status = ExecutionStatus.COMPLETED

        return result

    async def _simulate_profile_view(
        self, context: ExecutionContext, username: str
    ) -> None:
        """Simulate viewing a user's profile."""
        # In production, this would use Playwright to navigate to the profile
        await asyncio.sleep(random.uniform(2, 5))  # noqa: S311
        logger.debug("Simulated profile view for %s", username)

    async def _perform_follow_action(
        self, context: ExecutionContext, username: str
    ) -> bool:
        """Perform the actual follow action using browser automation."""
        # Mock implementation - in production would use Playwright
        # This is where you'd implement the actual browser automation
        await asyncio.sleep(0.5)  # Simulate action time
        return True  # Mock success

    async def _perform_unfollow_action(
        self, context: ExecutionContext, username: str
    ) -> bool:
        """Perform the actual unfollow action."""
        await asyncio.sleep(0.5)
        return True

    async def _perform_dm_action(
        self, context: ExecutionContext, username: str, message: str
    ) -> bool:
        """Perform the actual DM action."""
        await asyncio.sleep(0.5)
        return True


def create_automation_executor_service(
    browser_service=None,
    proxy_service=None,
    scheduler_service=None,
) -> AutomationExecutorService:
    """Factory function to create AutomationExecutorService."""
    return AutomationExecutorService(
        browser_service=browser_service,
        proxy_service=proxy_service,
        scheduler_service=scheduler_service,
    )
