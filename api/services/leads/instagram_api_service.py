"""
Instagram API Service using instagrapi library.
Provides browser-less automation for Instagram operations at scale.

This service uses the instagrapi library which simulates Instagram's mobile API,
enabling high-concurrency operations (1000+ accounts) without browser overhead.

Features:
- Login with session persistence (Redis)
- Follow/Unfollow users
- Send Direct Messages
- Get followers/following lists
- Profile information retrieval

Memory usage: ~1-5MB per session vs 300-500MB for browser automation.
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

# Thread pool for running sync instagrapi calls
_executor = ThreadPoolExecutor(max_workers=100)


class InstagramAPIError(Exception):
    """Base exception for Instagram API errors."""
    pass


class LoginError(InstagramAPIError):
    """Login failed."""
    pass


class RateLimitError(InstagramAPIError):
    """Rate limit hit."""
    pass


class ActionError(InstagramAPIError):
    """Action failed."""
    pass


class ChallengeRequiredError(InstagramAPIError):
    """Challenge/verification required."""
    pass


class AccountStatus(StrEnum):
    """Instagram account status."""
    ACTIVE = "active"
    CHALLENGE_REQUIRED = "challenge_required"
    RATE_LIMITED = "rate_limited"
    BANNED = "banned"
    LOGIN_REQUIRED = "login_required"
    UNKNOWN = "unknown"


@dataclass
class InstagramSession:
    """Instagram session data for persistence."""
    username: str
    user_id: str | None = None
    session_data: dict[str, Any] = field(default_factory=dict)
    device_settings: dict[str, Any] = field(default_factory=dict)
    status: AccountStatus = AccountStatus.ACTIVE
    last_login: datetime | None = None
    last_action: datetime | None = None
    error_count: int = 0

    def to_json(self) -> str:
        """Serialize session to JSON for Redis storage."""
        return json.dumps({
            "username": self.username,
            "user_id": self.user_id,
            "session_data": self.session_data,
            "device_settings": self.device_settings,
            "status": self.status,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "last_action": self.last_action.isoformat() if self.last_action else None,
            "error_count": self.error_count,
        })

    @classmethod
    def from_json(cls, data: str) -> "InstagramSession":
        """Deserialize session from JSON."""
        obj = json.loads(data)
        return cls(
            username=obj["username"],
            user_id=obj.get("user_id"),
            session_data=obj.get("session_data", {}),
            device_settings=obj.get("device_settings", {}),
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
    is_private: bool = False


@dataclass
class DMResult:
    """Result of a DM operation."""
    success: bool
    thread_id: str | None = None
    message_id: str | None = None
    error: str | None = None


@dataclass
class UserInfo:
    """Instagram user information."""
    user_id: str
    username: str
    full_name: str | None = None
    biography: str | None = None
    follower_count: int = 0
    following_count: int = 0
    media_count: int = 0
    is_private: bool = False
    is_verified: bool = False
    profile_pic_url: str | None = None


class InstagramAPIService:
    """
    High-performance Instagram API service using instagrapi.
    
    This service provides browser-less Instagram automation by using
    the instagrapi library which simulates Instagram's mobile API.
    
    Key benefits:
    - Memory efficient: ~1-5MB per session vs 300MB for browser
    - High concurrency: Can handle 1000+ concurrent sessions
    - Fast: Direct HTTP API calls, no browser overhead
    
    Usage:
        service = InstagramAPIService(session_manager)
        await service.login("username", "password", proxy="http://proxy:port")
        result = await service.follow_user("target_user_id")
        result = await service.send_dm("user_id", "Hello!")
    """

    def __init__(self, session_manager=None):
        """
        Initialize Instagram API service.
        
        Args:
            session_manager: Optional SessionManager for Redis-based session persistence
        """
        self.session_manager = session_manager
        self._clients: dict[str, Any] = {}  # username -> Client instance
        self._sessions: dict[str, InstagramSession] = {}
        self._lock = asyncio.Lock()

    def _get_client(self, username: str):
        """Get or create instagrapi Client for username."""
        try:
            from instagrapi import Client
        except ImportError:
            raise InstagramAPIError(
                "instagrapi not installed. Run: pip install instagrapi"
            )

        if username not in self._clients:
            self._clients[username] = Client()
        return self._clients[username]

    async def login(
        self,
        username: str,
        password: str,
        proxy: str | None = None,
        session_data: dict | None = None,
    ) -> InstagramSession:
        """
        Login to Instagram account.
        
        Args:
            username: Instagram username
            password: Instagram password
            proxy: Optional proxy URL (http://user:pass@host:port)
            session_data: Optional saved session data for session restoration
            
        Returns:
            InstagramSession with login status and session data
            
        Raises:
            LoginError: If login fails
            ChallengeRequired: If verification is needed
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._login_sync,
            username,
            password,
            proxy,
            session_data,
        )

    def _login_sync(
        self,
        username: str,
        password: str,
        proxy: str | None,
        session_data: dict | None,
    ) -> InstagramSession:
        """Synchronous login implementation."""
        try:
            from instagrapi import Client
            from instagrapi.exceptions import (
                BadPassword,
                PleaseWaitFewMinutes,
            )
            from instagrapi.exceptions import (
                ChallengeRequired as IGChallengeRequired,
            )
        except ImportError:
            raise InstagramAPIError("instagrapi not installed")

        client = Client()
        
        # Set proxy if provided
        if proxy:
            client.set_proxy(proxy)

        session = InstagramSession(username=username)

        try:
            # Try to restore session first
            if session_data:
                client.set_settings(session_data)
                try:
                    client.get_timeline_feed()  # Test if session is valid
                    session.session_data = client.get_settings()
                    session.user_id = str(client.user_id)
                    session.status = AccountStatus.ACTIVE
                    session.last_login = datetime.now()
                    self._clients[username] = client
                    self._sessions[username] = session
                    logger.info("Restored session for %s", username)
                    return session
                except Exception:
                    logger.info("Session expired for %s, re-logging in", username)

            # Fresh login
            client.login(username, password)
            session.session_data = client.get_settings()
            session.device_settings = client.get_settings().get("device_settings", {})
            session.user_id = str(client.user_id)
            session.status = AccountStatus.ACTIVE
            session.last_login = datetime.now()
            
            self._clients[username] = client
            self._sessions[username] = session
            
            logger.info("Successfully logged in as %s", username)
            return session

        except BadPassword:
            session.status = AccountStatus.LOGIN_REQUIRED
            raise LoginError(f"Invalid password for {username}")
        except IGChallengeRequired as e:
            session.status = AccountStatus.CHALLENGE_REQUIRED
            raise ChallengeRequired(f"Challenge required for {username}: {e}")
        except PleaseWaitFewMinutes:
            session.status = AccountStatus.RATE_LIMITED
            raise RateLimitError(f"Rate limited for {username}")
        except Exception as e:
            session.status = AccountStatus.UNKNOWN
            logger.exception("Login failed for %s", username)
            raise LoginError(f"Login failed for {username}: {e}")

    async def logout(self, username: str) -> bool:
        """Logout and clear session."""
        if username in self._clients:
            del self._clients[username]
        if username in self._sessions:
            del self._sessions[username]
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
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._follow_user_sync,
            username,
            target_user_id,
        )

    def _follow_user_sync(self, username: str, target_user_id: str) -> FollowResult:
        """Synchronous follow implementation."""
        try:
            from instagrapi.exceptions import (
                PleaseWaitFewMinutes,
                UserNotFound,
            )
        except ImportError:
            return FollowResult(success=False, error="instagrapi not installed")

        client = self._clients.get(username)
        if not client:
            return FollowResult(success=False, error="Not logged in")

        try:
            result = client.user_follow(target_user_id)
            
            # Update session last action
            if username in self._sessions:
                self._sessions[username].last_action = datetime.now()

            return FollowResult(
                success=result,
                user_id=target_user_id,
            )

        except UserNotFound:
            return FollowResult(
                success=False,
                user_id=target_user_id,
                error="User not found",
            )
        except PleaseWaitFewMinutes:
            if username in self._sessions:
                self._sessions[username].status = AccountStatus.RATE_LIMITED
            return FollowResult(
                success=False,
                user_id=target_user_id,
                error="Rate limited",
            )
        except Exception as e:
            logger.warning("Follow failed for %s -> %s: %s", username, target_user_id, e)
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
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._unfollow_user_sync,
            username,
            target_user_id,
        )

    def _unfollow_user_sync(self, username: str, target_user_id: str) -> FollowResult:
        """Synchronous unfollow implementation."""
        client = self._clients.get(username)
        if not client:
            return FollowResult(success=False, error="Not logged in")

        try:
            result = client.user_unfollow(target_user_id)
            
            if username in self._sessions:
                self._sessions[username].last_action = datetime.now()

            return FollowResult(success=result, user_id=target_user_id)

        except Exception as e:
            logger.warning("Unfollow failed: %s", e)
            return FollowResult(success=False, user_id=target_user_id, error=str(e))

    async def send_dm(
        self,
        username: str,
        target_user_ids: list[str],
        message: str,
    ) -> DMResult:
        """
        Send a Direct Message to one or more users.
        
        Args:
            username: The account username sending the DM
            target_user_ids: List of user IDs to send the message to
            message: The message content
            
        Returns:
            DMResult with success status and thread/message IDs
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._send_dm_sync,
            username,
            target_user_ids,
            message,
        )

    def _send_dm_sync(
        self,
        username: str,
        target_user_ids: list[str],
        message: str,
    ) -> DMResult:
        """Synchronous DM implementation."""
        client = self._clients.get(username)
        if not client:
            return DMResult(success=False, error="Not logged in")

        try:
            result = client.direct_send(message, target_user_ids)
            
            if username in self._sessions:
                self._sessions[username].last_action = datetime.now()

            return DMResult(
                success=True,
                thread_id=str(result.thread_id) if hasattr(result, "thread_id") else None,
                message_id=str(result.id) if hasattr(result, "id") else None,
            )

        except Exception as e:
            logger.warning("DM failed: %s", e)
            return DMResult(success=False, error=str(e))

    async def get_user_info(
        self,
        username: str,
        target_username: str,
    ) -> UserInfo | None:
        """Get information about a user by username."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._get_user_info_sync,
            username,
            target_username,
        )

    def _get_user_info_sync(self, username: str, target_username: str) -> UserInfo | None:
        """Synchronous user info implementation."""
        client = self._clients.get(username)
        if not client:
            return None

        try:
            user = client.user_info_by_username(target_username)
            return UserInfo(
                user_id=str(user.pk),
                username=user.username,
                full_name=user.full_name,
                biography=user.biography,
                follower_count=user.follower_count,
                following_count=user.following_count,
                media_count=user.media_count,
                is_private=user.is_private,
                is_verified=user.is_verified,
                profile_pic_url=str(user.profile_pic_url) if user.profile_pic_url else None,
            )
        except Exception as e:
            logger.warning("Get user info failed: %s", e)
            return None

    async def get_user_id(self, username: str, target_username: str) -> str | None:
        """Get user ID from username."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._get_user_id_sync,
            username,
            target_username,
        )

    def _get_user_id_sync(self, username: str, target_username: str) -> str | None:
        """Synchronous user ID lookup."""
        client = self._clients.get(username)
        if not client:
            return None

        try:
            user_id = client.user_id_from_username(target_username)
            return str(user_id)
        except Exception:
            return None

    async def get_followers(
        self,
        username: str,
        target_user_id: str,
        amount: int = 100,
    ) -> list[UserInfo]:
        """Get followers of a user."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._get_followers_sync,
            username,
            target_user_id,
            amount,
        )

    def _get_followers_sync(
        self,
        username: str,
        target_user_id: str,
        amount: int,
    ) -> list[UserInfo]:
        """Synchronous followers fetch."""
        client = self._clients.get(username)
        if not client:
            return []

        try:
            followers = client.user_followers(target_user_id, amount=amount)
            return [
                UserInfo(
                    user_id=str(user.pk),
                    username=user.username,
                    full_name=user.full_name,
                    is_private=user.is_private,
                    is_verified=user.is_verified,
                )
                for user in followers.values()
            ]
        except Exception as e:
            logger.warning("Get followers failed: %s", e)
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
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._check_follow_status_sync,
            username,
            target_user_id,
        )

    def _check_follow_status_sync(
        self,
        username: str,
        target_user_id: str,
    ) -> dict[str, bool]:
        """Synchronous follow status check."""
        client = self._clients.get(username)
        if not client:
            return {"following": False, "followed_by": False}

        try:
            friendship = client.user_friendship_v1(target_user_id)
            return {
                "following": friendship.following,
                "followed_by": friendship.followed_by,
            }
        except Exception as e:
            logger.warning("Check follow status failed: %s", e)
            return {"following": False, "followed_by": False}

    def get_session(self, username: str) -> InstagramSession | None:
        """Get session for a username."""
        return self._sessions.get(username)

    def get_session_data(self, username: str) -> dict | None:
        """Get serializable session data for persistence."""
        session = self._sessions.get(username)
        if session:
            return session.session_data
        return None

    async def restore_session(
        self,
        username: str,
        session_data: dict,
        proxy: str | None = None,
    ) -> bool:
        """
        Restore a session from saved data without password.
        
        Args:
            username: Instagram username
            session_data: Saved session data from get_session_data()
            proxy: Optional proxy URL
            
        Returns:
            True if session restored successfully
        """
        try:
            # Try to login with saved session
            session = await self.login(
                username=username,
                password="",  # Not needed with session data
                proxy=proxy,
                session_data=session_data,
            )
            return session.status == AccountStatus.ACTIVE
        except Exception as e:
            logger.warning("Session restore failed for %s: %s", username, e)
            return False

    @property
    def active_sessions(self) -> int:
        """Number of active sessions."""
        return len(self._clients)


def create_instagram_api_service(session_manager=None) -> InstagramAPIService:
    """Factory function to create InstagramAPIService."""
    return InstagramAPIService(session_manager=session_manager)

