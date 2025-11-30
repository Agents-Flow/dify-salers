"""
Lead acquisition service layer.
Handles business logic for lead tasks and leads management.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.leads import Lead, LeadStatus, LeadTask, LeadTaskRun, LeadTaskStatus, SupportedPlatform

logger = logging.getLogger(__name__)


class LeadTaskService:
    """Service for managing lead acquisition tasks."""

    @staticmethod
    def get_tasks(
        tenant_id: str,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
    ) -> dict[str, Any]:
        """
        Get paginated list of lead tasks for a tenant.

        Args:
            tenant_id: The tenant ID
            page: Page number (1-indexed)
            limit: Items per page
            status: Optional status filter

        Returns:
            Dictionary with data, total, page, and has_more
        """
        with Session(db.engine) as session:
            query = select(LeadTask).where(LeadTask.tenant_id == tenant_id)

            if status:
                query = query.where(LeadTask.status == status)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total = session.scalar(count_query) or 0

            # Get paginated results
            query = query.order_by(LeadTask.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)
            tasks = session.scalars(query).all()

            return {
                "data": [LeadTaskService._task_to_dict(t) for t in tasks],
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": total > page * limit,
            }

    @staticmethod
    def get_task(tenant_id: str, task_id: str) -> dict[str, Any] | None:
        """Get a single task by ID."""
        task = db.session.query(LeadTask).filter_by(id=task_id, tenant_id=tenant_id).first()

        if not task:
            return None
        return LeadTaskService._task_to_dict(task)

    @staticmethod
    def get_supported_platforms() -> list[dict[str, str]]:
        """Get list of supported platforms for lead crawling."""
        return [
            {"value": SupportedPlatform.DOUYIN, "label": "抖音 (Douyin)"},
            {"value": SupportedPlatform.XIAOHONGSHU, "label": "小红书 (Xiaohongshu)"},
            {"value": SupportedPlatform.KUAISHOU, "label": "快手 (Kuaishou)"},
            {"value": SupportedPlatform.BILIBILI, "label": "B站 (Bilibili)"},
            {"value": SupportedPlatform.WEIBO, "label": "微博 (Weibo)"},
        ]

    @staticmethod
    def create_task(
        tenant_id: str,
        created_by: str,
        name: str,
        task_type: str = "comment_crawl",
        platform: str = "douyin",
        config: dict | None = None,
    ) -> dict[str, Any]:
        """
        Create a new lead acquisition task.

        Args:
            tenant_id: The tenant ID
            created_by: User ID who created the task
            name: Task name
            task_type: Type of task (default: comment_crawl)
            platform: Target platform (default: douyin)
            config: Task configuration

        Returns:
            Created task as dictionary
        """
        # Validate platform
        valid_platforms = [p.value for p in SupportedPlatform]
        if platform not in valid_platforms:
            platform = SupportedPlatform.DOUYIN

        task = LeadTask(
            tenant_id=tenant_id,
            created_by=created_by,
            name=name,
            task_type=task_type,
            platform=platform,
            config=config or {},
        )
        db.session.add(task)
        db.session.commit()

        logger.info("Created lead task: %s for tenant: %s", task.id, tenant_id)
        return LeadTaskService._task_to_dict(task)

    @staticmethod
    def run_task(tenant_id: str, task_id: str) -> bool:
        """
        Start execution of a task.
        Triggers the Celery async task.

        Args:
            tenant_id: The tenant ID
            task_id: Task ID to run

        Returns:
            True if task was started, False otherwise
        """
        task = db.session.query(LeadTask).filter_by(id=task_id, tenant_id=tenant_id).first()

        if not task:
            return False

        if task.status not in (LeadTaskStatus.PENDING, LeadTaskStatus.FAILED):
            return False

        task.status = LeadTaskStatus.RUNNING
        task.error_message = None
        db.session.commit()

        # Import here to avoid circular imports
        from tasks.lead_crawl_task import crawl_lead_task

        crawl_lead_task.delay(task_id)

        logger.info("Started lead task: %s", task_id)
        return True

    @staticmethod
    def update_task(
        tenant_id: str,
        task_id: str,
        name: str | None = None,
        platform: str | None = None,
        config: dict | None = None,
    ) -> dict[str, Any] | None:
        """
        Update task name, platform and/or configuration.

        Args:
            tenant_id: The tenant ID
            task_id: Task ID to update
            name: New task name (optional)
            platform: New platform (optional)
            config: New task configuration (optional)

        Returns:
            Updated task as dictionary, or None if not found
        """
        task = db.session.query(LeadTask).filter_by(id=task_id, tenant_id=tenant_id).first()

        if not task:
            return None

        # Only allow editing pending or failed tasks
        if task.status not in (LeadTaskStatus.PENDING, LeadTaskStatus.FAILED, LeadTaskStatus.COMPLETED):
            return None

        if name is not None:
            task.name = name
        if platform is not None:
            valid_platforms = [p.value for p in SupportedPlatform]
            if platform in valid_platforms:
                task.platform = platform
        if config is not None:
            task.config = config

        db.session.commit()
        logger.info("Updated lead task: %s", task_id)
        return LeadTaskService._task_to_dict(task)

    @staticmethod
    def restart_task(tenant_id: str, task_id: str, clear_leads: bool = False) -> bool:
        """
        Restart a completed or failed task.

        Args:
            tenant_id: The tenant ID
            task_id: Task ID to restart
            clear_leads: If True, delete existing leads before restarting

        Returns:
            True if task was restarted, False otherwise
        """
        task = db.session.query(LeadTask).filter_by(id=task_id, tenant_id=tenant_id).first()

        if not task:
            return False

        # Only allow restarting completed or failed tasks
        if task.status not in (LeadTaskStatus.COMPLETED, LeadTaskStatus.FAILED):
            return False

        # Optionally clear existing leads
        if clear_leads:
            deleted_count = db.session.query(Lead).filter_by(task_id=task_id).delete()
            logger.info("Cleared %s leads for task: %s", deleted_count, task_id)
            task.total_leads = 0

        # Reset task status
        task.status = LeadTaskStatus.RUNNING
        task.error_message = None
        task.result_summary = None
        db.session.commit()

        # Trigger async task
        from tasks.lead_crawl_task import crawl_lead_task

        crawl_lead_task.delay(task_id)

        logger.info("Restarted lead task: %s (clear_leads=%s)", task_id, clear_leads)
        return True

    @staticmethod
    def delete_task(tenant_id: str, task_id: str) -> bool:
        """Delete a task and its associated leads."""
        task = db.session.query(LeadTask).filter_by(id=task_id, tenant_id=tenant_id).first()

        if not task:
            return False

        # Delete associated leads
        db.session.query(Lead).filter_by(task_id=task_id).delete()
        db.session.delete(task)
        db.session.commit()

        logger.info("Deleted lead task: %s", task_id)
        return True

    @staticmethod
    def update_task_status(
        task_id: str,
        status: LeadTaskStatus,
        result_summary: dict | None = None,
        error_message: str | None = None,
        total_leads: int | None = None,
    ) -> None:
        """Update task status and results."""
        task = db.session.query(LeadTask).filter_by(id=task_id).first()
        if task:
            task.status = status
            if result_summary is not None:
                task.result_summary = result_summary
            if error_message is not None:
                task.error_message = error_message
            if total_leads is not None:
                task.total_leads = total_leads
            db.session.commit()

    @staticmethod
    def _task_to_dict(task: LeadTask) -> dict[str, Any]:
        """Convert task model to dictionary."""
        return {
            "id": task.id,
            "tenant_id": task.tenant_id,
            "name": task.name,
            "platform": task.platform,
            "task_type": task.task_type,
            "status": task.status,
            "config": task.config,
            "result_summary": task.result_summary,
            "error_message": task.error_message,
            "total_leads": task.total_leads,
            "created_by": task.created_by,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }


class LeadTaskRunService:
    """Service for managing task execution runs."""

    @staticmethod
    def create_run(task_id: str, config_snapshot: dict | None = None) -> LeadTaskRun:
        """Create a new task run record."""
        # Get next run number
        max_run = db.session.query(func.max(LeadTaskRun.run_number)).filter(
            LeadTaskRun.task_id == task_id
        ).scalar() or 0

        run = LeadTaskRun(
            task_id=task_id,
            run_number=max_run + 1,
            config_snapshot=config_snapshot,
        )
        db.session.add(run)
        db.session.commit()
        logger.info("Created task run %s for task %s (run #%s)", run.id, task_id, run.run_number)
        return run

    @staticmethod
    def complete_run(
        run_id: str,
        status: str = "completed",
        total_crawled: int = 0,
        total_created: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Mark a task run as completed."""
        run = db.session.query(LeadTaskRun).filter_by(id=run_id).first()
        if run:
            run.status = status
            run.completed_at = func.current_timestamp()
            run.total_crawled = total_crawled
            run.total_created = total_created
            if error_message:
                run.error_message = error_message
            db.session.commit()

    @staticmethod
    def get_task_runs(task_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get execution history for a task."""
        runs = db.session.query(LeadTaskRun).filter_by(
            task_id=task_id
        ).order_by(LeadTaskRun.started_at.desc()).limit(limit).all()

        return [
            {
                "id": run.id,
                "run_number": run.run_number,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "total_crawled": run.total_crawled,
                "total_created": run.total_created,
                "config_snapshot": run.config_snapshot,
                "error_message": run.error_message,
            }
            for run in runs
        ]

    @staticmethod
    def get_latest_run(task_id: str) -> dict[str, Any] | None:
        """Get the most recent run for a task."""
        run = db.session.query(LeadTaskRun).filter_by(
            task_id=task_id
        ).order_by(LeadTaskRun.started_at.desc()).first()

        if not run:
            return None

        return {
            "id": run.id,
            "run_number": run.run_number,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "total_crawled": run.total_crawled,
            "total_created": run.total_created,
            "config_snapshot": run.config_snapshot,
            "error_message": run.error_message,
        }


class LeadService:
    """Service for managing leads (potential customers)."""

    @staticmethod
    def get_leads(
        tenant_id: str,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
        min_intent: int | None = None,
        task_id: str | None = None,
        task_run_id: str | None = None,
        keyword: str | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """
        Get paginated list of leads.

        Args:
            tenant_id: The tenant ID
            page: Page number (1-indexed)
            limit: Items per page
            status: Optional status filter
            min_intent: Minimum intent score filter
            task_id: Optional task ID filter
            task_run_id: Optional task run ID filter
            keyword: Optional keyword search
            platform: Optional platform filter

        Returns:
            Dictionary with data, total, page, and has_more
        """
        with Session(db.engine) as session:
            query = select(Lead).where(Lead.tenant_id == tenant_id)

            if status:
                query = query.where(Lead.status == status)
            if min_intent is not None:
                query = query.where(Lead.intent_score >= min_intent)
            if task_id:
                query = query.where(Lead.task_id == task_id)
            if task_run_id:
                query = query.where(Lead.task_run_id == task_run_id)
            if platform:
                query = query.where(Lead.platform == platform)
            if keyword:
                query = query.where(Lead.nickname.ilike(f"%{keyword}%") | Lead.comment_content.ilike(f"%{keyword}%"))

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total = session.scalar(count_query) or 0

            # Get paginated results
            query = query.order_by(Lead.intent_score.desc(), Lead.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)
            leads = session.scalars(query).all()

            return {
                "data": [LeadService._lead_to_dict(lead) for lead in leads],
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": total > page * limit,
            }

    @staticmethod
    def get_lead(tenant_id: str, lead_id: str) -> dict[str, Any] | None:
        """Get a single lead by ID."""
        lead = db.session.query(Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()

        if not lead:
            return None
        return LeadService._lead_to_dict(lead)

    @staticmethod
    def create_lead(
        tenant_id: str,
        task_id: str | None = None,
        **kwargs,
    ) -> Lead:
        """Create a new lead."""
        lead = Lead(
            tenant_id=tenant_id,
            task_id=task_id,
            **kwargs,
        )
        db.session.add(lead)
        db.session.commit()
        return lead

    @staticmethod
    def create_leads_batch(
        tenant_id: str,
        task_id: str,
        leads_data: list[dict],
        task_run_id: str | None = None,
    ) -> int:
        """
        Batch create leads with deduplication.

        Args:
            tenant_id: The tenant ID
            task_id: Task ID
            leads_data: List of lead data dictionaries
            task_run_id: Optional task run ID for tracking execution history

        Returns:
            Number of leads created
        """
        created_count = 0

        for data in leads_data:
            platform_user_id = data.get("platform_user_id")
            platform = data.get("platform", "douyin")

            # Auto-generate reply_url if missing but video_id and comment_id exist
            reply_url = data.get("reply_url")
            if not reply_url:
                video_id = data.get("platform_video_id")
                comment_id = data.get("platform_comment_id")
                if video_id and comment_id:
                    reply_url = LeadService._build_reply_url(platform, video_id, comment_id)

            # Check for existing lead
            existing = (
                db.session.query(Lead)
                .filter_by(
                    tenant_id=tenant_id,
                    platform=platform,
                    platform_user_id=platform_user_id,
                )
                .first()
            )

            if existing:
                # Update existing lead with new task/run reference
                existing.task_id = task_id
                if task_run_id:
                    existing.task_run_id = task_run_id
                if data.get("comment_content"):
                    existing.comment_content = data["comment_content"]
                if data.get("source_video_url"):
                    existing.source_video_url = data["source_video_url"]
                if data.get("source_video_title"):
                    existing.source_video_title = data["source_video_title"]
                # Update platform-specific IDs
                if data.get("platform_comment_id"):
                    existing.platform_comment_id = data["platform_comment_id"]
                if data.get("platform_video_id"):
                    existing.platform_video_id = data["platform_video_id"]
                if data.get("platform_user_sec_uid"):
                    existing.platform_user_sec_uid = data["platform_user_sec_uid"]
                # Always update reply_url (auto-generated or from data)
                if reply_url:
                    existing.reply_url = reply_url
            else:
                # Create new lead
                lead = Lead(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    task_run_id=task_run_id,
                    platform=platform,
                    platform_user_id=platform_user_id,
                    nickname=data.get("nickname"),
                    avatar_url=data.get("avatar_url"),
                    region=data.get("region"),
                    comment_content=data.get("comment_content"),
                    source_video_url=data.get("source_video_url"),
                    source_video_title=data.get("source_video_title"),
                    platform_comment_id=data.get("platform_comment_id"),
                    platform_video_id=data.get("platform_video_id"),
                    platform_user_sec_uid=data.get("platform_user_sec_uid"),
                    reply_url=reply_url,
                )
                db.session.add(lead)
                created_count += 1

        db.session.commit()
        return created_count

    @staticmethod
    def update_lead(
        tenant_id: str,
        lead_id: str,
        **kwargs,
    ) -> dict[str, Any] | None:
        """Update a lead."""
        lead = db.session.query(Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()

        if not lead:
            return None

        # Update allowed fields
        allowed_fields = ["status", "intent_score", "intent_tags", "intent_reason"]
        for field in allowed_fields:
            if field in kwargs:
                setattr(lead, field, kwargs[field])

        # Handle status change to contacted
        if kwargs.get("status") == LeadStatus.CONTACTED and not lead.contacted_at:
            from libs.datetime_utils import naive_utc_now

            lead.contacted_at = naive_utc_now()

        db.session.commit()
        return LeadService._lead_to_dict(lead)

    @staticmethod
    def update_lead_intent(
        lead_id: str,
        intent_score: int,
        intent_tags: list[str] | None = None,
        intent_reason: str | None = None,
    ) -> None:
        """Update lead intent analysis results."""
        lead = db.session.query(Lead).filter_by(id=lead_id).first()
        if lead:
            lead.intent_score = intent_score
            if intent_tags is not None:
                lead.intent_tags = intent_tags
            if intent_reason is not None:
                lead.intent_reason = intent_reason
            db.session.commit()

    @staticmethod
    def get_stats(tenant_id: str) -> dict[str, Any]:
        """Get lead statistics for a tenant."""
        with Session(db.engine) as session:
            total = session.scalar(select(func.count()).where(Lead.tenant_id == tenant_id)) or 0

            new_count = (
                session.scalar(select(func.count()).where(Lead.tenant_id == tenant_id, Lead.status == LeadStatus.NEW))
                or 0
            )

            contacted_count = (
                session.scalar(
                    select(func.count()).where(Lead.tenant_id == tenant_id, Lead.status == LeadStatus.CONTACTED)
                )
                or 0
            )

            converted_count = (
                session.scalar(
                    select(func.count()).where(Lead.tenant_id == tenant_id, Lead.status == LeadStatus.CONVERTED)
                )
                or 0
            )

            high_intent_count = (
                session.scalar(select(func.count()).where(Lead.tenant_id == tenant_id, Lead.intent_score >= 60)) or 0
            )

            return {
                "total": total,
                "new": new_count,
                "contacted": contacted_count,
                "converted": converted_count,
                "high_intent": high_intent_count,
            }

    @staticmethod
    def _build_reply_url(platform: str, video_id: str, comment_id: str) -> str | None:
        """Build a reply URL based on platform, video ID, and comment ID."""
        if not video_id or not comment_id:
            return None

        # Link to the video page - user can find and reply to the comment
        # Note: Douyin web doesn't support direct comment linking
        platform_urls = {
            "douyin": f"https://www.douyin.com/video/{video_id}",
            "xiaohongshu": f"https://www.xiaohongshu.com/explore/{video_id}",
            "kuaishou": f"https://www.kuaishou.com/short-video/{video_id}",
            "bilibili": f"https://www.bilibili.com/video/{video_id}",
            "weibo": f"https://weibo.com/detail/{video_id}",
        }
        return platform_urls.get(platform)

    @staticmethod
    def _build_profile_url(platform: str, sec_uid: str | None) -> str | None:
        """Build user profile URL for direct messaging."""
        if not sec_uid:
            return None

        platform_urls = {
            "douyin": f"https://www.douyin.com/user/{sec_uid}",
            "xiaohongshu": f"https://www.xiaohongshu.com/user/profile/{sec_uid}",
            "kuaishou": f"https://www.kuaishou.com/profile/{sec_uid}",
            "bilibili": f"https://space.bilibili.com/{sec_uid}",
            "weibo": f"https://weibo.com/u/{sec_uid}",
        }
        return platform_urls.get(platform)

    @staticmethod
    def _lead_to_dict(lead: Lead) -> dict[str, Any]:
        """Convert lead model to dictionary."""
        # Generate profile URL for DM functionality
        profile_url = LeadService._build_profile_url(lead.platform, lead.platform_user_sec_uid)

        return {
            "id": lead.id,
            "tenant_id": lead.tenant_id,
            "task_id": lead.task_id,
            "task_run_id": lead.task_run_id,
            "platform": lead.platform,
            "platform_user_id": lead.platform_user_id,
            "platform_comment_id": lead.platform_comment_id,
            "platform_video_id": lead.platform_video_id,
            "platform_user_sec_uid": lead.platform_user_sec_uid,
            "nickname": lead.nickname,
            "avatar_url": lead.avatar_url,
            "region": lead.region,
            "comment_content": lead.comment_content,
            "source_video_url": lead.source_video_url,
            "source_video_title": lead.source_video_title,
            "reply_url": lead.reply_url,
            "replied_at": lead.replied_at.isoformat() if lead.replied_at else None,
            "reply_content": lead.reply_content,
            "profile_url": profile_url,
            "intent_score": lead.intent_score,
            "intent_tags": lead.intent_tags,
            "intent_reason": lead.intent_reason,
            "status": lead.status,
            "contacted_at": lead.contacted_at.isoformat() if lead.contacted_at else None,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
        }
