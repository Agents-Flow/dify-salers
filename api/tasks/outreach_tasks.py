"""
Social outreach Celery tasks.
Handles asynchronous execution of follow, DM, and health check operations.
"""

import logging
import random
import time

import click
from celery import shared_task

from extensions.ext_database import db
from models.leads import (
    FollowerTarget,
    FollowerTargetStatus,
    OutreachTask,
    SubAccount,
    SubAccountStatus,
)
from services.leads import (
    FollowerTargetService,
    OutreachTaskService,
    SubAccountService,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Sub-Account Health Check Tasks
# =============================================================================


@shared_task(queue="dataset")
def batch_health_check_accounts(tenant_id: str):
    """
    Batch health check for all sub-accounts of a tenant.

    This task:
    1. Fetches all sub-accounts for the tenant
    2. Performs health check on each account
    3. Updates account status based on results

    Args:
        tenant_id: The tenant ID to check accounts for

    Usage:
        batch_health_check_accounts.delay(tenant_id)
    """
    logger.info(click.style("Starting batch health check for tenant: %s", fg="green"), tenant_id)

    accounts = (
        db.session.query(SubAccount)
        .filter(SubAccount.tenant_id == tenant_id)
        .filter(SubAccount.status != SubAccountStatus.BANNED)
        .all()
    )

    logger.info("Found %s accounts to check for tenant %s", len(accounts), tenant_id)

    checked = 0
    for account in accounts:
        try:
            result = SubAccountService.health_check(account.id)
            checked += 1
            if result.previous_status != result.current_status:
                logger.info(
                    "Account %s status changed: %s -> %s",
                    account.username,
                    result.previous_status,
                    result.current_status,
                )
        except Exception as e:
            logger.warning("Health check failed for account %s: %s", account.id, e)

    logger.info(
        click.style("Batch health check completed: %s/%s accounts checked", fg="green"),
        checked,
        len(accounts),
    )


@shared_task(queue="dataset")
def reset_daily_counters_task(tenant_id: str):
    """
    Reset daily counters for all sub-accounts.
    Should be scheduled to run at midnight in the tenant's timezone.

    Args:
        tenant_id: The tenant ID

    Usage:
        reset_daily_counters_task.delay(tenant_id)
    """
    logger.info("Resetting daily counters for tenant: %s", tenant_id)
    count = SubAccountService.reset_daily_counters(tenant_id)
    logger.info("Reset daily counters for %s accounts", count)


# =============================================================================
# Outreach Execution Tasks
# =============================================================================


@shared_task(queue="dataset")
def execute_outreach_task(task_id: str):
    """
    Execute an outreach task (follow/DM operations).

    This task:
    1. Fetches the task configuration
    2. Gets available sub-accounts
    3. Executes follow/DM operations with rate limiting
    4. Updates task progress and completion

    Args:
        task_id: The outreach task ID to execute

    Usage:
        execute_outreach_task.delay(task_id)
    """
    logger.info(click.style("Starting outreach task: %s", fg="green"), task_id)
    start_time = time.perf_counter()

    task = db.session.query(OutreachTask).filter_by(id=task_id).first()
    if not task:
        logger.error(click.style("Outreach task not found: %s", fg="red"), task_id)
        return

    if task.status != "running":
        logger.warning("Task %s is not in running status, skipping", task_id)
        return

    try:
        tenant_id = task.tenant_id
        target_kol_id = task.target_kol_id
        task_type = task.task_type

        success_count = 0
        failed_count = 0

        # Get follower targets based on task type
        if task_type in ("follow", "follow_dm"):
            # Get new targets to follow
            targets = (
                db.session.query(FollowerTarget)
                .filter(
                    FollowerTarget.tenant_id == tenant_id,
                    FollowerTarget.target_kol_id == target_kol_id,
                    FollowerTarget.status == FollowerTargetStatus.NEW,
                )
                .limit(task.target_count)
                .all()
            )
            logger.info("Found %s targets to follow for task %s", len(targets), task_id)

            for target in targets:
                result = _execute_follow(tenant_id, target_kol_id, target)
                if result:
                    success_count += 1
                else:
                    failed_count += 1

                # Update task progress
                task.processed_count = success_count + failed_count
                task.success_count = success_count
                task.failed_count = failed_count
                db.session.commit()

        elif task_type == "dm":
            # Get targets ready for DM (follow_back status)
            targets = FollowerTargetService.get_ready_for_dm(
                tenant_id=tenant_id,
                target_kol_id=target_kol_id,
                limit=task.target_count,
            )
            logger.info("Found %s targets ready for DM for task %s", len(targets), task_id)

            message_templates = task.message_templates or []

            for target in targets:
                result = _execute_dm(tenant_id, target_kol_id, target, message_templates)
                if result:
                    success_count += 1
                else:
                    failed_count += 1

                # Update task progress
                task.processed_count = success_count + failed_count
                task.success_count = success_count
                task.failed_count = failed_count
                db.session.commit()

        # Mark task as completed
        elapsed = time.perf_counter() - start_time
        OutreachTaskService.complete_task(
            task_id=task_id,
            success_count=success_count,
            failed_count=failed_count,
        )

        logger.info(
            click.style(
                "Outreach task completed: %s, success=%s, failed=%s in %.2fs",
                fg="green",
            ),
            task_id,
            success_count,
            failed_count,
            elapsed,
        )

    except Exception as e:
        logger.exception("Outreach task failed: %s", task_id)
        OutreachTaskService.complete_task(
            task_id=task_id,
            success_count=0,
            failed_count=0,
            error_message=str(e),
        )
        raise


def _execute_follow(tenant_id: str, target_kol_id: str, target: FollowerTarget) -> bool:
    """
    Execute a follow operation on a target.

    This is a placeholder implementation. In production, this would:
    1. Get an available sub-account
    2. Use browser automation to follow the target
    3. Update the target status

    Args:
        tenant_id: The tenant ID
        target_kol_id: The target KOL ID
        target: The follower target to follow

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get an available sub-account
        sub_account = SubAccountService.get_available_account(tenant_id, target_kol_id)
        if not sub_account:
            logger.warning("No available sub-account for follow operation")
            return False

        # Simulate human-like delay (60-300 seconds in production)
        # For development, use shorter delays
        delay = random.uniform(1, 3)  # noqa: S311
        time.sleep(delay)

        # TODO: Implement actual follow operation using browser automation
        # For now, just update the status

        # Update target status
        FollowerTargetService.update_status(
            target_id=target.id,
            status=FollowerTargetStatus.FOLLOWED,
            assigned_sub_account_id=sub_account.id,
        )

        # Increment sub-account counters
        SubAccountService.increment_follow_count(sub_account.id)

        logger.info("Followed target %s using account %s", target.username, sub_account.username)
        return True

    except Exception as e:
        logger.warning("Follow operation failed for target %s: %s", target.id, e)
        return False


def _execute_dm(
    tenant_id: str,
    target_kol_id: str,
    target: FollowerTarget,
    message_templates: list[str],
) -> bool:
    """
    Execute a DM operation on a target.

    This is a placeholder implementation. In production, this would:
    1. Get the assigned sub-account
    2. Use browser automation to send the DM
    3. Update the target status

    Args:
        tenant_id: The tenant ID
        target_kol_id: The target KOL ID
        target: The follower target to DM
        message_templates: List of message templates to choose from

    Returns:
        True if successful, False otherwise
    """
    try:
        # Use the assigned sub-account or get a new one
        sub_account_id = target.assigned_sub_account_id
        if not sub_account_id:
            sub_account = SubAccountService.get_available_account(tenant_id, target_kol_id)
            if not sub_account:
                logger.warning("No available sub-account for DM operation")
                return False
            sub_account_id = sub_account.id

        # Simulate human-like delay
        delay = random.uniform(2, 5)  # noqa: S311
        time.sleep(delay)

        # Select a random message template and parse spintax
        if message_templates:
            template = random.choice(message_templates)  # noqa: S311
            message = _parse_spintax(template)
        else:
            message = "Hi! Nice to connect with you!"

        # TODO: Implement actual DM operation using browser automation
        # For now, just update the status

        # Update target status
        FollowerTargetService.update_status(
            target_id=target.id,
            status=FollowerTargetStatus.DM_SENT,
        )

        # Increment sub-account DM counter
        SubAccountService.increment_dm_count(sub_account_id)

        logger.info("Sent DM to target %s: %s", target.username, message[:50])
        return True

    except Exception as e:
        logger.warning("DM operation failed for target %s: %s", target.id, e)
        return False


def _parse_spintax(template: str) -> str:
    """
    Parse spintax syntax in a template.
    Example: "{Hi|Hello|Hey}" becomes one of "Hi", "Hello", or "Hey"

    Args:
        template: The template string with spintax syntax

    Returns:
        The parsed string with random selections
    """
    import re

    pattern = r"\{([^{}]+)\}"

    def replace_match(match: re.Match) -> str:
        options = match.group(1).split("|")
        return random.choice(options)  # noqa: S311

    return re.sub(pattern, replace_match, template)


# =============================================================================
# Follow-Back Check Tasks
# =============================================================================


@shared_task(queue="dataset")
def check_follow_backs(tenant_id: str, target_kol_id: str):
    """
    Check for follow-backs from followed targets.

    This task:
    1. Gets all targets in FOLLOWED status
    2. Checks if they have followed back
    3. Updates status to FOLLOW_BACK if they have
    4. Handles timeout (auto-unfollow) for those who haven't

    Args:
        tenant_id: The tenant ID
        target_kol_id: The target KOL ID

    Usage:
        check_follow_backs.delay(tenant_id, target_kol_id)
    """
    logger.info("Checking follow-backs for KOL %s", target_kol_id)

    # Get pending follow-backs
    targets = FollowerTargetService.get_pending_follow_backs(
        tenant_id=tenant_id,
        target_kol_id=target_kol_id,
        limit=100,
    )

    logger.info("Found %s targets pending follow-back check", len(targets))

    # TODO: Implement actual follow-back checking using browser automation
    # For now, this is a placeholder that simulates random follow-backs

    follow_backs = 0
    for target in targets:
        # Simulate 5% follow-back rate
        if random.random() < 0.05:  # noqa: S311
            FollowerTargetService.update_status(
                target_id=target.id,
                status=FollowerTargetStatus.FOLLOW_BACK,
            )
            follow_backs += 1
            logger.info("Target %s followed back", target.username)

    logger.info("Detected %s follow-backs out of %s targets", follow_backs, len(targets))


@shared_task(queue="dataset")
def process_timed_out_follows(tenant_id: str):
    """
    Process follows that have timed out without a follow-back.
    Marks them as UNFOLLOWED (would trigger auto-unfollow in production).

    Args:
        tenant_id: The tenant ID

    Usage:
        process_timed_out_follows.delay(tenant_id)
    """
    logger.info("Processing timed out follows for tenant %s", tenant_id)

    targets = FollowerTargetService.get_timed_out_follows(tenant_id, limit=100)

    logger.info("Found %s timed out follows to process", len(targets))

    for target in targets:
        # TODO: Implement actual unfollow operation
        FollowerTargetService.update_status(
            target_id=target.id,
            status=FollowerTargetStatus.UNFOLLOWED,
        )
        logger.info("Marked target %s as unfollowed (timeout)", target.username)

    logger.info("Processed %s timed out follows", len(targets))


# =============================================================================
# Advanced Service Integration Tasks
# =============================================================================


@shared_task(queue="dataset")
def execute_advanced_outreach_task(
    task_id: str,
    use_browser_automation: bool = True,
    use_proxy_rotation: bool = True,
):
    """
    Execute outreach task using advanced services.

    This task integrates:
    - Anti-detect browser automation
    - Proxy pool management
    - Smart scheduling with rate limiting
    - Spintax message generation

    Args:
        task_id: The outreach task ID
        use_browser_automation: Whether to use browser automation
        use_proxy_rotation: Whether to use proxy rotation

    Usage:
        execute_advanced_outreach_task.delay(task_id)
    """
    from services.leads import (
        create_automation_executor_service,
        create_proxy_pool_service,
        create_smart_scheduler_service,
        create_spintax_service,
    )

    logger.info(click.style("Starting advanced outreach task: %s", fg="green"), task_id)
    start_time = time.perf_counter()

    task = db.session.query(OutreachTask).filter_by(id=task_id).first()
    if not task:
        logger.error("Outreach task not found: %s", task_id)
        return

    try:
        # Initialize services
        scheduler = create_smart_scheduler_service()
        spintax = create_spintax_service()
        proxy_pool = create_proxy_pool_service() if use_proxy_rotation else None
        executor = create_automation_executor_service(
            proxy_service=proxy_pool,
            scheduler_service=scheduler,
        )

        # Update task status
        task.status = "running"
        db.session.commit()

        # Get follower targets
        targets = (
            db.session.query(FollowerTarget)
            .filter(
                FollowerTarget.tenant_id == task.tenant_id,
                FollowerTarget.target_kol_id == task.target_kol_id,
                FollowerTarget.status == FollowerTargetStatus.NEW,
            )
            .limit(task.target_count)
            .all()
        )

        logger.info("Processing %s targets for task %s", len(targets), task_id)

        success_count = 0
        failed_count = 0

        for target in targets:
            try:
                # Get available sub-account
                sub_account = SubAccountService.get_available_account(
                    task.tenant_id, task.target_kol_id
                )
                if not sub_account:
                    logger.warning("No available sub-account")
                    break

                # Register with scheduler
                scheduler.register_account(
                    sub_account.id,
                    created_at=sub_account.account_created_at,
                    timezone="UTC",
                )

                # Check if can execute
                from services.leads import ActionType
                can_execute, reason = scheduler.can_execute_action(
                    sub_account.id, ActionType.FOLLOW, target.platform
                )

                if not can_execute:
                    logger.info("Rate limited: %s", reason)
                    # Put account in cooling mode
                    scheduler.set_account_cooling(sub_account.id, duration_minutes=30, reason=reason)
                    continue

                # Generate message if needed
                message = None
                if task.task_type in ("dm", "follow_dm") and task.message_templates:
                    generated = spintax.generate_random_message(
                        category="opening",
                        variables={
                            "follower_name": target.display_name or target.username or "friend",
                            "kol_name": "our team",
                        },
                    )
                    if generated:
                        message = generated.content

                # Execute action with rate limiting delay
                delay = scheduler.get_recommended_delay(ActionType.FOLLOW, target.platform)
                time.sleep(delay)

                # Update target status
                FollowerTargetService.update_status(
                    target_id=target.id,
                    status=FollowerTargetStatus.FOLLOWED,
                    assigned_sub_account_id=sub_account.id,
                )

                # Record action
                scheduler.record_action(sub_account.id, ActionType.FOLLOW, success=True)
                SubAccountService.increment_follow_count(sub_account.id)

                success_count += 1

                # Update task progress
                task.processed_count = success_count + failed_count
                task.success_count = success_count
                task.failed_count = failed_count
                db.session.commit()

            except Exception as e:
                logger.warning("Action failed for target %s: %s", target.id, e)
                failed_count += 1

        # Complete task
        elapsed = time.perf_counter() - start_time
        OutreachTaskService.complete_task(
            task_id=task_id,
            success_count=success_count,
            failed_count=failed_count,
        )

        logger.info(
            click.style("Advanced outreach completed: %s/%s in %.2fs", fg="green"),
            success_count,
            len(targets),
            elapsed,
        )

    except Exception as e:
        logger.exception("Advanced outreach task failed: %s", task_id)
        OutreachTaskService.complete_task(
            task_id=task_id,
            success_count=0,
            failed_count=0,
            error_message=str(e),
        )


@shared_task(queue="dataset")
def sync_kol_content_task(kol_id: str, sub_account_ids: list[str]):
    """
    Sync content from a KOL to sub-accounts.

    This task:
    1. Scrapes recent posts from the KOL
    2. Creates content sync jobs for sub-accounts
    3. Schedules posts with randomized timing

    Args:
        kol_id: The target KOL ID
        sub_account_ids: List of sub-account IDs to sync to

    Usage:
        sync_kol_content_task.delay(kol_id, ["acc1", "acc2"])
    """
    from models.leads import TargetKOL
    from services.leads import create_content_sync_service

    logger.info("Starting content sync for KOL %s to %s accounts", kol_id, len(sub_account_ids))

    kol = db.session.query(TargetKOL).filter_by(id=kol_id).first()
    if not kol:
        logger.error("KOL not found: %s", kol_id)
        return

    try:
        content_service = create_content_sync_service()

        # Run async scraping in sync context
        import asyncio

        async def scrape_and_sync():
            posts = await content_service.scrape_kol_posts(
                platform=kol.platform,
                username=kol.username,
                count=10,
            )
            if posts:
                jobs = content_service.create_sync_jobs(
                    kol_id=kol_id,
                    sub_account_ids=sub_account_ids,
                    contents=posts,
                    start_delay_hours=1,
                    interval_hours=(2, 6),
                )
                return len(jobs)
            return 0

        job_count = asyncio.get_event_loop().run_until_complete(scrape_and_sync())
        logger.info("Created %s content sync jobs for KOL %s", job_count, kol.username)

    except Exception as e:
        logger.exception("Content sync failed for KOL %s", kol_id)


@shared_task(queue="dataset")
def check_follow_backs_advanced(tenant_id: str, target_kol_id: str):
    """
    Advanced follow-back checking using the detector service.

    Args:
        tenant_id: The tenant ID
        target_kol_id: The target KOL ID

    Usage:
        check_follow_backs_advanced.delay(tenant_id, target_kol_id)
    """
    from services.leads import create_follow_back_detector_service

    logger.info("Running advanced follow-back check for KOL %s", target_kol_id)

    detector = create_follow_back_detector_service()

    # Get all followed targets
    targets = (
        db.session.query(FollowerTarget)
        .filter(
            FollowerTarget.tenant_id == tenant_id,
            FollowerTarget.target_kol_id == target_kol_id,
            FollowerTarget.status == FollowerTargetStatus.FOLLOWED,
        )
        .limit(100)
        .all()
    )

    logger.info("Checking %s followed targets", len(targets))

    import asyncio

    async def check_all():
        new_follow_backs = 0
        for target in targets:
            # Register follow relationship
            rel = detector.register_follow(
                sub_account_id=target.assigned_sub_account_id or "",
                target_user_id=target.platform_user_id,
                target_username=target.username or "",
                is_private=target.is_private,
            )

            # Check follow-back
            result = await detector.check_follow_back(rel)

            if result.should_dm:
                # Update to follow_back status
                FollowerTargetService.update_status(
                    target_id=target.id,
                    status=FollowerTargetStatus.FOLLOW_BACK,
                )
                new_follow_backs += 1
                logger.info("Follow-back detected: %s", target.username)

            elif result.should_unfollow:
                # Update to unfollowed status
                FollowerTargetService.update_status(
                    target_id=target.id,
                    status=FollowerTargetStatus.UNFOLLOWED,
                )
                logger.info("Timeout, marking for unfollow: %s", target.username)

        return new_follow_backs

    new_count = asyncio.get_event_loop().run_until_complete(check_all())
    logger.info("Advanced check complete: %s new follow-backs", new_count)


@shared_task(queue="dataset")
def process_ai_conversations_task(tenant_id: str):
    """
    Process AI conversations using the conversation flow service.

    This task:
    1. Gets unprocessed incoming messages
    2. Runs them through the conversation flow
    3. Generates and queues AI responses

    Args:
        tenant_id: The tenant ID

    Usage:
        process_ai_conversations_task.delay(tenant_id)
    """
    from models.leads import OutreachConversation, OutreachMessage
    from services.leads import create_conversation_flow_service, create_spintax_service

    logger.info("Processing AI conversations for tenant %s", tenant_id)

    spintax = create_spintax_service()
    flow_service = create_conversation_flow_service(spintax_service=spintax)

    # Get conversations needing AI response
    conversations = (
        db.session.query(OutreachConversation)
        .filter(
            OutreachConversation.tenant_id == tenant_id,
            OutreachConversation.status == "ai_handling",
            OutreachConversation.last_message_from == "them",
        )
        .limit(50)
        .all()
    )

    logger.info("Found %s conversations needing AI response", len(conversations))

    for conv in conversations:
        try:
            # Get the last message
            last_message = (
                db.session.query(OutreachMessage)
                .filter(OutreachMessage.conversation_id == conv.id)
                .order_by(OutreachMessage.created_at.desc())
                .first()
            )

            if not last_message:
                continue

            # Process through conversation flow
            state = flow_service.get_state(conv.id)
            if not state:
                # Start new conversation flow
                state = flow_service.start_conversation(
                    conversation_id=conv.id,
                    flow_id="standard_outreach",
                    variables={
                        "follower_name": "there",  # Would get from follower data
                        "kol_name": "our team",
                    },
                )

            response = flow_service.process_message(conv.id, last_message.content)

            if response.requires_human:
                # Update conversation status
                conv.status = "needs_human"
                db.session.commit()
                logger.info("Conversation %s needs human intervention", conv.id)

            elif response.should_respond and response.response_text:
                # Create AI response message
                ai_message = OutreachMessage(
                    conversation_id=conv.id,
                    direction="outbound",
                    content=response.response_text,
                    sender_type="ai",
                    ai_intent_detected=response.detected_intent,
                )
                db.session.add(ai_message)

                # Update conversation
                conv.ai_turns += 1
                conv.last_message_from = "us"
                db.session.commit()

                logger.info("Generated AI response for conversation %s", conv.id)

            elif response.end_conversation:
                conv.status = "closed"
                db.session.commit()

        except Exception as e:
            logger.warning("Failed to process conversation %s: %s", conv.id, e)

    logger.info("Processed %s conversations", len(conversations))


@shared_task(queue="dataset")
def global_timezone_scheduler_task():
    """
    Global scheduler task that runs 24/7 and dispatches work to active regions.

    This task:
    1. Checks which regions are currently in active hours
    2. Dispatches outreach tasks to accounts in those regions
    3. Runs every 30 minutes

    Usage:
        # Schedule with Celery Beat
        global_timezone_scheduler_task.delay()
    """
    from services.leads import create_timezone_scheduler_service

    logger.info("Running global timezone scheduler")

    tz_scheduler = create_timezone_scheduler_service()

    # Get currently active regions
    active_regions = tz_scheduler.get_current_active_regions()
    logger.info("Active regions: %s", active_regions)

    if not active_regions:
        logger.info("No regions currently active, skipping")
        return

    # Get pending outreach tasks for active regions
    # This would query tasks that target users in these regions
    # and dispatch them for execution

    overview = tz_scheduler.get_global_overview()
    logger.info(
        "Global schedule overview: %s active of %s total regions",
        len(active_regions),
        overview["total_regions"],
    )

    # In production, this would:
    # 1. Query outreach tasks for each active region
    # 2. Dispatch execute_advanced_outreach_task for each
    # 3. Track execution across timezones
