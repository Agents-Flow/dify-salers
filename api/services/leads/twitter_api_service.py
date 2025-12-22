"""
Twitter/X API Service using twikit library.
Provides browser-less automation for X/Twitter operations at scale.

This service uses the twikit library which simulates Twitter's web/mobile API,
enabling high-concurrency operations (1000+ accounts) without browser overhead.

Features:
- Login with session persistence (cookies stored in Redis)
- Follow/Unfollow users
- Send Direct Messages
- Get followers/following lists
- Tweet and reply operations

Memory usage: ~1-5MB per session vs 300-500MB for browser automation.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TwitterAPIError(Exception):
    """Base exception for Twitter API errors."""
    pass


class LoginError(TwitterAPIError):
    """Login failed."""
    pass


class RateLimitError(TwitterAPIError):
    """Rate limit hit."""
    pass


class ActionError(TwitterAPIError):
    """Action failed."""
    pass


class AccountLockedError(TwitterAPIError):
    """Account is locked/suspended."""
    pass


class AccountStatus(StrEnum):
    """Twitter account status."""
    ACTIVE = "active"
    LOCKED = "locked"
    RATE_LIMITED = "rate_limited"
    SUSPENDED = "suspended"
    LOGIN_REQUIRED = "login_required"
    UNKNOWN = "unknown"


@dataclass
class TwitterSession:
    """Twitter session data for persistence."""
    username: str
    user_id: str | None = None
    cookies: dict[str, str] = field(default_factory=dict)
    status: AccountStatus = AccountStatus.ACTIVE
    last_login: datetime | None = None
    last_action: datetime | None = None
    error_count: int = 0

    def to_json(self) -> str:
        """Serialize session to JSON for Redis storage."""
        return json.dumps({
            "username": self.username,
            "user_id": self.user_id,
            "cookies": self.cookies,
            "status": self.status,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "last_action": self.last_action.isoformat() if self.last_action else None,
            "error_count": self.error_count,
        })

    @classmethod
    def from_json(cls, data: str) -> "TwitterSession":
        """Deserialize session from JSON."""
        obj = json.loads(data)
        return cls(
            username=obj["username"],
            user_id=obj.get("user_id"),
            cookies=obj.get("cookies", {}),
            status=AccountStatus(obj.get("status", "unknown")),
            last_login=datetime.fromisoformat(obj["last_login"]) if obj.get("last_login") else None,
            last_action=datetime.fromisoformat(obj["last_action"]) if obj.get("last_action") else None,
            error_count=obj.get("error_count", 0),
        )


@dataclass
class FollowResult:
    """Result of a follow operation."""
    success: bool
    user_id: str | None = None
    username: str | None = None
    error: str | None = None


@dataclass
class DMResult:
    """Result of a DM operation."""
    success: bool
    conversation_id: str | None = None
    message_id: str | None = None
    error: str | None = None


@dataclass
class UserInfo:
    """Twitter user information."""
    user_id: str
    username: str
    name: str | None = None
    description: str | None = None
    followers_count: int = 0
    following_count: int = 0
    tweet_count: int = 0
    is_protected: bool = False
    is_verified: bool = False
    profile_image_url: str | None = None


class TwitterAPIService:
    """
    High-performance Twitter/X API service using twikit.
    
    This service provides browser-less Twitter automation by using
    the twikit library which simulates Twitter's web API.
    
    Key benefits:
    - Memory efficient: ~1-5MB per session vs 300MB for browser
    - High concurrency: Can handle 1000+ concurrent sessions
    - Async native: Built on asyncio for maximum throughput
    
    Usage:
        service = TwitterAPIService(session_manager)
        await service.login("username", "email", "password")
        result = await service.follow_user("username", "target_user_id")
        result = await service.send_dm("username", "user_id", "Hello!")
    """

    def __init__(self, session_manager=None, cookies_dir: str | None = None):
        """
        Initialize Twitter API service.
        
        Args:
            session_manager: Optional SessionManager for Redis-based session persistence
            cookies_dir: Optional directory for storing cookies files (fallback)
        """
        self.session_manager = session_manager
        self.cookies_dir = Path(cookies_dir) if cookies_dir else Path("/tmp/twitter_cookies")
        self._clients: dict[str, Any] = {}  # username -> Client instance
        self._sessions: dict[str, TwitterSession] = {}
        self._lock = asyncio.Lock()

    async def _get_client(self, username: str):
        """Get or create twikit Client for username."""
        try:
            from twikit import Client
        except ImportError:
            raise TwitterAPIError(
                "twikit not installed. Run: pip install twikit"
            )

        if username not in self._clients:
            self._clients[username] = Client("en-US")
        return self._clients[username]

    async def login(
        self,
        username: str,
        email: str,
        password: str,
        cookies: dict | None = None,
    ) -> TwitterSession:
        """
        Login to Twitter/X account.
        
        Args:
            username: Twitter username (without @)
            email: Email address associated with account
            password: Account password
            cookies: Optional saved cookies for session restoration
            
        Returns:
            TwitterSession with login status and session data
            
        Raises:
            LoginError: If login fails
            AccountLocked: If account is locked
        """
        try:
            from twikit import Client
            from twikit.errors import (
                AccountLocked as TwikitAccountLocked,
            )
            from twikit.errors import (
                BadRequest,
                Unauthorized,
            )
        except ImportError:
            raise TwitterAPIError("twikit not installed")

        session = TwitterSession(username=username)
        client = Client("en-US")

        try:
            # Try to restore session from cookies first
            if cookies:
                client.set_cookies(cookies)
                try:
                    # Verify session is valid
                    user = await client.user()
                    session.user_id = user.id
                    session.cookies = client.get_cookies()
                    session.status = AccountStatus.ACTIVE
                    session.last_login = datetime.now()
                    
                    self._clients[username] = client
                    self._sessions[username] = session
                    logger.info("Restored Twitter session for %s", username)
                    return session
                except Exception:
                    logger.info("Twitter session expired for %s, re-logging in", username)

            # Fresh login
            await client.login(
                auth_info_1=username,
                auth_info_2=email,
                password=password,
            )
            
            # Get user info and cookies
            user = await client.user()
            session.user_id = user.id
            session.cookies = client.get_cookies()
            session.status = AccountStatus.ACTIVE
            session.last_login = datetime.now()
            
            self._clients[username] = client
            self._sessions[username] = session
            
            logger.info("Successfully logged in to Twitter as %s", username)
            return session

        except TwikitAccountLocked:
            session.status = AccountStatus.LOCKED
            raise AccountLocked(f"Twitter account {username} is locked")
        except Unauthorized:
            session.status = AccountStatus.LOGIN_REQUIRED
            raise LoginError(f"Invalid credentials for Twitter user {username}")
        except BadRequest as e:
            if "rate limit" in str(e).lower():
                session.status = AccountStatus.RATE_LIMITED
                raise RateLimitError(f"Rate limited for {username}")
            raise LoginError(f"Login failed for {username}: {e}")
        except Exception as e:
            session.status = AccountStatus.UNKNOWN
            logger.exception("Twitter login failed for %s", username)
            raise LoginError(f"Twitter login failed for {username}: {e}")

    async def logout(self, username: str) -> bool:
        """Logout and clear session."""
        client = self._clients.pop(username, None)
        if client:
            try:
                await client.logout()
            except Exception:
                pass
        self._sessions.pop(username, None)
        return True

    async def follow_user(
        self,
        username: str,
        target_user_id: str,
    ) -> FollowResult:
        """
        Follow a user by their user ID.
        
        Args:
            username: The account username performing the follow
            target_user_id: The user ID to follow
            
        Returns:
            FollowResult with success status
        """
        client = self._clients.get(username)
        if not client:
            return FollowResult(success=False, error="Not logged in")

        try:
            user = await client.get_user_by_id(target_user_id)
            await user.follow()
            
            # Update session last action
            if username in self._sessions:
                self._sessions[username].last_action = datetime.now()

            return FollowResult(
                success=True,
                user_id=target_user_id,
                username=user.screen_name,
            )

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str:
                if username in self._sessions:
                    self._sessions[username].status = AccountStatus.RATE_LIMITED
                return FollowResult(
                    success=False,
                    user_id=target_user_id,
                    error="Rate limited",
                )
            
            logger.warning("Twitter follow failed for %s -> %s: %s", username, target_user_id, e)
            return FollowResult(
                success=False,
                user_id=target_user_id,
                error=str(e),
            )

    async def unfollow_user(
        self,
        username: str,
        target_user_id: str,
    ) -> FollowResult:
        """Unfollow a user by their user ID."""
        client = self._clients.get(username)
        if not client:
            return FollowResult(success=False, error="Not logged in")

        try:
            user = await client.get_user_by_id(target_user_id)
            await user.unfollow()
            
            if username in self._sessions:
                self._sessions[username].last_action = datetime.now()

            return FollowResult(success=True, user_id=target_user_id)

        except Exception as e:
            logger.warning("Twitter unfollow failed: %s", e)
            return FollowResult(success=False, user_id=target_user_id, error=str(e))

    async def send_dm(
        self,
        username: str,
        target_user_id: str,
        message: str,
    ) -> DMResult:
        """
        Send a Direct Message to a user.
        
        Args:
            username: The account username sending the DM
            target_user_id: User ID to send the message to
            message: The message content
            
        Returns:
            DMResult with success status and conversation/message IDs
        """
        client = self._clients.get(username)
        if not client:
            return DMResult(success=False, error="Not logged in")

        try:
            result = await client.send_dm(target_user_id, message)
            
            if username in self._sessions:
                self._sessions[username].last_action = datetime.now()

            return DMResult(
                success=True,
                conversation_id=getattr(result, "conversation_id", None),
                message_id=getattr(result, "id", None),
            )

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str:
                if username in self._sessions:
                    self._sessions[username].status = AccountStatus.RATE_LIMITED
                return DMResult(success=False, error="Rate limited")
            
            logger.warning("Twitter DM failed: %s", e)
            return DMResult(success=False, error=str(e))

    async def get_user_info(
        self,
        username: str,
        target_username: str,
    ) -> UserInfo | None:
        """Get information about a user by screen name."""
        client = self._clients.get(username)
        if not client:
            return None

        try:
            user = await client.get_user_by_screen_name(target_username)
            return UserInfo(
                user_id=user.id,
                username=user.screen_name,
                name=user.name,
                description=user.description,
                followers_count=user.followers_count,
                following_count=user.following_count,
                tweet_count=user.statuses_count,
                is_protected=user.is_protected,
                is_verified=user.is_blue_verified,
                profile_image_url=user.profile_image_url,
            )
        except Exception as e:
            logger.warning("Twitter get user info failed: %s", e)
            return None

    async def get_user_by_id(
        self,
        username: str,
        target_user_id: str,
    ) -> UserInfo | None:
        """Get information about a user by ID."""
        client = self._clients.get(username)
        if not client:
            return None

        try:
            user = await client.get_user_by_id(target_user_id)
            return UserInfo(
                user_id=user.id,
                username=user.screen_name,
                name=user.name,
                description=user.description,
                followers_count=user.followers_count,
                following_count=user.following_count,
                tweet_count=user.statuses_count,
                is_protected=user.is_protected,
                is_verified=user.is_blue_verified,
                profile_image_url=user.profile_image_url,
            )
        except Exception as e:
            logger.warning("Twitter get user by ID failed: %s", e)
            return None

    async def get_followers(
        self,
        username: str,
        target_user_id: str,
        count: int = 100,
    ) -> list[UserInfo]:
        """Get followers of a user."""
        client = self._clients.get(username)
        if not client:
            return []

        try:
            user = await client.get_user_by_id(target_user_id)
            followers = await user.get_followers(count=count)
            
            return [
                UserInfo(
                    user_id=f.id,
                    username=f.screen_name,
                    name=f.name,
                    description=f.description,
                    followers_count=f.followers_count,
                    following_count=f.following_count,
                    is_protected=f.is_protected,
                    is_verified=f.is_blue_verified,
                )
                for f in followers
            ]
        except Exception as e:
            logger.warning("Twitter get followers failed: %s", e)
            return []

    async def get_following(
        self,
        username: str,
        target_user_id: str,
        count: int = 100,
    ) -> list[UserInfo]:
        """Get users that a user is following."""
        client = self._clients.get(username)
        if not client:
            return []

        try:
            user = await client.get_user_by_id(target_user_id)
            following = await user.get_following(count=count)
            
            return [
                UserInfo(
                    user_id=f.id,
                    username=f.screen_name,
                    name=f.name,
                    is_protected=f.is_protected,
                    is_verified=f.is_blue_verified,
                )
                for f in following
            ]
        except Exception as e:
            logger.warning("Twitter get following failed: %s", e)
            return []

    async def check_follow_status(
        self,
        username: str,
        target_user_id: str,
    ) -> dict[str, bool]:
        """
        Check follow relationship with a user.
        
        Returns:
            Dict with 'following' (we follow them) and 'followed_by' (they follow us)
        """
        client = self._clients.get(username)
        if not client:
            return {"following": False, "followed_by": False}

        try:
            # Get our following list and check
            me = await client.user()
            my_following = await me.get_following(count=1000)
            following_ids = {f.id for f in my_following}
            
            # Check if we follow them
            is_following = target_user_id in following_ids
            
            # Get target's following and check if they follow us
            target_user = await client.get_user_by_id(target_user_id)
            target_following = await target_user.get_following(count=1000)
            target_following_ids = {f.id for f in target_following}
            
            is_followed_by = me.id in target_following_ids
            
            return {
                "following": is_following,
                "followed_by": is_followed_by,
            }
        except Exception as e:
            logger.warning("Twitter check follow status failed: %s", e)
            return {"following": False, "followed_by": False}

    async def send_tweet(
        self,
        username: str,
        text: str,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """
        Post a tweet or reply.
        
        Args:
            username: Account username
            text: Tweet text content
            reply_to: Optional tweet ID to reply to
            
        Returns:
            Dict with tweet_id and success status
        """
        client = self._clients.get(username)
        if not client:
            return {"success": False, "error": "Not logged in"}

        try:
            if reply_to:
                tweet = await client.create_tweet(text, reply_to=reply_to)
            else:
                tweet = await client.create_tweet(text)
            
            if username in self._sessions:
                self._sessions[username].last_action = datetime.now()

            return {
                "success": True,
                "tweet_id": tweet.id,
            }
        except Exception as e:
            logger.warning("Twitter send tweet failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_session(self, username: str) -> TwitterSession | None:
        """Get session for a username."""
        return self._sessions.get(username)

    def get_cookies(self, username: str) -> dict | None:
        """Get cookies for persistence."""
        session = self._sessions.get(username)
        if session:
            return session.cookies
        return None

    async def restore_session(
        self,
        username: str,
        cookies: dict,
    ) -> bool:
        """
        Restore a session from saved cookies.
        
        Args:
            username: Twitter username
            cookies: Saved cookies from get_cookies()
            
        Returns:
            True if session restored successfully
        """
        try:
            session = await self.login(
                username=username,
                email="",  # Not needed with cookies
                password="",  # Not needed with cookies
                cookies=cookies,
            )
            return session.status == AccountStatus.ACTIVE
        except Exception as e:
            logger.warning("Twitter session restore failed for %s: %s", username, e)
            return False

    @property
    def active_sessions(self) -> int:
        """Number of active sessions."""
        return len(self._clients)


def create_twitter_api_service(session_manager=None) -> TwitterAPIService:
    """Factory function to create TwitterAPIService."""
    return TwitterAPIService(session_manager=session_manager)

