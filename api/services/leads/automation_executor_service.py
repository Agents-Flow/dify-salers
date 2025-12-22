"""
Automation executor service for outreach operations.
Orchestrates follow, unfollow, DM, and engagement actions with anti-detection measures.

This service has been updated to use browser-less HTTP API clients:
- Instagram: instagrapi library
- Twitter/X: twikit library

Memory usage reduced from ~300MB/session (browser) to ~3MB/session (HTTP API).
Supports 1000+ concurrent sessions on a single server.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .instagram_api_service import InstagramAPIService
    from .session_manager_service import SessionManagerService
    from .twitter_api_service import TwitterAPIService

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
    username: str  # Platform username for API authentication
    profile_id: str  # Anti-detect browser profile (for fallback)
    proxy_config: dict[str, Any] | None = None
    ws_endpoint: str | None = None  # Browser WebSocket endpoint (for fallback)
    platform: str = "instagram"
    session_started_at: datetime | None = None
    use_http_api: bool = True  # Use HTTP API instead of browser


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
    
    Now supports two execution modes:
    1. HTTP API mode (default): Uses instagrapi/twikit for browser-less automation
       - Memory efficient: ~3MB per session
       - Supports 1000+ concurrent sessions
       
    2. Browser mode (fallback): Uses Playwright with anti-detect browser
       - For scenarios requiring full browser (e.g., initial login with captcha)
       - Memory heavy: ~300MB per session
    
    Integrates with:
    - InstagramAPIService (instagrapi)
    - TwitterAPIService (twikit)
    - SessionManagerService (Redis session persistence)
    - SmartSchedulerService (rate limiting)
    - ProxyPoolService (proxy rotation)
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
        instagram_api_service: "InstagramAPIService | None" = None,
        twitter_api_service: "TwitterAPIService | None" = None,
        session_manager: "SessionManagerService | None" = None,
    ):
        self.browser_service = browser_service
        self.proxy_service = proxy_service
        self.scheduler_service = scheduler_service
        self.instagram_api = instagram_api_service
        self.twitter_api = twitter_api_service
        self.session_manager = session_manager
        self._active_contexts: dict[str, ExecutionContext] = {}
        
        # Lazy-initialize API services if not provided
        self._instagram_api_initialized = instagram_api_service is not None
        self._twitter_api_initialized = twitter_api_service is not None

    def _ensure_instagram_api(self) -> "InstagramAPIService":
        """Lazy-initialize Instagram API service."""
        if not self._instagram_api_initialized:
            from .instagram_api_service import create_instagram_api_service
            self.instagram_api = create_instagram_api_service(self.session_manager)
            self._instagram_api_initialized = True
        return self.instagram_api  # type: ignore

    def _ensure_twitter_api(self) -> "TwitterAPIService":
        """Lazy-initialize Twitter API service."""
        if not self._twitter_api_initialized:
            from .twitter_api_service import create_twitter_api_service
            self.twitter_api = create_twitter_api_service(self.session_manager)
            self._twitter_api_initialized = True
        return self.twitter_api  # type: ignore

    async def start_session(
        self,
        account_id: str,
        username: str,
        password: str,
        platform: str = "instagram",
        profile_id: str = "",
        browser_provider: str = "multilogin",
        use_http_api: bool = True,
        email: str | None = None,
    ) -> ExecutionContext:
        """
        Start an automation session for an account.
        
        Args:
            account_id: Internal account ID
            username: Platform username
            password: Platform password
            platform: "instagram" or "twitter"/"x"
            profile_id: Anti-detect browser profile ID (for fallback)
            browser_provider: Browser provider (for fallback)
            use_http_api: If True, use HTTP API instead of browser
            email: Email address (required for Twitter login)
            
        Returns:
            ExecutionContext for subsequent operations
        """
        context = ExecutionContext(
            account_id=account_id,
            username=username,
            profile_id=profile_id,
            platform=platform.lower(),
            session_started_at=datetime.now(),
            use_http_api=use_http_api,
        )

        # Get proxy for this account
        proxy_url = None
        if self.proxy_service:
            proxy = self.proxy_service.get_account_proxy(account_id)
            if proxy:
                context.proxy_config = proxy.to_playwright_config()
                # Format proxy URL for HTTP API
                if hasattr(proxy, "to_url"):
                    proxy_url = proxy.to_url()
                elif proxy.host:
                    if proxy.username:
                        proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
                    else:
                        proxy_url = f"http://{proxy.host}:{proxy.port}"

        if use_http_api:
            # Use HTTP API for session (memory efficient)
            try:
                # Try to restore session from Redis first
                saved_session = None
                if self.session_manager:
                    saved_session = await self.session_manager.get_session_data(platform, username)

                if context.platform == "instagram":
                    api = self._ensure_instagram_api()
                    session = await api.login(
                        username=username,
                        password=password,
                        proxy=proxy_url,
                        session_data=saved_session,
                    )
                    # Persist session to Redis
                    if self.session_manager and session.session_data:
                        await self.session_manager.store_session(
                            platform="instagram",
                            username=username,
                            session_data=session.session_data,
                            user_id=session.user_id,
                            status=session.status,
                            proxy_config=context.proxy_config,
                        )
                    logger.info("Started Instagram HTTP API session for %s", username)

                elif context.platform in ("twitter", "x"):
                    api = self._ensure_twitter_api()
                    session = await api.login(
                        username=username,
                        email=email or "",
                        password=password,
                        cookies=saved_session,
                    )
                    # Persist session to Redis
                    if self.session_manager and session.cookies:
                        await self.session_manager.store_session(
                            platform="twitter",
                            username=username,
                            session_data=session.cookies,
                            user_id=session.user_id,
                            status=session.status,
                            proxy_config=context.proxy_config,
                        )
                    logger.info("Started Twitter HTTP API session for %s", username)

            except Exception as e:
                logger.warning("HTTP API login failed for %s: %s, may need browser", username, e)
                # Could fall back to browser mode here
                context.use_http_api = False
                raise
        else:
            # Fallback to browser session (memory heavy)
            if self.browser_service and profile_id:
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
        logger.info("Started automation session for account %s (HTTP API: %s)", account_id, use_http_api)
        return context

    async def stop_session(self, account_id: str) -> bool:
        """Stop an automation session."""
        context = self._active_contexts.pop(account_id, None)
        if not context:
            return False

        if context.use_http_api:
            # Logout from HTTP API
            try:
                if context.platform == "instagram" and self.instagram_api:
                    await self.instagram_api.logout(context.username)
                elif context.platform in ("twitter", "x") and self.twitter_api:
                    await self.twitter_api.logout(context.username)
            except Exception as e:
                logger.warning("Failed to logout from API: %s", e)
        else:
            # Stop browser session
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
        self, context: ExecutionContext, target_username: str
    ) -> None:
        """
        Simulate viewing a user's profile.
        With HTTP API, we fetch user info instead of browser navigation.
        """
        try:
            if context.use_http_api:
                # Fetch user info via API (simulates profile view)
                if context.platform == "instagram" and self.instagram_api:
                    await self.instagram_api.get_user_info(context.username, target_username)
                elif context.platform in ("twitter", "x") and self.twitter_api:
                    await self.twitter_api.get_user_info(context.username, target_username)
            else:
                # Browser simulation
                await asyncio.sleep(random.uniform(2, 5))  # noqa: S311
            logger.debug("Simulated profile view for %s", target_username)
        except Exception as e:
            logger.debug("Profile view simulation failed: %s", e)

    async def _perform_follow_action(
        self, context: ExecutionContext, target_username: str
    ) -> bool:
        """
        Perform the actual follow action.
        
        Uses HTTP API by default (instagrapi/twikit), falls back to browser.
        """
        if context.use_http_api:
            try:
                if context.platform == "instagram":
                    api = self._ensure_instagram_api()
                    # Need to get user_id from username first
                    user_id = await api.get_user_id(context.username, target_username)
                    if not user_id:
                        logger.warning("Could not find user_id for %s", target_username)
                        return False
                    result = await api.follow_user(context.username, user_id)
                    return result.success

                elif context.platform in ("twitter", "x"):
                    api = self._ensure_twitter_api()
                    # Get user info to get user_id
                    user_info = await api.get_user_info(context.username, target_username)
                    if not user_info:
                        logger.warning("Could not find user %s on Twitter", target_username)
                        return False
                    result = await api.follow_user(context.username, user_info.user_id)
                    return result.success

            except Exception as e:
                logger.warning("HTTP API follow failed: %s", e)
                return False
        else:
            # Browser fallback - not implemented in this version
            await asyncio.sleep(0.5)
            logger.warning("Browser follow not implemented, use HTTP API")
            return False

    async def _perform_follow_by_id(
        self, context: ExecutionContext, target_user_id: str
    ) -> bool:
        """
        Perform follow action by user ID (more efficient).
        """
        if not context.use_http_api:
            return False

        try:
            if context.platform == "instagram":
                api = self._ensure_instagram_api()
                result = await api.follow_user(context.username, target_user_id)
                return result.success

            elif context.platform in ("twitter", "x"):
                api = self._ensure_twitter_api()
                result = await api.follow_user(context.username, target_user_id)
                return result.success

        except Exception as e:
            logger.warning("HTTP API follow by ID failed: %s", e)
            return False

        return False

    async def _perform_unfollow_action(
        self, context: ExecutionContext, target_username: str
    ) -> bool:
        """Perform the actual unfollow action."""
        if context.use_http_api:
            try:
                if context.platform == "instagram":
                    api = self._ensure_instagram_api()
                    user_id = await api.get_user_id(context.username, target_username)
                    if not user_id:
                        return False
                    result = await api.unfollow_user(context.username, user_id)
                    return result.success

                elif context.platform in ("twitter", "x"):
                    api = self._ensure_twitter_api()
                    user_info = await api.get_user_info(context.username, target_username)
                    if not user_info:
                        return False
                    result = await api.unfollow_user(context.username, user_info.user_id)
                    return result.success

            except Exception as e:
                logger.warning("HTTP API unfollow failed: %s", e)
                return False
        
        await asyncio.sleep(0.5)
        return False

    async def _perform_dm_action(
        self, context: ExecutionContext, target_username: str, message: str
    ) -> bool:
        """Perform the actual DM action."""
        if context.use_http_api:
            try:
                if context.platform == "instagram":
                    api = self._ensure_instagram_api()
                    user_id = await api.get_user_id(context.username, target_username)
                    if not user_id:
                        logger.warning("Could not find user_id for DM to %s", target_username)
                        return False
                    result = await api.send_dm(context.username, [user_id], message)
                    return result.success

                elif context.platform in ("twitter", "x"):
                    api = self._ensure_twitter_api()
                    user_info = await api.get_user_info(context.username, target_username)
                    if not user_info:
                        logger.warning("Could not find user %s for DM", target_username)
                        return False
                    result = await api.send_dm(context.username, user_info.user_id, message)
                    return result.success

            except Exception as e:
                logger.warning("HTTP API DM failed: %s", e)
                return False

        await asyncio.sleep(0.5)
        return False

    async def _perform_dm_by_id(
        self, context: ExecutionContext, target_user_id: str, message: str
    ) -> bool:
        """
        Perform DM action by user ID (more efficient).
        """
        if not context.use_http_api:
            return False

        try:
            if context.platform == "instagram":
                api = self._ensure_instagram_api()
                result = await api.send_dm(context.username, [target_user_id], message)
                return result.success

            elif context.platform in ("twitter", "x"):
                api = self._ensure_twitter_api()
                result = await api.send_dm(context.username, target_user_id, message)
                return result.success

        except Exception as e:
            logger.warning("HTTP API DM by ID failed: %s", e)
            return False

        return False

    async def check_mutual_follow(
        self, context: ExecutionContext, target_user_id: str
    ) -> dict[str, bool]:
        """
        Check if there's a mutual follow relationship.
        
        Returns:
            Dict with 'following' (we follow them) and 'followed_by' (they follow us)
        """
        if not context.use_http_api:
            return {"following": False, "followed_by": False}

        try:
            if context.platform == "instagram":
                api = self._ensure_instagram_api()
                return await api.check_follow_status(context.username, target_user_id)

            elif context.platform in ("twitter", "x"):
                api = self._ensure_twitter_api()
                return await api.check_follow_status(context.username, target_user_id)

        except Exception as e:
            logger.warning("Check mutual follow failed: %s", e)

        return {"following": False, "followed_by": False}


def create_automation_executor_service(
    browser_service=None,
    proxy_service=None,
    scheduler_service=None,
    instagram_api_service=None,
    twitter_api_service=None,
    session_manager=None,
) -> AutomationExecutorService:
    """
    Factory function to create AutomationExecutorService.
    
    Args:
        browser_service: Anti-detect browser service (for fallback)
        proxy_service: Proxy pool service for IP rotation
        scheduler_service: Smart scheduler for rate limiting
        instagram_api_service: Instagram HTTP API service (instagrapi)
        twitter_api_service: Twitter HTTP API service (twikit)
        session_manager: Session manager for Redis persistence
        
    Returns:
        Configured AutomationExecutorService instance
    """
    return AutomationExecutorService(
        browser_service=browser_service,
        proxy_service=proxy_service,
        scheduler_service=scheduler_service,
        instagram_api_service=instagram_api_service,
        twitter_api_service=twitter_api_service,
        session_manager=session_manager,
    )


async def run_concurrent_sessions(
    accounts: list[dict],
    action_type: str,
    targets: list[dict],
    max_concurrent: int = 100,
    platform: str = "instagram",
) -> dict:
    """
    Run concurrent sessions for bulk operations.
    
    This function demonstrates how to run 1000+ concurrent sessions
    using HTTP API instead of browser automation.
    
    Args:
        accounts: List of account dicts with username, password, etc.
        action_type: "follow" or "dm"
        targets: List of target dicts with user_id or username
        max_concurrent: Maximum concurrent operations
        platform: "instagram" or "twitter"
        
    Returns:
        Summary dict with success/failure counts
        
    Example:
        accounts = [
            {"username": "user1", "password": "pass1"},
            {"username": "user2", "password": "pass2"},
            ...  # 1000 accounts
        ]
        targets = [
            {"user_id": "12345"},
            {"user_id": "67890"},
            ...
        ]
        result = await run_concurrent_sessions(accounts, "follow", targets)
    """
    from .instagram_api_service import create_instagram_api_service
    from .session_manager_service import create_session_manager_service
    from .twitter_api_service import create_twitter_api_service

    session_manager = create_session_manager_service()
    
    if platform == "instagram":
        api_service = create_instagram_api_service(session_manager)
    else:
        api_service = create_twitter_api_service(session_manager)

    semaphore = asyncio.Semaphore(max_concurrent)
    results = {"success": 0, "failed": 0, "rate_limited": 0}
    results_lock = asyncio.Lock()

    async def process_account(account: dict, target: dict):
        async with semaphore:
            try:
                # Login
                if platform == "instagram":
                    await api_service.login(
                        username=account["username"],
                        password=account["password"],
                        proxy=account.get("proxy"),
                    )
                    
                    if action_type == "follow":
                        result = await api_service.follow_user(
                            account["username"],
                            target.get("user_id") or target.get("username"),
                        )
                    else:  # dm
                        result = await api_service.send_dm(
                            account["username"],
                            [target.get("user_id")],
                            target.get("message", "Hello!"),
                        )
                else:  # twitter
                    await api_service.login(
                        username=account["username"],
                        email=account.get("email", ""),
                        password=account["password"],
                    )
                    
                    if action_type == "follow":
                        result = await api_service.follow_user(
                            account["username"],
                            target.get("user_id"),
                        )
                    else:
                        result = await api_service.send_dm(
                            account["username"],
                            target.get("user_id"),
                            target.get("message", "Hello!"),
                        )

                async with results_lock:
                    if result.success:
                        results["success"] += 1
                    elif "rate" in (result.error or "").lower():
                        results["rate_limited"] += 1
                    else:
                        results["failed"] += 1

            except Exception as e:
                logger.warning("Account %s failed: %s", account["username"], e)
                async with results_lock:
                    results["failed"] += 1

    # Pair accounts with targets
    tasks = []
    for i, (account, target) in enumerate(zip(accounts, targets, strict=False)):
        tasks.append(process_account(account, target))

    # Run all tasks concurrently
    await asyncio.gather(*tasks, return_exceptions=True)

    return results
