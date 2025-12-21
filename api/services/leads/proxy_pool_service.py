"""
Residential proxy pool management service.
Manages proxy configuration, rotation, and health monitoring.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ProxyType(StrEnum):
    """Proxy protocol types."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyStatus(StrEnum):
    """Proxy health status."""
    ACTIVE = "active"
    SLOW = "slow"
    FAILED = "failed"
    BANNED = "banned"
    COOLING = "cooling"


class ProxyQuality(StrEnum):
    """Proxy quality tier."""
    RESIDENTIAL = "residential"  # Best quality, real ISP IPs
    DATACENTER = "datacenter"    # Fast but easily detected
    MOBILE = "mobile"            # Expensive but highest trust


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    id: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    proxy_type: ProxyType = ProxyType.HTTP
    quality: ProxyQuality = ProxyQuality.RESIDENTIAL
    country: str | None = None
    city: str | None = None
    isp: str | None = None
    status: ProxyStatus = ProxyStatus.ACTIVE
    # Performance metrics
    avg_response_time_ms: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0
    failed_requests: int = 0
    last_used_at: datetime | None = None
    last_check_at: datetime | None = None
    cooling_until: datetime | None = None
    # Assignment
    assigned_to_account_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "host": self.host, "port": self.port,
            "username": self.username, "proxy_type": self.proxy_type,
            "quality": self.quality, "country": self.country, "city": self.city,
            "isp": self.isp, "status": self.status,
            "avg_response_time_ms": self.avg_response_time_ms,
            "success_rate": self.success_rate, "total_requests": self.total_requests,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    def to_connection_string(self) -> str:
        """Generate proxy connection string."""
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.proxy_type}://{auth}{self.host}:{self.port}"

    def to_playwright_config(self) -> dict[str, Any]:
        """Generate config for Playwright proxy."""
        config: dict[str, Any] = {"server": f"{self.proxy_type}://{self.host}:{self.port}"}
        if self.username:
            config["username"] = self.username
            config["password"] = self.password or ""
        return config


@dataclass
class HealthCheckResult:
    """Proxy health check result."""
    proxy_id: str
    is_healthy: bool
    response_time_ms: float
    external_ip: str | None = None
    country_detected: str | None = None
    error_message: str | None = None
    checked_at: datetime = field(default_factory=datetime.now)


class ProxyPoolError(Exception):
    """Base exception for proxy pool errors."""
    pass


class NoAvailableProxyError(ProxyPoolError):
    """No available proxy in the pool."""
    pass


class ProxyPoolService:
    """
    Service for managing residential proxy pool.
    Handles proxy rotation, health checks, and assignment to sub-accounts.
    """

    def __init__(self):
        self._proxies: dict[str, ProxyConfig] = {}
        self._account_proxy_map: dict[str, str] = {}  # account_id -> proxy_id
        self._check_url = "https://httpbin.org/ip"
        self._check_timeout = 10.0
        self._cooling_duration = timedelta(minutes=30)
        self._max_consecutive_failures = 3

    def add_proxy(self, proxy: ProxyConfig) -> None:
        """Add a proxy to the pool."""
        self._proxies[proxy.id] = proxy
        logger.info("Added proxy %s (%s:%d) to pool", proxy.id, proxy.host, proxy.port)

    def add_proxies_from_list(
        self,
        proxy_list: list[dict[str, Any]],
        quality: ProxyQuality = ProxyQuality.RESIDENTIAL,
    ) -> int:
        """
        Bulk add proxies from a list of dicts.
        Format: [{"host": "x.x.x.x", "port": 1234, "username": "u", "password": "p", ...}, ...]
        """
        count = 0
        for i, p in enumerate(proxy_list):
            proxy_id = p.get("id", f"proxy_{i}_{p['host']}_{p['port']}")
            proxy = ProxyConfig(
                id=proxy_id, host=p["host"], port=p["port"],
                username=p.get("username"), password=p.get("password"),
                proxy_type=ProxyType(p.get("type", "http")),
                quality=ProxyQuality(p.get("quality", quality)),
                country=p.get("country"), city=p.get("city"), isp=p.get("isp"),
            )
            self.add_proxy(proxy)
            count += 1
        logger.info("Added %s proxies to pool", count)
        return count

    def remove_proxy(self, proxy_id: str) -> bool:
        """Remove a proxy from the pool."""
        if proxy_id in self._proxies:
            del self._proxies[proxy_id]
            # Remove any account assignments
            self._account_proxy_map = {
                k: v for k, v in self._account_proxy_map.items() if v != proxy_id
            }
            logger.info("Removed proxy %s from pool", proxy_id)
            return True
        return False

    def get_proxy(self, proxy_id: str) -> ProxyConfig | None:
        """Get a specific proxy by ID."""
        return self._proxies.get(proxy_id)

    def get_available_proxies(
        self,
        country: str | None = None,
        quality: ProxyQuality | None = None,
        exclude_assigned: bool = False,
    ) -> list[ProxyConfig]:
        """Get list of available proxies with optional filters."""
        now = datetime.now()
        available = []
        for proxy in self._proxies.values():
            # Skip non-active proxies
            if proxy.status == ProxyStatus.BANNED:
                continue
            if proxy.status == ProxyStatus.COOLING:
                if proxy.cooling_until and proxy.cooling_until > now:
                    continue
                # Cooling period ended, reset status
                proxy.status = ProxyStatus.ACTIVE
            # Apply filters
            if country and proxy.country != country:
                continue
            if quality and proxy.quality != quality:
                continue
            if exclude_assigned and proxy.assigned_to_account_id:
                continue
            available.append(proxy)
        return available

    def get_best_proxy(
        self,
        country: str | None = None,
        quality: ProxyQuality | None = None,
    ) -> ProxyConfig:
        """Get the best available proxy based on performance metrics."""
        available = self.get_available_proxies(country=country, quality=quality)
        if not available:
            raise NoAvailableProxyError("No available proxies in pool")
        # Sort by success rate (desc) and response time (asc)
        available.sort(key=lambda p: (-p.success_rate, p.avg_response_time_ms))
        return available[0]

    def get_random_proxy(
        self,
        country: str | None = None,
        quality: ProxyQuality | None = None,
    ) -> ProxyConfig:
        """Get a random available proxy."""
        available = self.get_available_proxies(country=country, quality=quality)
        if not available:
            raise NoAvailableProxyError("No available proxies in pool")
        return random.choice(available)  # noqa: S311

    def assign_proxy_to_account(
        self,
        account_id: str,
        proxy_id: str | None = None,
        country: str | None = None,
    ) -> ProxyConfig:
        """Assign a proxy to a sub-account (sticky assignment)."""
        # Check if account already has an assigned proxy
        if account_id in self._account_proxy_map:
            existing_proxy_id = self._account_proxy_map[account_id]
            if existing_proxy_id in self._proxies:
                return self._proxies[existing_proxy_id]
        # Assign specified proxy or get best available
        if proxy_id and proxy_id in self._proxies:
            proxy = self._proxies[proxy_id]
        else:
            proxy = self.get_best_proxy(country=country, exclude_assigned=True)
        proxy.assigned_to_account_id = account_id
        self._account_proxy_map[account_id] = proxy.id
        logger.info("Assigned proxy %s to account %s", proxy.id, account_id)
        return proxy

    def get_account_proxy(self, account_id: str) -> ProxyConfig | None:
        """Get the proxy assigned to a specific account."""
        proxy_id = self._account_proxy_map.get(account_id)
        if proxy_id:
            return self._proxies.get(proxy_id)
        return None

    def release_account_proxy(self, account_id: str) -> bool:
        """Release proxy assignment for an account."""
        if account_id in self._account_proxy_map:
            proxy_id = self._account_proxy_map.pop(account_id)
            if proxy_id in self._proxies:
                self._proxies[proxy_id].assigned_to_account_id = None
            logger.info("Released proxy assignment for account %s", account_id)
            return True
        return False

    def rotate_account_proxy(
        self,
        account_id: str,
        country: str | None = None,
    ) -> ProxyConfig:
        """Rotate to a new proxy for an account."""
        # Release current assignment
        self.release_account_proxy(account_id)
        # Get a new proxy (excluding the previous one if possible)
        return self.assign_proxy_to_account(account_id, country=country)

    async def check_proxy_health(self, proxy_id: str) -> HealthCheckResult:
        """Perform health check on a proxy."""
        proxy = self.get_proxy(proxy_id)
        if not proxy:
            return HealthCheckResult(proxy_id=proxy_id, is_healthy=False,
                response_time_ms=0, error_message="Proxy not found")

        start_time = datetime.now()
        try:
            async with httpx.AsyncClient(
                proxies={f"{proxy.proxy_type}://": proxy.to_connection_string()},
                timeout=self._check_timeout,
            ) as client:
                response = await client.get(self._check_url)
                response.raise_for_status()
                data = response.json()

            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            external_ip = data.get("origin", "").split(",")[0].strip()

            # Update proxy metrics
            proxy.total_requests += 1
            proxy.avg_response_time_ms = (
                (proxy.avg_response_time_ms * (proxy.total_requests - 1) + elapsed)
                / proxy.total_requests
            )
            proxy.success_rate = 1 - (proxy.failed_requests / proxy.total_requests)
            proxy.last_check_at = datetime.now()
            proxy.status = ProxyStatus.ACTIVE if elapsed < 5000 else ProxyStatus.SLOW

            return HealthCheckResult(
                proxy_id=proxy_id, is_healthy=True, response_time_ms=elapsed,
                external_ip=external_ip, checked_at=datetime.now(),
            )

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            proxy.total_requests += 1
            proxy.failed_requests += 1
            proxy.success_rate = 1 - (proxy.failed_requests / proxy.total_requests)
            proxy.last_check_at = datetime.now()

            # Check if should mark as failed/cooling
            if proxy.failed_requests >= self._max_consecutive_failures:
                proxy.status = ProxyStatus.COOLING
                proxy.cooling_until = datetime.now() + self._cooling_duration

            return HealthCheckResult(
                proxy_id=proxy_id, is_healthy=False, response_time_ms=elapsed,
                error_message=str(e), checked_at=datetime.now(),
            )

    async def check_all_proxies(self) -> list[HealthCheckResult]:
        """Check health of all proxies in the pool."""
        results = []
        for proxy_id in list(self._proxies.keys()):
            result = await self.check_proxy_health(proxy_id)
            results.append(result)
        return results

    def mark_proxy_banned(self, proxy_id: str, reason: str | None = None) -> bool:
        """Mark a proxy as banned (permanently removed from rotation)."""
        proxy = self.get_proxy(proxy_id)
        if proxy:
            proxy.status = ProxyStatus.BANNED
            logger.warning("Proxy %s marked as banned: %s", proxy_id, reason)
            return True
        return False

    def get_pool_stats(self) -> dict[str, Any]:
        """Get overall pool statistics."""
        total = len(self._proxies)
        by_status = dict.fromkeys(ProxyStatus, 0)
        by_quality = dict.fromkeys(ProxyQuality, 0)
        assigned = 0

        for proxy in self._proxies.values():
            by_status[proxy.status] += 1
            by_quality[proxy.quality] += 1
            if proxy.assigned_to_account_id:
                assigned += 1

        return {
            "total": total,
            "active": by_status[ProxyStatus.ACTIVE],
            "slow": by_status[ProxyStatus.SLOW],
            "cooling": by_status[ProxyStatus.COOLING],
            "banned": by_status[ProxyStatus.BANNED],
            "failed": by_status[ProxyStatus.FAILED],
            "assigned": assigned,
            "available": total - assigned - by_status[ProxyStatus.BANNED],
            "by_quality": {k.value: v for k, v in by_quality.items()},
        }


def create_proxy_pool_service() -> ProxyPoolService:
    """Factory function to create ProxyPoolService."""
    return ProxyPoolService()
