"""
Follow-back detection service for Instagram.
Monitors mutual follow status and manages the follow-unfollow lifecycle.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class FollowStatus(StrEnum):
    """Follow relationship status."""
    NOT_FOLLOWING = "not_following"
    FOLLOWING = "following"
    MUTUAL = "mutual"
    PENDING = "pending"  # Follow request sent (private account)
    BLOCKED = "blocked"


@dataclass
class FollowRelationship:
    """Represents a follow relationship between two accounts."""
    id: str
    sub_account_id: str
    target_user_id: str
    target_username: str
    status: FollowStatus = FollowStatus.NOT_FOLLOWING
    followed_at: datetime | None = None
    follow_back_at: datetime | None = None
    unfollow_at: datetime | None = None
    timeout_at: datetime | None = None  # When to auto-unfollow
    check_count: int = 0
    last_checked_at: datetime | None = None
    is_private_account: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sub_account_id": self.sub_account_id,
            "target_username": self.target_username,
            "status": self.status,
            "followed_at": self.followed_at.isoformat() if self.followed_at else None,
            "follow_back_at": self.follow_back_at.isoformat() if self.follow_back_at else None,
            "is_mutual": self.status == FollowStatus.MUTUAL,
            "days_waiting": self._days_waiting(),
        }

    def _days_waiting(self) -> int:
        if not self.followed_at:
            return 0
        return (datetime.now() - self.followed_at).days


@dataclass
class DetectionResult:
    """Result of a follow-back detection check."""
    relationship_id: str
    previous_status: FollowStatus
    current_status: FollowStatus
    changed: bool = False
    checked_at: datetime = field(default_factory=datetime.now)
    should_unfollow: bool = False
    should_dm: bool = False
    error_message: str | None = None


@dataclass
class BatchDetectionResult:
    """Result of batch detection."""
    total_checked: int = 0
    new_follow_backs: int = 0
    timeouts: int = 0
    errors: int = 0
    results: list[DetectionResult] = field(default_factory=list)


class FollowBackDetectorService:
    """
    Service for detecting Instagram follow-backs.
    Manages the lifecycle of follow relationships and triggers DM workflows.
    """

    # Default timeout for auto-unfollow (7 days)
    DEFAULT_TIMEOUT_DAYS = 7

    # Check interval (don't check too frequently)
    MIN_CHECK_INTERVAL_HOURS = 1

    def __init__(self, automation_executor=None):
        self.automation_executor = automation_executor
        self._relationships: dict[str, FollowRelationship] = {}
        self._timeout_days = self.DEFAULT_TIMEOUT_DAYS

    def set_timeout_days(self, days: int) -> None:
        """Set the number of days before auto-unfollow."""
        self._timeout_days = days
        logger.info("Set follow-back timeout to %d days", days)

    def register_follow(
        self,
        sub_account_id: str,
        target_user_id: str,
        target_username: str,
        is_private: bool = False,
    ) -> FollowRelationship:
        """Register a new follow action for tracking."""
        relationship_id = f"{sub_account_id}_{target_user_id}"

        if relationship_id in self._relationships:
            # Update existing relationship
            rel = self._relationships[relationship_id]
            rel.status = FollowStatus.PENDING if is_private else FollowStatus.FOLLOWING
            rel.followed_at = datetime.now()
            rel.timeout_at = datetime.now() + timedelta(days=self._timeout_days)
        else:
            rel = FollowRelationship(
                id=relationship_id,
                sub_account_id=sub_account_id,
                target_user_id=target_user_id,
                target_username=target_username,
                status=FollowStatus.PENDING if is_private else FollowStatus.FOLLOWING,
                followed_at=datetime.now(),
                timeout_at=datetime.now() + timedelta(days=self._timeout_days),
                is_private_account=is_private,
            )
            self._relationships[relationship_id] = rel

        logger.info(
            "Registered follow: %s -> %s (private=%s)",
            sub_account_id, target_username, is_private
        )
        return rel

    def get_relationship(
        self,
        sub_account_id: str,
        target_user_id: str,
    ) -> FollowRelationship | None:
        """Get a follow relationship."""
        relationship_id = f"{sub_account_id}_{target_user_id}"
        return self._relationships.get(relationship_id)

    def get_pending_relationships(
        self,
        sub_account_id: str | None = None,
    ) -> list[FollowRelationship]:
        """Get relationships pending follow-back check."""
        now = datetime.now()
        pending = []

        for rel in self._relationships.values():
            # Skip if already mutual or unfollowed
            if rel.status in (FollowStatus.MUTUAL, FollowStatus.NOT_FOLLOWING):
                continue

            # Filter by account if specified
            if sub_account_id and rel.sub_account_id != sub_account_id:
                continue

            # Check if enough time has passed since last check
            if rel.last_checked_at:
                hours_since_check = (now - rel.last_checked_at).total_seconds() / 3600
                if hours_since_check < self.MIN_CHECK_INTERVAL_HOURS:
                    continue

            pending.append(rel)

        return pending

    def get_timeout_relationships(
        self,
        sub_account_id: str | None = None,
    ) -> list[FollowRelationship]:
        """Get relationships that have timed out (need auto-unfollow)."""
        now = datetime.now()
        timeouts = []

        for rel in self._relationships.values():
            if rel.status != FollowStatus.FOLLOWING:
                continue

            if sub_account_id and rel.sub_account_id != sub_account_id:
                continue

            if rel.timeout_at and rel.timeout_at <= now:
                timeouts.append(rel)

        return timeouts

    async def check_follow_back(
        self,
        relationship: FollowRelationship,
    ) -> DetectionResult:
        """Check if a target user has followed back."""
        result = DetectionResult(
            relationship_id=relationship.id,
            previous_status=relationship.status,
            current_status=relationship.status,
        )

        try:
            # In production, this would use browser automation to check
            # the follower list of the sub-account
            is_following_back = await self._check_follower_status(
                relationship.sub_account_id,
                relationship.target_user_id,
            )

            relationship.check_count += 1
            relationship.last_checked_at = datetime.now()

            if is_following_back:
                if relationship.status != FollowStatus.MUTUAL:
                    # New follow-back detected!
                    result.current_status = FollowStatus.MUTUAL
                    result.changed = True
                    result.should_dm = True

                    relationship.status = FollowStatus.MUTUAL
                    relationship.follow_back_at = datetime.now()

                    logger.info(
                        "Follow-back detected: %s <- %s",
                        relationship.sub_account_id,
                        relationship.target_username
                    )
            else:
                # Check for timeout
                if relationship.timeout_at and datetime.now() >= relationship.timeout_at:
                    result.should_unfollow = True
                    logger.info(
                        "Follow-back timeout: %s -> %s",
                        relationship.sub_account_id,
                        relationship.target_username
                    )

        except Exception as e:
            result.error_message = str(e)
            logger.exception("Error checking follow-back status")

        return result

    async def check_batch(
        self,
        sub_account_id: str,
        limit: int = 50,
    ) -> BatchDetectionResult:
        """Check follow-back status for multiple relationships."""
        batch_result = BatchDetectionResult()

        # Get pending relationships for this account
        pending = self.get_pending_relationships(sub_account_id)[:limit]

        for relationship in pending:
            result = await self.check_follow_back(relationship)
            batch_result.results.append(result)
            batch_result.total_checked += 1

            if result.error_message:
                batch_result.errors += 1
            elif result.changed and result.current_status == FollowStatus.MUTUAL:
                batch_result.new_follow_backs += 1

        # Also check for timeouts
        timeouts = self.get_timeout_relationships(sub_account_id)
        batch_result.timeouts = len(timeouts)

        logger.info(
            "Batch check complete: %d checked, %d new follow-backs, %d timeouts",
            batch_result.total_checked,
            batch_result.new_follow_backs,
            batch_result.timeouts
        )

        return batch_result

    async def process_timeouts(
        self,
        sub_account_id: str,
    ) -> list[str]:
        """Process timed-out relationships by unfollowing."""
        unfollowed = []
        timeouts = self.get_timeout_relationships(sub_account_id)

        for relationship in timeouts:
            try:
                # Execute unfollow
                if self.automation_executor:
                    context = self.automation_executor._active_contexts.get(sub_account_id)
                    if context:
                        await self.automation_executor.execute_unfollow(
                            context, relationship.target_username
                        )

                # Update status
                relationship.status = FollowStatus.NOT_FOLLOWING
                relationship.unfollow_at = datetime.now()
                unfollowed.append(relationship.target_username)

                logger.info(
                    "Auto-unfollowed due to timeout: %s -> %s",
                    sub_account_id, relationship.target_username
                )

            except Exception as e:
                logger.exception("Error processing timeout unfollow")

        return unfollowed

    async def _check_follower_status(
        self,
        sub_account_id: str,
        target_user_id: str,
    ) -> bool:
        """
        Check if target user is in sub-account's follower list.
        In production, this would use browser automation.
        """
        # Mock implementation - in production would check actual follower list
        # This is where Playwright would navigate to the followers page
        # and search for the target user
        return False  # Default to not following back

    def get_mutual_followers(
        self,
        sub_account_id: str,
    ) -> list[FollowRelationship]:
        """Get all mutual follow relationships for an account."""
        return [
            rel for rel in self._relationships.values()
            if rel.sub_account_id == sub_account_id
            and rel.status == FollowStatus.MUTUAL
        ]

    def get_dm_ready_targets(
        self,
        sub_account_id: str,
    ) -> list[FollowRelationship]:
        """Get mutual followers who haven't been DM'd yet."""
        mutual = self.get_mutual_followers(sub_account_id)
        # Filter to those without DM sent (would check metadata or separate tracking)
        return [
            rel for rel in mutual
            if not rel.metadata.get("dm_sent", False)
        ]

    def mark_dm_sent(
        self,
        relationship_id: str,
    ) -> bool:
        """Mark that a DM has been sent for this relationship."""
        rel = self._relationships.get(relationship_id)
        if rel:
            rel.metadata["dm_sent"] = True
            rel.metadata["dm_sent_at"] = datetime.now().isoformat()
            return True
        return False

    def get_stats(
        self,
        sub_account_id: str | None = None,
    ) -> dict[str, Any]:
        """Get statistics for follow-back detection."""
        relationships = list(self._relationships.values())
        if sub_account_id:
            relationships = [r for r in relationships if r.sub_account_id == sub_account_id]

        total = len(relationships)
        by_status = dict.fromkeys(FollowStatus, 0)
        for rel in relationships:
            by_status[rel.status] += 1

        mutual_count = by_status[FollowStatus.MUTUAL]
        following_count = by_status[FollowStatus.FOLLOWING]

        return {
            "total": total,
            "following": following_count,
            "mutual": mutual_count,
            "pending": by_status[FollowStatus.PENDING],
            "not_following": by_status[FollowStatus.NOT_FOLLOWING],
            "follow_back_rate": mutual_count / (following_count + mutual_count)
            if (following_count + mutual_count) > 0 else 0,
        }


def create_follow_back_detector_service(
    automation_executor=None,
) -> FollowBackDetectorService:
    """Factory function to create FollowBackDetectorService."""
    return FollowBackDetectorService(automation_executor=automation_executor)
