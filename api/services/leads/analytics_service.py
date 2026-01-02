"""
Leads analytics service.
Provides data analysis and metrics for the leads module.
"""

import logging
import operator
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.leads import (
    ConversationStatus,
    FollowerTarget,
    FollowerTargetStatus,
    OutreachConversation,
    OutreachTask,
    SubAccount,
    SubAccountStatus,
    TargetKOL,
)

logger = logging.getLogger(__name__)


class LeadsAnalyticsService:
    """Service for leads analytics and metrics."""

    @staticmethod
    def get_dashboard_overview(tenant_id: str) -> dict[str, Any]:
        """Get dashboard overview statistics."""
        with Session(db.engine) as session:
            # KOL stats
            kol_total = session.scalar(
                select(func.count(TargetKOL.id)).where(TargetKOL.tenant_id == tenant_id)
            ) or 0

            kol_active = session.scalar(
                select(func.count(TargetKOL.id)).where(
                    TargetKOL.tenant_id == tenant_id,
                    TargetKOL.status == "active",
                )
            ) or 0

            # Account stats
            account_total = session.scalar(
                select(func.count(SubAccount.id)).where(SubAccount.tenant_id == tenant_id)
            ) or 0

            account_healthy = session.scalar(
                select(func.count(SubAccount.id)).where(
                    SubAccount.tenant_id == tenant_id,
                    SubAccount.status == SubAccountStatus.HEALTHY,
                )
            ) or 0

            # Conversation stats
            conv_total = session.scalar(
                select(func.count(OutreachConversation.id)).where(
                    OutreachConversation.tenant_id == tenant_id
                )
            ) or 0

            conv_active = session.scalar(
                select(func.count(OutreachConversation.id)).where(
                    OutreachConversation.tenant_id == tenant_id,
                    OutreachConversation.status == ConversationStatus.AI_HANDLING,
                )
            ) or 0

            conv_needs_human = session.scalar(
                select(func.count(OutreachConversation.id)).where(
                    OutreachConversation.tenant_id == tenant_id,
                    OutreachConversation.status == ConversationStatus.NEEDS_HUMAN,
                )
            ) or 0

            # Funnel stats
            funnel = LeadsAnalyticsService.get_conversion_funnel(tenant_id)

            return {
                "kols": {
                    "total": kol_total,
                    "active": kol_active,
                },
                "accounts": {
                    "total": account_total,
                    "healthy": account_healthy,
                    "health_rate": round(account_healthy / account_total * 100, 1) if account_total > 0 else 0,
                },
                "conversations": {
                    "total": conv_total,
                    "active": conv_active,
                    "needs_human": conv_needs_human,
                },
                "funnel": funnel,
            }

    @staticmethod
    def get_conversion_funnel(
        tenant_id: str,
        target_kol_id: str | None = None,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> dict[str, Any]:
        """Get conversion funnel statistics."""
        with Session(db.engine) as session:
            base_query = select(func.count(FollowerTarget.id)).where(
                FollowerTarget.tenant_id == tenant_id
            )

            if target_kol_id:
                base_query = base_query.where(FollowerTarget.target_kol_id == target_kol_id)

            if date_range:
                base_query = base_query.where(
                    FollowerTarget.scraped_at >= date_range[0],
                    FollowerTarget.scraped_at <= date_range[1],
                )

            total = session.scalar(base_query) or 0

            followed = session.scalar(
                base_query.where(FollowerTarget.followed_at.isnot(None))
            ) or 0

            follow_backs = session.scalar(
                base_query.where(FollowerTarget.follow_back_at.isnot(None))
            ) or 0

            dm_sent = session.scalar(
                base_query.where(FollowerTarget.dm_sent_at.isnot(None))
            ) or 0

            converted = session.scalar(
                base_query.where(FollowerTarget.status == FollowerTargetStatus.CONVERTED)
            ) or 0

            return {
                "total_followers": total,
                "followed": followed,
                "follow_backs": follow_backs,
                "dm_sent": dm_sent,
                "converted": converted,
                "follow_back_rate": round(follow_backs / followed * 100, 1) if followed > 0 else 0,
                "dm_response_rate": round(converted / dm_sent * 100, 1) if dm_sent > 0 else 0,
                "conversion_rate": round(converted / total * 100, 2) if total > 0 else 0,
            }

    @staticmethod
    def get_kol_performance(tenant_id: str) -> list[dict[str, Any]]:
        """Get performance metrics for each KOL."""
        with Session(db.engine) as session:
            kols = session.scalars(
                select(TargetKOL).where(TargetKOL.tenant_id == tenant_id)
            ).all()

            results = []
            for kol in kols:
                # Get follower stats for this KOL
                total = session.scalar(
                    select(func.count(FollowerTarget.id)).where(
                        FollowerTarget.target_kol_id == kol.id
                    )
                ) or 0

                converted = session.scalar(
                    select(func.count(FollowerTarget.id)).where(
                        FollowerTarget.target_kol_id == kol.id,
                        FollowerTarget.status == FollowerTargetStatus.CONVERTED,
                    )
                ) or 0

                results.append({
                    "kol_id": kol.id,
                    "username": kol.username,
                    "platform": kol.platform,
                    "follower_count": kol.follower_count,
                    "scraped_followers": total,
                    "conversions": converted,
                    "conversion_rate": round(converted / total * 100, 2) if total > 0 else 0,
                })

            return sorted(results, key=operator.itemgetter("conversions"), reverse=True)

    @staticmethod
    def get_account_health_trend(tenant_id: str, days: int = 7) -> list[dict[str, Any]]:
        """Get account health trend over time."""
        # This would require historical tracking; for now return current snapshot
        with Session(db.engine) as session:
            accounts = session.scalars(
                select(SubAccount).where(SubAccount.tenant_id == tenant_id)
            ).all()

            status_counts: dict[str, int] = {}
            for account in accounts:
                status = account.status
                status_counts[status] = status_counts.get(status, 0) + 1

            return [
                {"status": status, "count": count}
                for status, count in status_counts.items()
            ]

    @staticmethod
    def get_daily_stats(tenant_id: str, days: int = 30) -> list[dict[str, Any]]:
        """Get daily statistics for the past N days."""
        results = []
        today = datetime.utcnow().date()

        with Session(db.engine) as session:
            for i in range(days):
                date = today - timedelta(days=i)
                start = datetime.combine(date, datetime.min.time())
                end = datetime.combine(date, datetime.max.time())

                # Followers scraped
                scraped = session.scalar(
                    select(func.count(FollowerTarget.id)).where(
                        FollowerTarget.tenant_id == tenant_id,
                        FollowerTarget.scraped_at >= start,
                        FollowerTarget.scraped_at <= end,
                    )
                ) or 0

                # Follows sent
                followed = session.scalar(
                    select(func.count(FollowerTarget.id)).where(
                        FollowerTarget.tenant_id == tenant_id,
                        FollowerTarget.followed_at >= start,
                        FollowerTarget.followed_at <= end,
                    )
                ) or 0

                # DMs sent
                dm_sent = session.scalar(
                    select(func.count(FollowerTarget.id)).where(
                        FollowerTarget.tenant_id == tenant_id,
                        FollowerTarget.dm_sent_at >= start,
                        FollowerTarget.dm_sent_at <= end,
                    )
                ) or 0

                # Conversions
                converted = session.scalar(
                    select(func.count(FollowerTarget.id)).where(
                        FollowerTarget.tenant_id == tenant_id,
                        FollowerTarget.converted_at >= start,
                        FollowerTarget.converted_at <= end,
                    )
                ) or 0

                results.append({
                    "date": date.isoformat(),
                    "scraped": scraped,
                    "followed": followed,
                    "dm_sent": dm_sent,
                    "converted": converted,
                })

        return list(reversed(results))

    @staticmethod
    def get_task_execution_summary(tenant_id: str) -> dict[str, Any]:
        """Get summary of outreach task executions."""
        with Session(db.engine) as session:
            total = session.scalar(
                select(func.count(OutreachTask.id)).where(OutreachTask.tenant_id == tenant_id)
            ) or 0

            completed = session.scalar(
                select(func.count(OutreachTask.id)).where(
                    OutreachTask.tenant_id == tenant_id,
                    OutreachTask.status == "completed",
                )
            ) or 0

            running = session.scalar(
                select(func.count(OutreachTask.id)).where(
                    OutreachTask.tenant_id == tenant_id,
                    OutreachTask.status == "running",
                )
            ) or 0

            failed = session.scalar(
                select(func.count(OutreachTask.id)).where(
                    OutreachTask.tenant_id == tenant_id,
                    OutreachTask.status == "failed",
                )
            ) or 0

            # Aggregate success/fail counts
            total_processed = session.scalar(
                select(func.sum(OutreachTask.processed_count)).where(
                    OutreachTask.tenant_id == tenant_id
                )
            ) or 0

            total_success = session.scalar(
                select(func.sum(OutreachTask.success_count)).where(
                    OutreachTask.tenant_id == tenant_id
                )
            ) or 0

            return {
                "total_tasks": total,
                "completed": completed,
                "running": running,
                "failed": failed,
                "total_processed": total_processed,
                "total_success": total_success,
                "success_rate": round(total_success / total_processed * 100, 1) if total_processed > 0 else 0,
            }

    @staticmethod
    def get_ai_status(tenant_id: str) -> dict[str, Any]:
        """Get AI service status for the tenant."""
        from services.leads.social_scraper_service import SocialScraperService

        # Check follower scraper status
        scraper_configured = SocialScraperService.is_configured()

        # Check conversation AI status (check if there are any workflow bindings)
        from services.leads import WorkflowBindingService

        bindings = WorkflowBindingService.get_bindings(tenant_id)
        conversation_binding = next(
            (b for b in bindings if b["action_type"] == "process_conversation" and b["is_enabled"]),
            None,
        )

        return {
            "conversation_ai": {
                "enabled": conversation_binding is not None,
                "configured": conversation_binding is not None,
            },
            "follower_scraper": {
                "enabled": SocialScraperService.APIFY_ENABLED,
                "configured": scraper_configured,
            },
        }
