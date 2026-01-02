"""
Anti-detect browser integration service.
Provides integration with Multilogin and GoLogin for browser fingerprint isolation.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BrowserProvider(StrEnum):
    """Supported anti-detect browser providers."""
    MULTILOGIN = "multilogin"
    GOLOGIN = "gologin"


class BrowserProfileStatus(StrEnum):
    """Browser profile status."""
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class BrowserProfile:
    """Browser profile information."""
    profile_id: str
    name: str
    provider: BrowserProvider
    status: BrowserProfileStatus
    os: str
    browser_type: str
    proxy_id: str | None = None
    last_used: datetime | None = None
    fingerprint_id: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "provider": self.provider,
            "status": self.status,
            "os": self.os,
            "browser_type": self.browser_type,
            "proxy_id": self.proxy_id,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "fingerprint_id": self.fingerprint_id,
            "notes": self.notes,
        }


@dataclass
class BrowserSession:
    """Active browser session information."""
    session_id: str
    profile_id: str
    ws_endpoint: str
    debug_port: int
    started_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "ws_endpoint": self.ws_endpoint,
            "debug_port": self.debug_port,
            "started_at": self.started_at.isoformat(),
        }


class AntiDetectBrowserError(Exception):
    """Base exception for anti-detect browser errors."""
    pass


class BrowserNotConfiguredError(AntiDetectBrowserError):
    """Browser provider not configured."""
    pass


class ProfileNotFoundError(AntiDetectBrowserError):
    """Browser profile not found."""
    pass


class SessionStartError(AntiDetectBrowserError):
    """Failed to start browser session."""
    pass


class AntiDetectBrowserProvider(ABC):
    """Abstract base class for anti-detect browser providers."""

    @abstractmethod
    async def list_profiles(self) -> list[BrowserProfile]:
        pass

    @abstractmethod
    async def create_profile(
        self, name: str, os: str = "windows", browser_type: str = "chrome",
        proxy_config: dict[str, Any] | None = None,
    ) -> BrowserProfile:
        pass

    @abstractmethod
    async def delete_profile(self, profile_id: str) -> bool:
        pass

    @abstractmethod
    async def start_session(self, profile_id: str) -> BrowserSession:
        pass

    @abstractmethod
    async def stop_session(self, profile_id: str) -> bool:
        pass

    @abstractmethod
    async def update_proxy(self, profile_id: str, proxy_config: dict[str, Any]) -> bool:
        pass


class MultiloginProvider(AntiDetectBrowserProvider):
    """Multilogin API integration."""

    def __init__(self, api_token: str, base_url: str = "https://api.multilogin.com"):
        self.api_token = api_token
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"},
                timeout=30.0,
            )
        return self._client

    async def list_profiles(self) -> list[BrowserProfile]:
        client = await self._get_client()
        try:
            response = await client.get("/v2/profile")
            response.raise_for_status()
            data = response.json()
            return [
                BrowserProfile(
                    profile_id=item["uuid"], name=item.get("name", "Unnamed"),
                    provider=BrowserProvider.MULTILOGIN, status=BrowserProfileStatus.READY,
                    os=item.get("os", "windows"), browser_type=item.get("browser_type", "mimic"),
                    proxy_id=item.get("proxy", {}).get("id"), fingerprint_id=item.get("fingerprint_id"),
                )
                for item in data.get("data", [])
            ]
        except httpx.HTTPError as e:
            logger.exception("Multilogin API error")
            raise AntiDetectBrowserError(f"Failed to list profiles: {e}") from e

    async def create_profile(
        self, name: str, os: str = "windows", browser_type: str = "mimic",
        proxy_config: dict[str, Any] | None = None,
    ) -> BrowserProfile:
        client = await self._get_client()
        payload: dict[str, Any] = {
            "name": name, "browser_type": browser_type, "os_type": os,
            "parameters": {"flags": {"audio_masking": "mask", "fonts_masking": "mask",
                "geolocation_masking": "mask", "graphics_masking": "mask", "graphics_noise": "mask",
                "localization_masking": "mask", "media_devices_masking": "mask",
                "navigator_masking": "mask", "ports_masking": "mask", "screen_masking": "mask",
                "timezone_masking": "mask", "webrtc_masking": "mask"}},
        }
        if proxy_config:
            payload["proxy"] = {
                "type": proxy_config.get("type", "http"), "host": proxy_config["host"],
                "port": proxy_config["port"], "username": proxy_config.get("username"),
                "password": proxy_config.get("password"),
            }
        try:
            response = await client.post("/v2/profile", json=payload)
            response.raise_for_status()
            data = response.json()
            return BrowserProfile(
                profile_id=data["uuid"], name=name, provider=BrowserProvider.MULTILOGIN,
                status=BrowserProfileStatus.READY, os=os, browser_type=browser_type,
                proxy_id=data.get("proxy", {}).get("id"),
            )
        except httpx.HTTPError as e:
            raise AntiDetectBrowserError(f"Failed to create profile: {e}") from e

    async def delete_profile(self, profile_id: str) -> bool:
        client = await self._get_client()
        try:
            response = await client.delete(f"/v2/profile/{profile_id}")
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            raise ProfileNotFoundError(f"Profile not found: {profile_id}") from e

    async def start_session(self, profile_id: str) -> BrowserSession:
        client = await self._get_client()
        try:
            response = await client.get(f"/v2/profile/{profile_id}/start")
            response.raise_for_status()
            data = response.json()
            return BrowserSession(
                session_id=data.get("id", profile_id), profile_id=profile_id,
                ws_endpoint=data.get("webSocketDebuggerUrl", ""),
                debug_port=data.get("debug_port", 0), started_at=datetime.now(),
            )
        except httpx.HTTPError as e:
            raise SessionStartError(f"Failed to start session: {e}") from e

    async def stop_session(self, profile_id: str) -> bool:
        client = await self._get_client()
        try:
            response = await client.get(f"/v2/profile/{profile_id}/stop")
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def update_proxy(self, profile_id: str, proxy_config: dict[str, Any]) -> bool:
        client = await self._get_client()
        payload = {"proxy": {"type": proxy_config.get("type", "http"), "host": proxy_config["host"],
            "port": proxy_config["port"], "username": proxy_config.get("username"),
            "password": proxy_config.get("password")}}
        try:
            response = await client.patch(f"/v2/profile/{profile_id}", json=payload)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            raise AntiDetectBrowserError(f"Failed to update proxy: {e}") from e

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


class GoLoginProvider(AntiDetectBrowserProvider):
    """GoLogin API integration."""

    def __init__(self, api_token: str, base_url: str = "https://api.gologin.com"):
        self.api_token = api_token
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"},
                timeout=30.0,
            )
        return self._client

    async def list_profiles(self) -> list[BrowserProfile]:
        client = await self._get_client()
        try:
            response = await client.get("/browser/v2")
            response.raise_for_status()
            data = response.json()
            return [
                BrowserProfile(
                    profile_id=item["id"], name=item.get("name", "Unnamed"),
                    provider=BrowserProvider.GOLOGIN, status=BrowserProfileStatus.READY,
                    os=item.get("os", "win"), browser_type="orbita",
                    proxy_id=item.get("proxy", {}).get("id"),
                )
                for item in data.get("profiles", [])
            ]
        except httpx.HTTPError as e:
            raise AntiDetectBrowserError(f"Failed to list profiles: {e}") from e

    async def create_profile(
        self, name: str, os: str = "win", browser_type: str = "orbita",
        proxy_config: dict[str, Any] | None = None,
    ) -> BrowserProfile:
        client = await self._get_client()
        payload: dict[str, Any] = {
            "name": name, "os": os,
            "navigator": {"userAgent": "random", "resolution": "random", "language": "en-US"},
            "proxyEnabled": bool(proxy_config),
        }
        if proxy_config:
            payload["proxy"] = {
                "mode": proxy_config.get("type", "http"), "host": proxy_config["host"],
                "port": proxy_config["port"], "username": proxy_config.get("username", ""),
                "password": proxy_config.get("password", ""),
            }
        try:
            response = await client.post("/browser/v2", json=payload)
            response.raise_for_status()
            data = response.json()
            return BrowserProfile(
                profile_id=data["id"], name=name, provider=BrowserProvider.GOLOGIN,
                status=BrowserProfileStatus.READY, os=os, browser_type=browser_type,
            )
        except httpx.HTTPError as e:
            raise AntiDetectBrowserError(f"Failed to create profile: {e}") from e

    async def delete_profile(self, profile_id: str) -> bool:
        client = await self._get_client()
        try:
            response = await client.delete(f"/browser/{profile_id}")
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            raise ProfileNotFoundError(f"Profile not found: {profile_id}") from e

    async def start_session(self, profile_id: str) -> BrowserSession:
        client = await self._get_client()
        try:
            response = await client.post(f"/browser/{profile_id}/start")
            response.raise_for_status()
            data = response.json()
            return BrowserSession(
                session_id=data.get("id", profile_id), profile_id=profile_id,
                ws_endpoint=data.get("wsUrl", ""), debug_port=data.get("port", 0),
                started_at=datetime.now(),
            )
        except httpx.HTTPError as e:
            raise SessionStartError(f"Failed to start session: {e}") from e

    async def stop_session(self, profile_id: str) -> bool:
        client = await self._get_client()
        try:
            response = await client.post(f"/browser/{profile_id}/stop")
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def update_proxy(self, profile_id: str, proxy_config: dict[str, Any]) -> bool:
        client = await self._get_client()
        payload = {"proxyEnabled": True, "proxy": {
            "mode": proxy_config.get("type", "http"), "host": proxy_config["host"],
            "port": proxy_config["port"], "username": proxy_config.get("username", ""),
            "password": proxy_config.get("password", ""),
        }}
        try:
            response = await client.put(f"/browser/{profile_id}", json=payload)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            raise AntiDetectBrowserError(f"Failed to update proxy: {e}") from e

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


class AntiDetectBrowserService:
    """Unified service for managing anti-detect browser profiles."""

    def __init__(self):
        self._providers: dict[BrowserProvider, AntiDetectBrowserProvider] = {}

    def configure_provider(
        self, provider: BrowserProvider, api_token: str, base_url: str | None = None,
    ) -> None:
        """Configure a browser provider with API credentials."""
        if provider == BrowserProvider.MULTILOGIN:
            self._providers[provider] = MultiloginProvider(
                api_token=api_token, base_url=base_url or "https://api.multilogin.com",
            )
        elif provider == BrowserProvider.GOLOGIN:
            self._providers[provider] = GoLoginProvider(
                api_token=api_token, base_url=base_url or "https://api.gologin.com",
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        logger.info("Configured anti-detect browser provider: %s", provider)

    def get_provider(self, provider: BrowserProvider) -> AntiDetectBrowserProvider:
        """Get a configured provider."""
        if provider not in self._providers:
            raise BrowserNotConfiguredError(f"Provider {provider} not configured.")
        return self._providers[provider]

    async def create_profile_for_account(
        self, account_name: str, provider: BrowserProvider,
        proxy_config: dict[str, Any] | None = None,
    ) -> BrowserProfile:
        """Create a browser profile for a sub-account."""
        browser_provider = self.get_provider(provider)
        profile = await browser_provider.create_profile(
            name=f"account_{account_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            proxy_config=proxy_config,
        )
        logger.info("Created browser profile %s for account %s", profile.profile_id, account_name)
        return profile

    async def start_automation_session(
        self, profile_id: str, provider: BrowserProvider,
    ) -> BrowserSession:
        """Start a browser session for automation tasks."""
        browser_provider = self.get_provider(provider)
        session = await browser_provider.start_session(profile_id)
        logger.info("Started browser session for profile %s", profile_id)
        return session

    async def stop_automation_session(
        self, profile_id: str, provider: BrowserProvider,
    ) -> bool:
        """Stop a browser session."""
        browser_provider = self.get_provider(provider)
        result = await browser_provider.stop_session(profile_id)
        if result:
            logger.info("Stopped browser session for profile %s", profile_id)
        return result

    async def list_all_profiles(
        self, provider: BrowserProvider | None = None,
    ) -> list[BrowserProfile]:
        """List profiles from one or all configured providers."""
        profiles: list[BrowserProfile] = []
        if provider:
            browser_provider = self.get_provider(provider)
            profiles = await browser_provider.list_profiles()
        else:
            for p, browser_provider in self._providers.items():
                try:
                    provider_profiles = await browser_provider.list_profiles()
                    profiles.extend(provider_profiles)
                except Exception as e:
                    logger.warning("Failed to list profiles from %s: %s", p, e)
        return profiles

    async def cleanup(self):
        """Clean up all provider connections."""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()


def create_antidetect_browser_service() -> AntiDetectBrowserService:
    """Factory function to create AntiDetectBrowserService."""
    return AntiDetectBrowserService()
