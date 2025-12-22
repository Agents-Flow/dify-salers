"""
Session Manager Service for social media API sessions.
Provides Redis-based persistence for login sessions (Instagram, Twitter/X).

This service enables:
- Session persistence across server restarts
- Session sharing across multiple workers
- Session expiration and cleanup
- Concurrent session management for 1000+ accounts

Architecture:
    Redis Key Structure:
    - social:session:{platform}:{username} -> JSON session data
    - social:session:index:{platform} -> Set of active usernames
    - social:session:locks:{platform}:{username} -> Distributed lock

Memory: Each session ~2-5KB in Redis vs 300MB browser state
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

# Default session TTL: 7 days
DEFAULT_SESSION_TTL = 60 * 60 * 24 * 7

# Lock TTL for distributed operations
LOCK_TTL = 30


class Platform(StrEnum):
    """Supported platforms."""
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    X = "x"  # Alias for twitter


@dataclass
class StoredSession:
    """Session data structure for storage."""
    platform: str
    username: str
    user_id: str | None
    session_data: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    last_action_at: datetime | None
    error_count: int
    proxy_config: dict[str, Any] | None
    metadata: dict[str, Any]

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "platform": self.platform,
            "username": self.username,
            "user_id": self.user_id,
            "session_data": self.session_data,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_action_at": self.last_action_at.isoformat() if self.last_action_at else None,
            "error_count": self.error_count,
            "proxy_config": self.proxy_config,
            "metadata": self.metadata,
        })

    @classmethod
    def from_json(cls, data: str) -> "StoredSession":
        """Deserialize from JSON."""
        obj = json.loads(data)
        return cls(
            platform=obj["platform"],
            username=obj["username"],
            user_id=obj.get("user_id"),
            session_data=obj.get("session_data", {}),
            status=obj.get("status", "unknown"),
            created_at=datetime.fromisoformat(obj["created_at"]),
            updated_at=datetime.fromisoformat(obj["updated_at"]),
            last_action_at=datetime.fromisoformat(obj["last_action_at"]) if obj.get("last_action_at") else None,
            error_count=obj.get("error_count", 0),
            proxy_config=obj.get("proxy_config"),
            metadata=obj.get("metadata", {}),
        )


class SessionManagerService:
    """
    Redis-based session manager for social media API sessions.
    
    This service manages session persistence for Instagram and Twitter/X
    API clients, enabling:
    
    - Session restoration after server restarts
    - Distributed session access across workers
    - Automatic session expiration
    - Session health tracking
    
    Usage:
        manager = SessionManagerService(redis_client)
        
        # Store session
        await manager.store_session(
            platform="instagram",
            username="user123",
            session_data={"cookies": {...}},
            user_id="12345",
        )
        
        # Retrieve session
        session = await manager.get_session("instagram", "user123")
        
        # List all sessions
        sessions = await manager.list_sessions("instagram")
    """

    # Redis key prefixes
    SESSION_KEY_PREFIX = "social:session"
    INDEX_KEY_PREFIX = "social:session:index"
    LOCK_KEY_PREFIX = "social:session:locks"

    def __init__(self, redis_client=None):
        """
        Initialize session manager.
        
        Args:
            redis_client: Redis client instance (from extensions.ext_redis)
        """
        self._redis = redis_client
        self._local_cache: dict[str, StoredSession] = {}
        self._cache_lock = asyncio.Lock()

    def _get_redis(self):
        """Get Redis client, lazy load if not provided."""
        if self._redis is None:
            try:
                from extensions.ext_redis import redis_client
                self._redis = redis_client
            except ImportError:
                logger.warning("Redis not available, using local cache only")
        return self._redis

    def _session_key(self, platform: str, username: str) -> str:
        """Generate Redis key for a session."""
        platform = self._normalize_platform(platform)
        return f"{self.SESSION_KEY_PREFIX}:{platform}:{username}"

    def _index_key(self, platform: str) -> str:
        """Generate Redis key for platform session index."""
        platform = self._normalize_platform(platform)
        return f"{self.INDEX_KEY_PREFIX}:{platform}"

    def _lock_key(self, platform: str, username: str) -> str:
        """Generate Redis key for session lock."""
        platform = self._normalize_platform(platform)
        return f"{self.LOCK_KEY_PREFIX}:{platform}:{username}"

    def _normalize_platform(self, platform: str) -> str:
        """Normalize platform name."""
        platform = platform.lower()
        if platform == "x":
            return "twitter"
        return platform

    async def store_session(
        self,
        platform: str,
        username: str,
        session_data: dict[str, Any],
        user_id: str | None = None,
        status: str = "active",
        proxy_config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        ttl: int = DEFAULT_SESSION_TTL,
    ) -> bool:
        """
        Store a session in Redis.
        
        Args:
            platform: Platform name (instagram, twitter, x)
            username: Account username
            session_data: Session data (cookies, tokens, device settings)
            user_id: Platform user ID
            status: Session status
            proxy_config: Proxy configuration for this session
            metadata: Additional metadata
            ttl: Time-to-live in seconds
            
        Returns:
            True if stored successfully
        """
        platform = self._normalize_platform(platform)
        now = datetime.utcnow()

        # Create or update session
        existing = await self.get_session(platform, username)
        if existing:
            session = StoredSession(
                platform=platform,
                username=username,
                user_id=user_id or existing.user_id,
                session_data=session_data,
                status=status,
                created_at=existing.created_at,
                updated_at=now,
                last_action_at=existing.last_action_at,
                error_count=existing.error_count if status == "active" else existing.error_count + 1,
                proxy_config=proxy_config or existing.proxy_config,
                metadata={**existing.metadata, **(metadata or {})},
            )
        else:
            session = StoredSession(
                platform=platform,
                username=username,
                user_id=user_id,
                session_data=session_data,
                status=status,
                created_at=now,
                updated_at=now,
                last_action_at=None,
                error_count=0,
                proxy_config=proxy_config,
                metadata=metadata or {},
            )

        # Store in Redis
        redis = self._get_redis()
        if redis:
            try:
                key = self._session_key(platform, username)
                index_key = self._index_key(platform)
                
                # Use pipeline for atomic operations
                pipe = redis.pipeline()
                pipe.setex(key, ttl, session.to_json())
                pipe.sadd(index_key, username)
                pipe.execute()
                
                logger.debug("Stored session for %s:%s", platform, username)
            except Exception as e:
                logger.warning("Failed to store session in Redis: %s", e)
                # Fallback to local cache
                async with self._cache_lock:
                    self._local_cache[f"{platform}:{username}"] = session
        else:
            # Local cache only
            async with self._cache_lock:
                self._local_cache[f"{platform}:{username}"] = session

        return True

    async def get_session(
        self,
        platform: str,
        username: str,
    ) -> StoredSession | None:
        """
        Retrieve a session from Redis.
        
        Args:
            platform: Platform name
            username: Account username
            
        Returns:
            StoredSession if found, None otherwise
        """
        platform = self._normalize_platform(platform)
        cache_key = f"{platform}:{username}"

        # Try Redis first
        redis = self._get_redis()
        if redis:
            try:
                key = self._session_key(platform, username)
                data = redis.get(key)
                if data:
                    return StoredSession.from_json(data)
            except Exception as e:
                logger.warning("Failed to get session from Redis: %s", e)

        # Fallback to local cache
        async with self._cache_lock:
            return self._local_cache.get(cache_key)

    async def get_session_data(
        self,
        platform: str,
        username: str,
    ) -> dict[str, Any] | None:
        """Get just the session_data dict for a session."""
        session = await self.get_session(platform, username)
        return session.session_data if session else None

    async def delete_session(
        self,
        platform: str,
        username: str,
    ) -> bool:
        """
        Delete a session.
        
        Args:
            platform: Platform name
            username: Account username
            
        Returns:
            True if deleted
        """
        platform = self._normalize_platform(platform)
        cache_key = f"{platform}:{username}"

        # Delete from Redis
        redis = self._get_redis()
        if redis:
            try:
                key = self._session_key(platform, username)
                index_key = self._index_key(platform)
                
                pipe = redis.pipeline()
                pipe.delete(key)
                pipe.srem(index_key, username)
                pipe.execute()
            except Exception as e:
                logger.warning("Failed to delete session from Redis: %s", e)

        # Delete from local cache
        async with self._cache_lock:
            self._local_cache.pop(cache_key, None)

        return True

    async def list_sessions(
        self,
        platform: str,
        status: str | None = None,
    ) -> list[StoredSession]:
        """
        List all sessions for a platform.
        
        Args:
            platform: Platform name
            status: Optional status filter
            
        Returns:
            List of StoredSession objects
        """
        platform = self._normalize_platform(platform)
        sessions = []

        redis = self._get_redis()
        if redis:
            try:
                index_key = self._index_key(platform)
                usernames = redis.smembers(index_key)
                
                for username in usernames:
                    if isinstance(username, bytes):
                        username = username.decode()
                    session = await self.get_session(platform, username)
                    if session:
                        if status is None or session.status == status:
                            sessions.append(session)
            except Exception as e:
                logger.warning("Failed to list sessions from Redis: %s", e)

        # Also check local cache
        async with self._cache_lock:
            for key, session in self._local_cache.items():
                if key.startswith(f"{platform}:"):
                    if status is None or session.status == status:
                        if session not in sessions:
                            sessions.append(session)

        return sessions

    async def list_usernames(self, platform: str) -> list[str]:
        """Get list of usernames with sessions for a platform."""
        platform = self._normalize_platform(platform)
        usernames = set()

        redis = self._get_redis()
        if redis:
            try:
                index_key = self._index_key(platform)
                members = redis.smembers(index_key)
                for m in members:
                    if isinstance(m, bytes):
                        m = m.decode()
                    usernames.add(m)
            except Exception as e:
                logger.warning("Failed to list usernames from Redis: %s", e)

        # Also check local cache
        async with self._cache_lock:
            for key in self._local_cache:
                if key.startswith(f"{platform}:"):
                    usernames.add(key.split(":", 1)[1])

        return list(usernames)

    async def update_status(
        self,
        platform: str,
        username: str,
        status: str,
        error_message: str | None = None,
    ) -> bool:
        """Update session status."""
        session = await self.get_session(platform, username)
        if not session:
            return False

        session.status = status
        session.updated_at = datetime.utcnow()
        if status != "active":
            session.error_count += 1
        if error_message:
            session.metadata["last_error"] = error_message

        return await self.store_session(
            platform=session.platform,
            username=session.username,
            session_data=session.session_data,
            user_id=session.user_id,
            status=session.status,
            proxy_config=session.proxy_config,
            metadata=session.metadata,
        )

    async def update_last_action(
        self,
        platform: str,
        username: str,
    ) -> bool:
        """Update last action timestamp."""
        session = await self.get_session(platform, username)
        if not session:
            return False

        session.last_action_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()

        return await self.store_session(
            platform=session.platform,
            username=session.username,
            session_data=session.session_data,
            user_id=session.user_id,
            status=session.status,
            proxy_config=session.proxy_config,
            metadata=session.metadata,
        )

    async def acquire_lock(
        self,
        platform: str,
        username: str,
        ttl: int = LOCK_TTL,
    ) -> bool:
        """
        Acquire a distributed lock for a session.
        Used to prevent concurrent operations on same account.
        
        Args:
            platform: Platform name
            username: Account username
            ttl: Lock TTL in seconds
            
        Returns:
            True if lock acquired
        """
        redis = self._get_redis()
        if not redis:
            return True  # No Redis, assume lock acquired

        try:
            lock_key = self._lock_key(platform, username)
            # SET NX with TTL
            acquired = redis.set(lock_key, "1", ex=ttl, nx=True)
            return bool(acquired)
        except Exception as e:
            logger.warning("Failed to acquire lock: %s", e)
            return True  # Fail open

    async def release_lock(
        self,
        platform: str,
        username: str,
    ) -> bool:
        """Release a distributed lock."""
        redis = self._get_redis()
        if not redis:
            return True

        try:
            lock_key = self._lock_key(platform, username)
            redis.delete(lock_key)
            return True
        except Exception as e:
            logger.warning("Failed to release lock: %s", e)
            return False

    async def get_stats(self, platform: str | None = None) -> dict[str, Any]:
        """
        Get session statistics.
        
        Args:
            platform: Optional platform filter
            
        Returns:
            Dict with session counts by status
        """
        stats = {
            "total": 0,
            "active": 0,
            "rate_limited": 0,
            "challenge_required": 0,
            "banned": 0,
            "unknown": 0,
            "by_platform": {},
        }

        platforms = [platform] if platform else ["instagram", "twitter"]
        
        for p in platforms:
            sessions = await self.list_sessions(p)
            platform_stats = {
                "total": len(sessions),
                "active": sum(1 for s in sessions if s.status == "active"),
                "rate_limited": sum(1 for s in sessions if s.status == "rate_limited"),
                "challenge_required": sum(1 for s in sessions if s.status == "challenge_required"),
                "banned": sum(1 for s in sessions if s.status in ("banned", "suspended", "locked")),
            }
            stats["by_platform"][p] = platform_stats
            stats["total"] += platform_stats["total"]
            stats["active"] += platform_stats["active"]
            stats["rate_limited"] += platform_stats["rate_limited"]
            stats["challenge_required"] += platform_stats["challenge_required"]
            stats["banned"] += platform_stats["banned"]

        return stats

    async def cleanup_expired(
        self,
        platform: str,
        max_age_days: int = 30,
    ) -> int:
        """
        Cleanup expired sessions.
        
        Args:
            platform: Platform name
            max_age_days: Maximum session age in days
            
        Returns:
            Number of sessions cleaned up
        """
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        sessions = await self.list_sessions(platform)
        
        cleaned = 0
        for session in sessions:
            if session.updated_at < cutoff:
                await self.delete_session(platform, session.username)
                cleaned += 1

        logger.info("Cleaned up %d expired sessions for %s", cleaned, platform)
        return cleaned

    async def bulk_store_sessions(
        self,
        sessions: list[dict[str, Any]],
    ) -> int:
        """
        Bulk store multiple sessions.
        
        Args:
            sessions: List of session dicts with platform, username, session_data, etc.
            
        Returns:
            Number of sessions stored
        """
        stored = 0
        for s in sessions:
            try:
                await self.store_session(
                    platform=s["platform"],
                    username=s["username"],
                    session_data=s.get("session_data", {}),
                    user_id=s.get("user_id"),
                    status=s.get("status", "active"),
                    proxy_config=s.get("proxy_config"),
                    metadata=s.get("metadata"),
                )
                stored += 1
            except Exception as e:
                logger.warning("Failed to store session: %s", e)

        return stored


def create_session_manager_service(redis_client=None) -> SessionManagerService:
    """Factory function to create SessionManagerService."""
    return SessionManagerService(redis_client=redis_client)

