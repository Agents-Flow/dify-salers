"""
Social account management service for X/Instagram outreach.
Handles TargetKOL, SubAccount, and FollowerTarget operations.
"""

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from libs.datetime_utils import naive_utc_now
from models.leads import (
    FollowerTarget,
    FollowerTargetStatus,
    OutreachConversation,
    OutreachTask,
    QualityTier,
    SubAccount,
    SubAccountStatus,
    TargetKOL,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of a CSV import operation."""

    total_rows: int
    imported: int
    skipped: int
    errors: list[str]


@dataclass
class HealthCheckResult:
    """Result of a sub-account health check."""

    account_id: str
    previous_status: str
    current_status: str
    message: str


class TargetKOLService:
    """Service for managing target KOL accounts."""

    @staticmethod
    def get_kols(
        tenant_id: str,
        page: int = 1,
        limit: int = 20,
        platform: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Get paginated list of target KOLs."""
        with Session(db.engine) as session:
            query = select(TargetKOL).where(TargetKOL.tenant_id == tenant_id)

            if platform:
                query = query.where(TargetKOL.platform == platform)
            if status:
                query = query.where(TargetKOL.status == status)

            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total = session.scalar(count_query) or 0

            # Get paginated results
            query = query.order_by(TargetKOL.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)
            kols = session.scalars(query).all()

            return {
                "data": [TargetKOLService._kol_to_dict(k) for k in kols],
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": total > page * limit,
            }

    @staticmethod
    def get_kol(tenant_id: str, kol_id: str) -> dict[str, Any] | None:
        """Get a single KOL by ID."""
        kol = db.session.query(TargetKOL).filter_by(id=kol_id, tenant_id=tenant_id).first()
        if not kol:
            return None
        return TargetKOLService._kol_to_dict(kol)

    @staticmethod
    def create_kol(
        tenant_id: str,
        platform: str,
        username: str,
        created_by: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a new target KOL."""
        kol = TargetKOL(
            tenant_id=tenant_id,
            platform=platform,
            username=username,
            created_by=created_by,
            **kwargs,
        )
        db.session.add(kol)
        db.session.commit()

        logger.info("Created target KOL: %s on %s", username, platform)
        return TargetKOLService._kol_to_dict(kol)

    @staticmethod
    def update_kol(tenant_id: str, kol_id: str, **kwargs) -> dict[str, Any] | None:
        """Update a target KOL."""
        kol = db.session.query(TargetKOL).filter_by(id=kol_id, tenant_id=tenant_id).first()
        if not kol:
            return None

        allowed_fields = [
            "display_name",
            "profile_url",
            "avatar_url",
            "bio",
            "follower_count",
            "following_count",
            "region",
            "language",
            "niche",
            "timezone",
            "status",
        ]
        for field in allowed_fields:
            if field in kwargs:
                setattr(kol, field, kwargs[field])

        db.session.commit()
        logger.info("Updated target KOL: %s", kol_id)
        return TargetKOLService._kol_to_dict(kol)

    @staticmethod
    def delete_kol(tenant_id: str, kol_id: str) -> bool:
        """Delete a target KOL and its associated data."""
        kol = db.session.query(TargetKOL).filter_by(id=kol_id, tenant_id=tenant_id).first()
        if not kol:
            return False

        # Delete associated sub-accounts and follower targets
        db.session.query(SubAccount).filter_by(target_kol_id=kol_id).delete()
        db.session.query(FollowerTarget).filter_by(target_kol_id=kol_id).delete()
        db.session.delete(kol)
        db.session.commit()

        logger.info("Deleted target KOL: %s", kol_id)
        return True

    @staticmethod
    def get_kol_stats(tenant_id: str, kol_id: str) -> dict[str, Any]:
        """Get statistics for a target KOL."""
        with Session(db.engine) as session:
            # Sub-account stats
            sub_accounts_total = (
                session.scalar(
                    select(func.count()).where(
                        SubAccount.tenant_id == tenant_id,
                        SubAccount.target_kol_id == kol_id,
                    )
                )
                or 0
            )
            sub_accounts_healthy = (
                session.scalar(
                    select(func.count()).where(
                        SubAccount.tenant_id == tenant_id,
                        SubAccount.target_kol_id == kol_id,
                        SubAccount.status == SubAccountStatus.HEALTHY,
                    )
                )
                or 0
            )

            # Follower target stats
            followers_total = (
                session.scalar(
                    select(func.count()).where(
                        FollowerTarget.tenant_id == tenant_id,
                        FollowerTarget.target_kol_id == kol_id,
                    )
                )
                or 0
            )
            followers_converted = (
                session.scalar(
                    select(func.count()).where(
                        FollowerTarget.tenant_id == tenant_id,
                        FollowerTarget.target_kol_id == kol_id,
                        FollowerTarget.status == FollowerTargetStatus.CONVERTED,
                    )
                )
                or 0
            )

            return {
                "sub_accounts": {
                    "total": sub_accounts_total,
                    "healthy": sub_accounts_healthy,
                },
                "followers": {
                    "total": followers_total,
                    "converted": followers_converted,
                    "conversion_rate": (
                        round(followers_converted / followers_total * 100, 2)
                        if followers_total > 0
                        else 0
                    ),
                },
            }

    @staticmethod
    def _kol_to_dict(kol: TargetKOL) -> dict[str, Any]:
        """Convert KOL model to dictionary."""
        return {
            "id": kol.id,
            "tenant_id": kol.tenant_id,
            "platform": kol.platform,
            "username": kol.username,
            "display_name": kol.display_name,
            "profile_url": kol.profile_url,
            "avatar_url": kol.avatar_url,
            "bio": kol.bio,
            "follower_count": kol.follower_count,
            "following_count": kol.following_count,
            "region": kol.region,
            "language": kol.language,
            "niche": kol.niche,
            "timezone": kol.timezone,
            "status": kol.status,
            "last_synced_at": kol.last_synced_at.isoformat() if kol.last_synced_at else None,
            "created_at": kol.created_at.isoformat() if kol.created_at else None,
            "updated_at": kol.updated_at.isoformat() if kol.updated_at else None,
        }


class SubAccountService:
    """Service for managing sub-accounts used for outreach operations."""

    @staticmethod
    def get_accounts(
        tenant_id: str,
        page: int = 1,
        limit: int = 20,
        target_kol_id: str | None = None,
        platform: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Get paginated list of sub-accounts."""
        with Session(db.engine) as session:
            query = select(SubAccount).where(SubAccount.tenant_id == tenant_id)

            if target_kol_id:
                query = query.where(SubAccount.target_kol_id == target_kol_id)
            if platform:
                query = query.where(SubAccount.platform == platform)
            if status:
                query = query.where(SubAccount.status == status)

            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total = session.scalar(count_query) or 0

            # Get paginated results
            query = query.order_by(SubAccount.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)
            accounts = session.scalars(query).all()

            return {
                "data": [SubAccountService._account_to_dict(a) for a in accounts],
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": total > page * limit,
            }

    @staticmethod
    def get_account(tenant_id: str, account_id: str) -> dict[str, Any] | None:
        """Get a single sub-account by ID."""
        account = (
            db.session.query(SubAccount).filter_by(id=account_id, tenant_id=tenant_id).first()
        )
        if not account:
            return None
        return SubAccountService._account_to_dict(account)

    @staticmethod
    def create_account(
        tenant_id: str,
        platform: str,
        username: str,
        created_by: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a new sub-account."""
        account = SubAccount(
            tenant_id=tenant_id,
            platform=platform,
            username=username,
            created_by=created_by,
            **kwargs,
        )
        db.session.add(account)
        db.session.commit()

        logger.info("Created sub-account: %s on %s", username, platform)
        return SubAccountService._account_to_dict(account)

    @staticmethod
    def import_accounts_csv(
        tenant_id: str,
        csv_content: str,
        platform: str,
        target_kol_id: str | None = None,
        created_by: str | None = None,
    ) -> ImportResult:
        """
        Import sub-accounts from CSV content.

        Expected CSV columns:
        - username (required)
        - email
        - password
        - email_password
        """
        result = ImportResult(total_rows=0, imported=0, skipped=0, errors=[])

        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(reader)
            result.total_rows = len(rows)

            for i, row in enumerate(rows, start=1):
                try:
                    username = row.get("username", "").strip()
                    if not username:
                        result.errors.append(f"Row {i}: Missing username")
                        result.skipped += 1
                        continue

                    # Check if account already exists
                    existing = (
                        db.session.query(SubAccount)
                        .filter_by(
                            tenant_id=tenant_id,
                            platform=platform,
                            username=username,
                        )
                        .first()
                    )
                    if existing:
                        result.skipped += 1
                        continue

                    # Create new account
                    account = SubAccount(
                        tenant_id=tenant_id,
                        platform=platform,
                        username=username,
                        email=row.get("email", "").strip() or None,
                        password_encrypted=row.get("password", "").strip() or None,
                        email_password_encrypted=row.get("email_password", "").strip() or None,
                        target_kol_id=target_kol_id,
                        created_by=created_by,
                    )
                    db.session.add(account)
                    result.imported += 1

                except Exception as e:
                    result.errors.append(f"Row {i}: {e!s}")
                    result.skipped += 1

            db.session.commit()
            logger.info(
                "Imported %d sub-accounts (skipped: %d, errors: %d)",
                result.imported,
                result.skipped,
                len(result.errors),
            )

        except csv.Error as e:
            result.errors.append(f"CSV parsing error: {e!s}")

        return result

    @staticmethod
    def get_available_account(
        tenant_id: str,
        target_kol_id: str,
    ) -> SubAccount | None:
        """
        Get an available sub-account for task execution.
        Prioritizes accounts that haven't hit daily limits and are not cooling.
        """
        now = naive_utc_now()

        account = (
            db.session.query(SubAccount)
            .filter(
                SubAccount.tenant_id == tenant_id,
                SubAccount.target_kol_id == target_kol_id,
                SubAccount.status == SubAccountStatus.HEALTHY,
                (SubAccount.cooling_until.is_(None)) | (SubAccount.cooling_until < now),
            )
            .filter(SubAccount.daily_follows < SubAccount.daily_limit_follows)
            .filter(SubAccount.daily_dms < SubAccount.daily_limit_dms)
            .order_by(SubAccount.daily_follows.asc())
            .first()
        )
        return account

    @staticmethod
    def mark_cooling(
        account_id: str,
        duration_hours: int = 24,
        reason: str | None = None,
    ) -> None:
        """Mark an account as cooling (temporary rest)."""
        account = db.session.query(SubAccount).filter_by(id=account_id).first()
        if account:
            account.status = SubAccountStatus.COOLING
            account.cooling_until = naive_utc_now() + timedelta(hours=duration_hours)
            if reason:
                account.ban_reason = reason
            db.session.commit()
            logger.info("Marked account %s as cooling for %d hours", account_id, duration_hours)

    @staticmethod
    def mark_banned(account_id: str, reason: str | None = None) -> None:
        """Mark an account as banned."""
        account = db.session.query(SubAccount).filter_by(id=account_id).first()
        if account:
            account.status = SubAccountStatus.BANNED
            account.ban_reason = reason
            db.session.commit()
            logger.info("Marked account %s as banned: %s", account_id, reason)

    @staticmethod
    def reset_daily_counters(tenant_id: str) -> int:
        """Reset daily counters for all accounts. Should be called daily."""
        result = (
            db.session.query(SubAccount)
            .filter_by(tenant_id=tenant_id)
            .update({"daily_follows": 0, "daily_dms": 0})
        )
        db.session.commit()
        logger.info("Reset daily counters for %d accounts", result)
        return result

    @staticmethod
    def increment_follow_count(account_id: str) -> None:
        """Increment follow count for an account."""
        account = db.session.query(SubAccount).filter_by(id=account_id).first()
        if account:
            account.daily_follows += 1
            account.total_follows += 1
            db.session.commit()

    @staticmethod
    def increment_dm_count(account_id: str) -> None:
        """Increment DM count for an account."""
        account = db.session.query(SubAccount).filter_by(id=account_id).first()
        if account:
            account.daily_dms += 1
            account.total_dms += 1
            db.session.commit()

    @staticmethod
    def health_check(account_id: str) -> HealthCheckResult:
        """
        Perform a health check on an account.
        This is a placeholder - actual implementation would use browser automation.
        """
        account = db.session.query(SubAccount).filter_by(id=account_id).first()
        if not account:
            return HealthCheckResult(
                account_id=account_id,
                previous_status="unknown",
                current_status="unknown",
                message="Account not found",
            )

        previous_status = account.status

        # Check if cooling period is over
        now = naive_utc_now()
        if account.status == SubAccountStatus.COOLING and account.cooling_until:
            if account.cooling_until < now:
                account.status = SubAccountStatus.HEALTHY
                account.cooling_until = None

        account.last_health_check = now
        db.session.commit()

        return HealthCheckResult(
            account_id=account_id,
            previous_status=previous_status,
            current_status=account.status,
            message="Health check completed",
        )

    @staticmethod
    def delete_account(tenant_id: str, account_id: str) -> bool:
        """Delete a sub-account."""
        account = (
            db.session.query(SubAccount).filter_by(id=account_id, tenant_id=tenant_id).first()
        )
        if not account:
            return False

        # Delete associated conversations
        db.session.query(OutreachConversation).filter_by(sub_account_id=account_id).delete()
        db.session.delete(account)
        db.session.commit()

        logger.info("Deleted sub-account: %s", account_id)
        return True

    @staticmethod
    def _account_to_dict(account: SubAccount) -> dict[str, Any]:
        """Convert account model to dictionary (excludes sensitive data)."""
        return {
            "id": account.id,
            "tenant_id": account.tenant_id,
            "target_kol_id": account.target_kol_id,
            "platform": account.platform,
            "username": account.username,
            "email": account.email,
            "browser_profile_id": account.browser_profile_id,
            "browser_provider": account.browser_provider,
            "has_proxy": account.proxy_config is not None,
            "status": account.status,
            "last_health_check": (
                account.last_health_check.isoformat() if account.last_health_check else None
            ),
            "cooling_until": (
                account.cooling_until.isoformat() if account.cooling_until else None
            ),
            "daily_follows": account.daily_follows,
            "daily_dms": account.daily_dms,
            "daily_limit_follows": account.daily_limit_follows,
            "daily_limit_dms": account.daily_limit_dms,
            "total_follows": account.total_follows,
            "total_dms": account.total_dms,
            "total_conversions": account.total_conversions,
            "is_warmed": account.is_warmed,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "updated_at": account.updated_at.isoformat() if account.updated_at else None,
        }


class FollowerTargetService:
    """Service for managing follower targets."""

    @staticmethod
    def get_targets(
        tenant_id: str,
        page: int = 1,
        limit: int = 20,
        target_kol_id: str | None = None,
        status: str | None = None,
        quality_tier: str | None = None,
    ) -> dict[str, Any]:
        """Get paginated list of follower targets."""
        with Session(db.engine) as session:
            query = select(FollowerTarget).where(FollowerTarget.tenant_id == tenant_id)

            if target_kol_id:
                query = query.where(FollowerTarget.target_kol_id == target_kol_id)
            if status:
                query = query.where(FollowerTarget.status == status)
            if quality_tier:
                query = query.where(FollowerTarget.quality_tier == quality_tier)

            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total = session.scalar(count_query) or 0

            # Get paginated results
            query = query.order_by(FollowerTarget.quality_score.desc())
            query = query.offset((page - 1) * limit).limit(limit)
            targets = session.scalars(query).all()

            return {
                "data": [FollowerTargetService._target_to_dict(t) for t in targets],
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": total > page * limit,
            }

    @staticmethod
    def create_targets_batch(
        tenant_id: str,
        target_kol_id: str,
        platform: str,
        targets_data: list[dict],
    ) -> int:
        """
        Batch create follower targets with deduplication.
        Returns the number of targets created.
        """
        created_count = 0

        for data in targets_data:
            platform_user_id = data.get("platform_user_id")
            if not platform_user_id:
                continue

            # Check for existing
            existing = (
                db.session.query(FollowerTarget)
                .filter_by(
                    tenant_id=tenant_id,
                    platform=platform,
                    platform_user_id=platform_user_id,
                )
                .first()
            )
            if existing:
                continue

            # Calculate quality score
            quality_score, quality_tier = FollowerTargetService._calculate_quality(data)

            target = FollowerTarget(
                tenant_id=tenant_id,
                target_kol_id=target_kol_id,
                platform=platform,
                platform_user_id=platform_user_id,
                username=data.get("username"),
                display_name=data.get("display_name"),
                bio=data.get("bio"),
                avatar_url=data.get("avatar_url"),
                follower_count=data.get("follower_count", 0),
                following_count=data.get("following_count", 0),
                post_count=data.get("post_count", 0),
                is_verified=data.get("is_verified", False),
                is_private=data.get("is_private", False),
                quality_score=quality_score,
                quality_tier=quality_tier,
                tags=data.get("tags"),
            )
            db.session.add(target)
            created_count += 1

        db.session.commit()
        logger.info("Created %d follower targets for KOL %s", created_count, target_kol_id)
        return created_count

    @staticmethod
    def _calculate_quality(data: dict) -> tuple[int, str]:
        """
        Calculate quality score and tier for a follower.
        Score: 0-100, Tier: high/medium/low
        """
        score = 50  # Base score

        follower_count = data.get("follower_count", 0)
        following_count = data.get("following_count", 0)
        post_count = data.get("post_count", 0)
        bio = data.get("bio", "") or ""

        # Follower count scoring
        if 100 <= follower_count <= 10000:
            score += 15  # Sweet spot
        elif follower_count > 10000:
            score += 10  # Good but might be harder to convert
        elif follower_count < 100:
            score -= 10  # Too few followers

        # Following ratio (following/followers)
        if follower_count > 0:
            ratio = following_count / follower_count
            if ratio > 5:
                score -= 20  # Likely spam/bot
            elif ratio < 1:
                score += 10  # Selective follower

        # Post count
        if post_count >= 10:
            score += 10  # Active user
        elif post_count == 0:
            score -= 15  # Inactive

        # Bio analysis
        if bio:
            score += 5  # Has bio
            # Negative keywords
            negative_keywords = ["bot", "spam", "promo", "follow4follow", "f4f"]
            if any(kw in bio.lower() for kw in negative_keywords):
                score -= 25

        # Clamp score
        score = max(0, min(100, score))

        # Determine tier
        if score >= 70:
            tier = QualityTier.HIGH
        elif score >= 40:
            tier = QualityTier.MEDIUM
        else:
            tier = QualityTier.LOW

        return score, tier

    @staticmethod
    def update_status(
        target_id: str,
        status: FollowerTargetStatus,
        assigned_sub_account_id: str | None = None,
    ) -> bool:
        """Update the status of a follower target."""
        target = db.session.query(FollowerTarget).filter_by(id=target_id).first()
        if not target:
            return False

        target.status = status

        # Update timestamps based on status
        now = naive_utc_now()
        if status == FollowerTargetStatus.FOLLOWED:
            target.followed_at = now
            # Set timeout for follow-back (7 days)
            target.follow_timeout_at = now + timedelta(days=7)
        elif status == FollowerTargetStatus.FOLLOW_BACK:
            target.follow_back_at = now
        elif status == FollowerTargetStatus.DM_SENT:
            target.dm_sent_at = now
        elif status == FollowerTargetStatus.CONVERTED:
            target.converted_at = now

        if assigned_sub_account_id:
            target.assigned_sub_account_id = assigned_sub_account_id

        db.session.commit()
        return True

    @staticmethod
    def get_pending_follow_backs(
        tenant_id: str,
        target_kol_id: str,
        limit: int = 100,
    ) -> list[FollowerTarget]:
        """Get targets that were followed but haven't followed back yet."""
        now = naive_utc_now()
        return (
            db.session.query(FollowerTarget)
            .filter(
                FollowerTarget.tenant_id == tenant_id,
                FollowerTarget.target_kol_id == target_kol_id,
                FollowerTarget.status == FollowerTargetStatus.FOLLOWED,
                (FollowerTarget.follow_timeout_at.is_(None))
                | (FollowerTarget.follow_timeout_at > now),
            )
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_ready_for_dm(
        tenant_id: str,
        target_kol_id: str,
        limit: int = 50,
    ) -> list[FollowerTarget]:
        """Get targets that have followed back and are ready for DM."""
        return (
            db.session.query(FollowerTarget)
            .filter(
                FollowerTarget.tenant_id == tenant_id,
                FollowerTarget.target_kol_id == target_kol_id,
                FollowerTarget.status == FollowerTargetStatus.FOLLOW_BACK,
            )
            .order_by(FollowerTarget.quality_score.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_timed_out_follows(tenant_id: str, limit: int = 100) -> list[FollowerTarget]:
        """Get targets whose follow-back timeout has expired."""
        now = naive_utc_now()
        return (
            db.session.query(FollowerTarget)
            .filter(
                FollowerTarget.tenant_id == tenant_id,
                FollowerTarget.status == FollowerTargetStatus.FOLLOWED,
                FollowerTarget.follow_timeout_at < now,
            )
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_funnel_stats(tenant_id: str, target_kol_id: str | None = None) -> dict[str, int]:
        """Get conversion funnel statistics."""
        with Session(db.engine) as session:
            base_filter = [FollowerTarget.tenant_id == tenant_id]
            if target_kol_id:
                base_filter.append(FollowerTarget.target_kol_id == target_kol_id)

            stats = {}
            for status in FollowerTargetStatus:
                count = (
                    session.scalar(
                        select(func.count()).where(
                            *base_filter,
                            FollowerTarget.status == status,
                        )
                    )
                    or 0
                )
                stats[status.value] = count

            # Calculate totals
            stats["total"] = sum(stats.values())

            return stats

    @staticmethod
    def _target_to_dict(target: FollowerTarget) -> dict[str, Any]:
        """Convert target model to dictionary."""
        return {
            "id": target.id,
            "tenant_id": target.tenant_id,
            "target_kol_id": target.target_kol_id,
            "platform": target.platform,
            "platform_user_id": target.platform_user_id,
            "username": target.username,
            "display_name": target.display_name,
            "bio": target.bio,
            "avatar_url": target.avatar_url,
            "follower_count": target.follower_count,
            "following_count": target.following_count,
            "post_count": target.post_count,
            "is_verified": target.is_verified,
            "is_private": target.is_private,
            "quality_tier": target.quality_tier,
            "quality_score": target.quality_score,
            "tags": target.tags,
            "status": target.status,
            "assigned_sub_account_id": target.assigned_sub_account_id,
            "scraped_at": target.scraped_at.isoformat() if target.scraped_at else None,
            "followed_at": target.followed_at.isoformat() if target.followed_at else None,
            "follow_back_at": (
                target.follow_back_at.isoformat() if target.follow_back_at else None
            ),
            "dm_sent_at": target.dm_sent_at.isoformat() if target.dm_sent_at else None,
            "converted_at": target.converted_at.isoformat() if target.converted_at else None,
            "created_at": target.created_at.isoformat() if target.created_at else None,
        }


class OutreachTaskService:
    """Service for managing outreach tasks."""

    @staticmethod
    def get_tasks(
        tenant_id: str,
        page: int = 1,
        limit: int = 20,
        target_kol_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Get paginated list of outreach tasks."""
        with Session(db.engine) as session:
            query = select(OutreachTask).where(OutreachTask.tenant_id == tenant_id)

            if target_kol_id:
                query = query.where(OutreachTask.target_kol_id == target_kol_id)
            if status:
                query = query.where(OutreachTask.status == status)

            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total = session.scalar(count_query) or 0

            # Get paginated results
            query = query.order_by(OutreachTask.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)
            tasks = session.scalars(query).all()

            return {
                "data": [OutreachTaskService._task_to_dict(t) for t in tasks],
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": total > page * limit,
            }

    @staticmethod
    def create_task(
        tenant_id: str,
        target_kol_id: str,
        name: str,
        task_type: str,
        platform: str,
        config: dict,
        created_by: str | None = None,
        message_templates: list[str] | None = None,
        scheduled_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a new outreach task."""
        # Calculate target count based on config
        target_count = config.get("target_count", 0)

        task = OutreachTask(
            tenant_id=tenant_id,
            target_kol_id=target_kol_id,
            name=name,
            task_type=task_type,
            platform=platform,
            config=config,
            message_templates=message_templates,
            target_count=target_count,
            scheduled_at=scheduled_at,
            created_by=created_by,
        )
        db.session.add(task)
        db.session.commit()

        logger.info("Created outreach task: %s", name)
        return OutreachTaskService._task_to_dict(task)

    @staticmethod
    def start_task(task_id: str) -> bool:
        """Mark a task as started."""
        task = db.session.query(OutreachTask).filter_by(id=task_id).first()
        if not task or task.status != "pending":
            return False

        task.status = "running"
        task.started_at = naive_utc_now()
        db.session.commit()

        # Trigger async execution (would be a Celery task)
        logger.info("Started outreach task: %s", task_id)
        return True

    @staticmethod
    def complete_task(
        task_id: str,
        success_count: int,
        failed_count: int,
        error_message: str | None = None,
    ) -> bool:
        """Mark a task as completed."""
        task = db.session.query(OutreachTask).filter_by(id=task_id).first()
        if not task:
            return False

        task.status = "completed" if not error_message else "failed"
        task.completed_at = naive_utc_now()
        task.success_count = success_count
        task.failed_count = failed_count
        task.processed_count = success_count + failed_count
        task.error_message = error_message
        db.session.commit()

        logger.info(
            "Completed outreach task: %s (success=%d, failed=%d)",
            task_id,
            success_count,
            failed_count,
        )
        return True

    @staticmethod
    def _task_to_dict(task: OutreachTask) -> dict[str, Any]:
        """Convert task model to dictionary."""
        return {
            "id": task.id,
            "tenant_id": task.tenant_id,
            "target_kol_id": task.target_kol_id,
            "name": task.name,
            "task_type": task.task_type,
            "platform": task.platform,
            "config": task.config,
            "message_templates": task.message_templates,
            "target_count": task.target_count,
            "processed_count": task.processed_count,
            "success_count": task.success_count,
            "failed_count": task.failed_count,
            "status": task.status,
            "error_message": task.error_message,
            "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }


def create_target_kol_service() -> TargetKOLService:
    """Factory function to create TargetKOLService."""
    return TargetKOLService()


def create_sub_account_service() -> SubAccountService:
    """Factory function to create SubAccountService."""
    return SubAccountService()


def create_follower_target_service() -> FollowerTargetService:
    """Factory function to create FollowerTargetService."""
    return FollowerTargetService()


def create_outreach_task_service() -> OutreachTaskService:
    """Factory function to create OutreachTaskService."""
    return OutreachTaskService()
