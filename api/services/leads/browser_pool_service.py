"""
Lightweight Browser Pool Service for login-only scenarios.

This service manages a small pool of browser instances (10-20) that are used
exclusively for scenarios that require a real browser:
- Initial account login with CAPTCHA
- Challenge/verification handling
- Cookie extraction for HTTP API sessions

Architecture:
    - Pool size: 10-20 browser instances (configurable)
    - Each instance handles one login at a time
    - Sessions released immediately after login
    - Cookies extracted and stored in Redis via SessionManager

Memory: ~3-6GB total (vs 300GB for 1000 browser sessions)
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

# Default pool size
DEFAULT_POOL_SIZE = 10
MAX_POOL_SIZE = 20

# Browser instance TTL (recreate after this many uses to prevent memory leaks)
INSTANCE_MAX_USES = 50

# Login timeout
LOGIN_TIMEOUT = 120  # seconds


class BrowserInstanceStatus(StrEnum):
    """Browser instance status."""
    IDLE = "idle"
    BUSY = "busy"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class BrowserInstance:
    """A browser instance in the pool."""
    id: str
    status: BrowserInstanceStatus = BrowserInstanceStatus.IDLE
    browser: Any = None  # Playwright browser
    context: Any = None  # Browser context
    page: Any = None  # Active page
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime | None = None
    use_count: int = 0
    current_task: str | None = None
    error_message: str | None = None

    def is_available(self) -> bool:
        """Check if instance is available for use."""
        return self.status == BrowserInstanceStatus.IDLE

    def should_recycle(self) -> bool:
        """Check if instance should be recycled."""
        return self.use_count >= INSTANCE_MAX_USES


@dataclass
class LoginResult:
    """Result of a browser-based login."""
    success: bool
    platform: str
    username: str
    cookies: dict[str, Any] | None = None
    session_data: dict[str, Any] | None = None
    user_id: str | None = None
    error: str | None = None
    challenge_required: bool = False
    challenge_url: str | None = None


class BrowserPoolService:
    """
    Lightweight browser pool for login-only scenarios.
    
    This service maintains a small pool of browser instances (10-20)
    for scenarios that require real browser interaction:
    
    1. Initial login with CAPTCHA
    2. Challenge/verification handling
    3. Cookie extraction for HTTP API
    
    Usage:
        pool = BrowserPoolService(pool_size=10)
        await pool.start()
        
        async with pool.acquire() as instance:
            result = await pool.perform_instagram_login(
                instance, "username", "password"
            )
            if result.success:
                # Store cookies for HTTP API use
                await session_manager.store_session(...)
        
        await pool.stop()
    
    The pool is designed to be shared across all accounts, with each
    login operation acquiring an instance, performing the login,
    extracting cookies, and immediately releasing the instance.
    """

    def __init__(
        self,
        pool_size: int = DEFAULT_POOL_SIZE,
        headless: bool = True,
        proxy_service=None,
        session_manager=None,
    ):
        """
        Initialize browser pool.
        
        Args:
            pool_size: Number of browser instances (10-20 recommended)
            headless: Run browsers in headless mode
            proxy_service: Optional proxy service for rotating proxies
            session_manager: Session manager for storing extracted cookies
        """
        self.pool_size = min(pool_size, MAX_POOL_SIZE)
        self.headless = headless
        self.proxy_service = proxy_service
        self.session_manager = session_manager
        
        self._instances: dict[str, BrowserInstance] = {}
        self._playwright = None
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self.pool_size)
        self._started = False

    async def start(self) -> None:
        """Start the browser pool."""
        if self._started:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

        logger.info("Starting browser pool with %d instances", self.pool_size)
        self._playwright = await async_playwright().start()
        
        # Pre-create browser instances
        for i in range(self.pool_size):
            instance_id = f"browser_{i}"
            instance = await self._create_instance(instance_id)
            self._instances[instance_id] = instance

        self._started = True
        logger.info("Browser pool started with %d instances", len(self._instances))

    async def stop(self) -> None:
        """Stop the browser pool and cleanup resources."""
        if not self._started:
            return

        logger.info("Stopping browser pool")
        
        for instance_id, instance in self._instances.items():
            await self._destroy_instance(instance)

        self._instances.clear()

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        self._started = False
        logger.info("Browser pool stopped")

    async def _create_instance(self, instance_id: str) -> BrowserInstance:
        """Create a new browser instance."""
        instance = BrowserInstance(id=instance_id, status=BrowserInstanceStatus.STARTING)

        try:
            # Launch browser with stealth settings
            browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            instance.browser = browser
            instance.status = BrowserInstanceStatus.IDLE
            logger.debug("Created browser instance %s", instance_id)
        except Exception as e:
            instance.status = BrowserInstanceStatus.ERROR
            instance.error_message = str(e)
            logger.exception("Failed to create browser instance %s", instance_id)

        return instance

    async def _destroy_instance(self, instance: BrowserInstance) -> None:
        """Destroy a browser instance."""
        instance.status = BrowserInstanceStatus.STOPPING
        
        try:
            if instance.page:
                await instance.page.close()
            if instance.context:
                await instance.context.close()
            if instance.browser:
                await instance.browser.close()
        except Exception as e:
            logger.warning("Error destroying browser instance %s: %s", instance.id, e)

        instance.browser = None
        instance.context = None
        instance.page = None

    async def _recycle_instance(self, instance: BrowserInstance) -> None:
        """Recycle a browser instance (destroy and recreate)."""
        logger.info("Recycling browser instance %s after %d uses", instance.id, instance.use_count)
        await self._destroy_instance(instance)
        new_instance = await self._create_instance(instance.id)
        self._instances[instance.id] = new_instance

    @asynccontextmanager
    async def acquire(self, timeout: float = 60) -> AsyncIterator[BrowserInstance]:
        """
        Acquire a browser instance from the pool.
        
        Usage:
            async with pool.acquire() as instance:
                # Use instance for login
                pass
            # Instance automatically released
        """
        if not self._started:
            raise RuntimeError("Browser pool not started")

        # Wait for available slot
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
        except TimeoutError:
            raise RuntimeError("Timeout waiting for available browser instance")

        instance = None
        try:
            async with self._lock:
                # Find an available instance
                for inst in self._instances.values():
                    if inst.is_available():
                        instance = inst
                        instance.status = BrowserInstanceStatus.BUSY
                        instance.last_used_at = datetime.now()
                        break

                if not instance:
                    # Should not happen with semaphore, but handle gracefully
                    raise RuntimeError("No available browser instance")

            # Create fresh context for this session
            instance.context = await instance.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            instance.page = await instance.context.new_page()

            yield instance

        finally:
            if instance:
                # Cleanup context
                try:
                    if instance.page:
                        await instance.page.close()
                        instance.page = None
                    if instance.context:
                        await instance.context.close()
                        instance.context = None
                except Exception as e:
                    logger.warning("Error cleaning up browser instance: %s", e)

                instance.use_count += 1
                instance.current_task = None
                instance.status = BrowserInstanceStatus.IDLE

                # Recycle if needed
                if instance.should_recycle():
                    asyncio.create_task(self._recycle_instance(instance))

            self._semaphore.release()

    async def perform_instagram_login(
        self,
        instance: BrowserInstance,
        username: str,
        password: str,
        proxy: str | None = None,
    ) -> LoginResult:
        """
        Perform Instagram login using browser.
        
        Args:
            instance: Browser instance from pool
            username: Instagram username
            password: Instagram password
            proxy: Optional proxy URL
            
        Returns:
            LoginResult with cookies if successful
        """
        instance.current_task = f"instagram_login:{username}"
        result = LoginResult(platform="instagram", username=username, success=False)

        try:
            page = instance.page
            
            # Navigate to Instagram
            await page.goto("https://www.instagram.com/accounts/login/", wait_until="networkidle")
            await asyncio.sleep(2)  # Wait for page to fully load

            # Accept cookies if dialog appears
            try:
                cookie_btn = page.locator("button:has-text('Allow'), button:has-text('Accept')")
                if await cookie_btn.count() > 0:
                    await cookie_btn.first.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            # Fill login form
            await page.fill("input[name='username']", username)
            await asyncio.sleep(0.5)
            await page.fill("input[name='password']", password)
            await asyncio.sleep(0.5)

            # Click login button
            await page.click("button[type='submit']")
            
            # Wait for navigation or error
            try:
                await page.wait_for_url("**/instagram.com/**", timeout=LOGIN_TIMEOUT * 1000)
            except Exception:
                pass

            await asyncio.sleep(3)

            # Check for challenge
            current_url = page.url
            if "challenge" in current_url or "checkpoint" in current_url:
                result.challenge_required = True
                result.challenge_url = current_url
                result.error = "Challenge required"
                return result

            # Check for login success
            if "login" not in current_url and "accounts" not in current_url:
                # Extract cookies
                cookies = await instance.context.cookies()
                cookie_dict = {c["name"]: c["value"] for c in cookies}
                
                result.success = True
                result.cookies = cookie_dict
                
                # Try to get session data similar to instagrapi format
                result.session_data = {
                    "cookies": cookie_dict,
                    "user_agent": await page.evaluate("() => navigator.userAgent"),
                }

                logger.info("Browser login successful for Instagram user %s", username)
            else:
                # Check for error message
                try:
                    error_elem = page.locator("#slfErrorAlert, [data-testid='login-error-message']")
                    if await error_elem.count() > 0:
                        result.error = await error_elem.first.text_content()
                except Exception:
                    result.error = "Login failed - unknown error"

        except Exception as e:
            logger.exception("Browser Instagram login failed for %s", username)
            result.error = str(e)

        return result

    async def perform_twitter_login(
        self,
        instance: BrowserInstance,
        username: str,
        email: str,
        password: str,
        proxy: str | None = None,
    ) -> LoginResult:
        """
        Perform Twitter/X login using browser.
        
        Args:
            instance: Browser instance from pool
            username: Twitter username
            email: Associated email
            password: Twitter password
            proxy: Optional proxy URL
            
        Returns:
            LoginResult with cookies if successful
        """
        instance.current_task = f"twitter_login:{username}"
        result = LoginResult(platform="twitter", username=username, success=False)

        try:
            page = instance.page

            # Navigate to Twitter login
            await page.goto("https://twitter.com/i/flow/login", wait_until="networkidle")
            await asyncio.sleep(2)

            # Enter username
            await page.fill("input[autocomplete='username']", username)
            await page.click("div[role='button']:has-text('Next')")
            await asyncio.sleep(2)

            # Check if email verification needed
            try:
                email_input = page.locator("input[data-testid='ocfEnterTextTextInput']")
                if await email_input.count() > 0:
                    await email_input.fill(email)
                    await page.click("div[role='button']:has-text('Next')")
                    await asyncio.sleep(2)
            except Exception:
                pass

            # Enter password
            await page.fill("input[name='password'], input[type='password']", password)
            await page.click("div[data-testid='LoginForm_Login_Button']")
            
            # Wait for navigation
            try:
                await page.wait_for_url("**/twitter.com/home**", timeout=LOGIN_TIMEOUT * 1000)
            except Exception:
                pass

            await asyncio.sleep(3)

            # Check for success
            current_url = page.url
            if "home" in current_url or "x.com" in current_url:
                # Extract cookies
                cookies = await instance.context.cookies()
                cookie_dict = {c["name"]: c["value"] for c in cookies}
                
                result.success = True
                result.cookies = cookie_dict
                
                logger.info("Browser login successful for Twitter user %s", username)
            else:
                if "challenge" in current_url or "account/access" in current_url:
                    result.challenge_required = True
                    result.challenge_url = current_url
                    result.error = "Challenge required"
                else:
                    result.error = "Login failed - check credentials"

        except Exception as e:
            logger.exception("Browser Twitter login failed for %s", username)
            result.error = str(e)

        return result

    async def extract_cookies_for_api(
        self,
        platform: str,
        username: str,
        password: str,
        email: str | None = None,
    ) -> LoginResult:
        """
        High-level method to extract cookies for HTTP API use.
        
        This acquires a browser instance, performs login, extracts cookies,
        and optionally stores them in Redis via SessionManager.
        
        Args:
            platform: "instagram" or "twitter"
            username: Account username
            password: Account password
            email: Email (required for Twitter)
            
        Returns:
            LoginResult with cookies
        """
        async with self.acquire() as instance:
            if platform == "instagram":
                result = await self.perform_instagram_login(
                    instance, username, password
                )
            elif platform in ("twitter", "x"):
                result = await self.perform_twitter_login(
                    instance, username, email or "", password
                )
            else:
                return LoginResult(
                    platform=platform,
                    username=username,
                    success=False,
                    error=f"Unsupported platform: {platform}",
                )

            # Store in session manager if successful
            if result.success and self.session_manager:
                await self.session_manager.store_session(
                    platform=platform,
                    username=username,
                    session_data=result.cookies or {},
                    status="active",
                )

            return result

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        idle = sum(1 for i in self._instances.values() if i.status == BrowserInstanceStatus.IDLE)
        busy = sum(1 for i in self._instances.values() if i.status == BrowserInstanceStatus.BUSY)
        error = sum(1 for i in self._instances.values() if i.status == BrowserInstanceStatus.ERROR)
        
        return {
            "pool_size": self.pool_size,
            "total_instances": len(self._instances),
            "idle": idle,
            "busy": busy,
            "error": error,
            "started": self._started,
            "instances": [
                {
                    "id": i.id,
                    "status": i.status,
                    "use_count": i.use_count,
                    "last_used": i.last_used_at.isoformat() if i.last_used_at else None,
                }
                for i in self._instances.values()
            ],
        }


def create_browser_pool_service(
    pool_size: int = DEFAULT_POOL_SIZE,
    headless: bool = True,
    proxy_service=None,
    session_manager=None,
) -> BrowserPoolService:
    """Factory function to create BrowserPoolService."""
    return BrowserPoolService(
        pool_size=pool_size,
        headless=headless,
        proxy_service=proxy_service,
        session_manager=session_manager,
    )

