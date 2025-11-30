"""
Lead crawling Celery task.
Handles asynchronous execution of lead acquisition tasks.
"""

import logging
import time
from dataclasses import asdict

import click
from celery import shared_task

from extensions.ext_database import db
from models.leads import LeadTask, LeadTaskStatus
from services.leads.crawler_service import (
    CrawledComment,
    CrawlerServiceError,
    create_crawler_service,
)
from services.leads.intent_analysis_service import (
    IntentAnalysisError,
    IntentAnalysisService,
)
from services.leads_service import LeadService, LeadTaskService

logger = logging.getLogger(__name__)


@shared_task(queue="dataset")
def crawl_lead_task(task_id: str):
    """
    Async task to crawl leads from social media platforms.

    This task:
    1. Fetches the task configuration
    2. Calls the crawler service (MediaCrawler integration)
    3. Stores the crawled leads in the database
    4. Optionally triggers intent analysis
    5. Updates task status

    Args:
        task_id: The lead task ID to execute

    Usage:
        crawl_lead_task.delay(task_id)
    """
    logger.info(click.style("Starting lead crawl task: %s", fg="green"), task_id)
    start_time = time.perf_counter()

    task = db.session.query(LeadTask).filter_by(id=task_id).first()
    if not task:
        logger.error(click.style("Lead task not found: %s", fg="red"), task_id)
        return

    if task.status != LeadTaskStatus.RUNNING:
        logger.warning("Task %s is not in running status, skipping", task_id)
        return

    try:
        config = task.config or {}
        tenant_id = task.tenant_id

        # Extract configuration
        video_urls = config.get("video_urls", [])
        keywords = config.get("keywords", [])
        max_comments = config.get("max_comments", 500)

        # Get platform from task (default to douyin)
        platform = task.platform or "douyin"
        logger.info(
            "Task config: platform=%s, videos=%s, keywords=%s, max=%s",
            platform, len(video_urls), keywords, max_comments
        )

        # Crawl leads using MediaCrawler service
        crawled_leads = _crawl_leads(video_urls, keywords, config.get("city"), max_comments, platform)

        # Store leads in database
        if crawled_leads:
            created_count = LeadService.create_leads_batch(
                tenant_id=tenant_id,
                task_id=task_id,
                leads_data=crawled_leads,
            )
            logger.info("Created %s leads for task %s", created_count, task_id)
        else:
            created_count = 0

        # Update task as completed
        elapsed = time.perf_counter() - start_time
        LeadTaskService.update_task_status(
            task_id=task_id,
            status=LeadTaskStatus.COMPLETED,
            result_summary={
                "total_crawled": len(crawled_leads),
                "total_created": created_count,
                "elapsed_seconds": round(elapsed, 2),
            },
            total_leads=created_count,
        )

        logger.info(
            click.style("Lead task completed: %s, created %s leads in %.2fs", fg="green"),
            task_id,
            created_count,
            elapsed,
        )

    except Exception as e:
        logger.exception("Lead task failed: %s", task_id)
        LeadTaskService.update_task_status(
            task_id=task_id,
            status=LeadTaskStatus.FAILED,
            error_message=str(e),
        )
        raise


def _crawl_leads(
    video_urls: list[str],
    keywords: list[str],
    city: str | None,
    max_comments: int,
    platform: str = "douyin",
) -> list[dict]:
    """
    Crawl leads from social media platform using MediaCrawler service.

    Args:
        video_urls: List of video URLs to crawl
        keywords: Keywords for search-based crawling
        city: Target city for filtering
        max_comments: Maximum comments to crawl
        platform: Target platform (douyin, xiaohongshu, kuaishou, bilibili, weibo)

    Returns:
        List of lead data dictionaries
    """
    try:
        crawler = create_crawler_service()
    except CrawlerServiceError as e:
        logger.warning("Crawler service not available: %s", e)
        return []

    all_comments: list[CrawledComment] = []

    # Crawl by video URLs
    if video_urls:
        comments_per_video = max_comments // len(video_urls) if video_urls else max_comments
        for url in video_urls:
            try:
                comments = crawler.crawl_video_comments(
                    video_url=url,
                    platform=platform,
                    max_comments=comments_per_video,
                )
                all_comments.extend(comments)
                logger.info("Crawled %s comments from %s on %s", len(comments), url, platform)
            except CrawlerServiceError as e:
                logger.warning("Failed to crawl video %s: %s", url, e)
                continue

    # Crawl by keywords
    if keywords:
        try:
            keyword_comments = crawler.crawl_search_comments(
                keywords=keywords,
                platform=platform,
                city=city,
                max_videos=10,
                max_comments_per_video=max_comments // len(keywords) if keywords else 50,
            )
            all_comments.extend(keyword_comments)
            logger.info("Crawled %s comments from %s keyword search", len(keyword_comments), platform)
        except CrawlerServiceError as e:
            logger.warning("Keyword search failed: %s", e)

    # Convert to dictionary format for database storage
    return [_comment_to_dict(c) for c in all_comments]


def _comment_to_dict(comment: CrawledComment) -> dict:
    """Convert CrawledComment to dictionary for database storage."""
    return asdict(comment)


@shared_task(queue="dataset")
def analyze_lead_intent(lead_id: str):
    """
    Async task to analyze lead intent using AI.

    This task calls Dify's workflow API to analyze the lead's
    comment content and determine purchase intent.

    Args:
        lead_id: The lead ID to analyze

    Usage:
        analyze_lead_intent.delay(lead_id)
    """
    from models.leads import Lead

    logger.info("Analyzing intent for lead: %s", lead_id)

    # Check if analysis is configured
    if not IntentAnalysisService.is_configured():
        logger.info("Intent analysis not configured, skipping lead: %s", lead_id)
        return

    # Fetch the lead
    lead = db.session.query(Lead).filter_by(id=lead_id).first()
    if not lead:
        logger.warning("Lead not found: %s", lead_id)
        return

    if not lead.comment_content:
        logger.info("Lead %s has no comment content, skipping", lead_id)
        return

    try:
        # Analyze the comment
        result = IntentAnalysisService.analyze_comment(
            tenant_id=lead.tenant_id,
            comment=lead.comment_content,
            additional_context={
                "source_video_title": lead.source_video_title or "",
                "region": lead.region or "",
            },
        )

        # Update lead with analysis results
        LeadService.update_lead_intent(
            lead_id=lead_id,
            intent_score=result.score,
            intent_tags=result.tags,
            intent_reason=result.reason,
        )

        logger.info("Intent analysis completed for lead %s: score=%s, tags=%s", lead_id, result.score, result.tags)

    except IntentAnalysisError as e:
        logger.warning("Intent analysis failed for lead %s: %s", lead_id, e)


@shared_task(queue="dataset")
def batch_analyze_leads_intent(task_id: str):
    """
    Async task to analyze intent for all leads in a task.

    Args:
        task_id: The task ID whose leads should be analyzed

    Usage:
        batch_analyze_leads_intent.delay(task_id)
    """
    from models.leads import Lead

    logger.info("Batch analyzing intent for task: %s", task_id)

    # Check if analysis is configured
    if not IntentAnalysisService.is_configured():
        logger.info("Intent analysis not configured, skipping batch analysis")
        return

    # Fetch all leads for this task that haven't been analyzed
    leads = (
        db.session.query(Lead)
        .filter(
            Lead.task_id == task_id,
            Lead.intent_score == 0,  # Only analyze leads without scores
            Lead.comment_content.isnot(None),
        )
        .all()
    )

    logger.info("Found %s leads to analyze for task %s", len(leads), task_id)

    # Queue individual analysis tasks
    for lead in leads:
        analyze_lead_intent.delay(lead.id)

    logger.info("Queued %s intent analysis tasks for task %s", len(leads), task_id)
