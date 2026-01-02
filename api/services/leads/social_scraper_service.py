"""
Social media scraper service for X and Instagram.
Uses Apify API for follower scraping from target KOL accounts.

Supported platforms:
- X (formerly Twitter)
- Instagram

Apify Actors used:
- Instagram: apify/instagram-scraper
- X/Twitter: apify/twitter-scraper
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ScrapedFollower:
    """Standardized follower data structure."""

    platform_user_id: str
    username: str
    platform: str  # "x" | "instagram"
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    is_verified: bool = False
    is_private: bool = False


class SocialScraperError(Exception):
    """Base exception for social scraper errors."""


class ApifyNotConfiguredError(SocialScraperError):
    """Apify API is not properly configured."""


class ApifyAPIError(SocialScraperError):
    """Error from Apify API."""


class SocialScraperService:
    """
    Service for scraping followers from X and Instagram using Apify.

    Configuration via environment variables:
        - APIFY_API_TOKEN: Your Apify API token
        - APIFY_ENABLED: Enable/disable Apify integration (default: false)

    Usage:
        scraper = SocialScraperService()
        followers = scraper.scrape_followers(
            platform="instagram",
            username="target_kol_username",
            max_followers=1000
        )
    """

    # Environment configuration
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
    APIFY_ENABLED = os.getenv("APIFY_ENABLED", "false").lower() == "true"

    # Apify Actor IDs
    INSTAGRAM_ACTOR = "apify/instagram-scraper"
    TWITTER_ACTOR = "apify/twitter-scraper"

    # Apify API base URL
    APIFY_API_BASE = "https://api.apify.com/v2"

    def __init__(self):
        """Initialize the scraper service."""
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Check if Apify is properly configured."""
        if not self.APIFY_ENABLED:
            logger.info("Apify integration is disabled")
        elif not self.APIFY_API_TOKEN:
            logger.warning(
                "APIFY_API_TOKEN not set. Apify integration will not work. "
                "Set APIFY_ENABLED=false to disable this warning."
            )

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Apify is properly configured and enabled."""
        return cls.APIFY_ENABLED and bool(cls.APIFY_API_TOKEN)

    def scrape_followers(
        self,
        platform: str,
        username: str,
        max_followers: int = 1000,
        timeout: int = 300,
    ) -> list[ScrapedFollower]:
        """
        Scrape followers from a target account.

        Args:
            platform: Target platform ("x" or "instagram")
            username: Target account username
            max_followers: Maximum number of followers to scrape
            timeout: Timeout in seconds for the API call

        Returns:
            List of ScrapedFollower objects

        Raises:
            ApifyNotConfiguredError: If Apify is not configured
            ApifyAPIError: If the API call fails
        """
        if not self.is_configured():
            logger.warning("Apify not configured, returning empty results")
            return []

        logger.info("Starting follower scrape for %s on %s (max: %s)", username, platform, max_followers)

        if platform == "instagram":
            return self._scrape_instagram_followers(username, max_followers, timeout)
        elif platform == "x":
            return self._scrape_twitter_followers(username, max_followers, timeout)
        else:
            logger.warning("Unsupported platform for follower scraping: %s", platform)
            return []

    def _scrape_instagram_followers(
        self,
        username: str,
        max_followers: int,
        timeout: int,
    ) -> list[ScrapedFollower]:
        """Scrape followers from Instagram using Apify."""
        # Apify Instagram Scraper input
        run_input = {
            "usernames": [username],
            "resultsType": "followers",
            "resultsLimit": max_followers,
            "searchType": "user",
            "scrapeUserData": True,
        }

        try:
            results = self._run_apify_actor(self.INSTAGRAM_ACTOR, run_input, timeout)
            return self._parse_instagram_followers(results)
        except Exception as e:
            logger.exception("Instagram follower scrape failed for %s", username)
            raise ApifyAPIError(f"Instagram scrape failed: {e}") from e

    def _scrape_twitter_followers(
        self,
        username: str,
        max_followers: int,
        timeout: int,
    ) -> list[ScrapedFollower]:
        """Scrape followers from X/Twitter using Apify."""
        # Apify Twitter Scraper input
        run_input = {
            "handles": [username],
            "mode": "followers",
            "maxItems": max_followers,
            "includeUserInfo": True,
        }

        try:
            results = self._run_apify_actor(self.TWITTER_ACTOR, run_input, timeout)
            return self._parse_twitter_followers(results)
        except Exception as e:
            logger.exception("Twitter follower scrape failed for %s", username)
            raise ApifyAPIError(f"Twitter scrape failed: {e}") from e

    def _run_apify_actor(
        self,
        actor_id: str,
        run_input: dict[str, Any],
        timeout: int,
    ) -> list[dict[str, Any]]:
        """
        Run an Apify actor and wait for results.

        Args:
            actor_id: The Apify actor ID
            run_input: Input configuration for the actor
            timeout: Timeout in seconds

        Returns:
            List of result items from the actor run
        """
        headers = {"Authorization": f"Bearer {self.APIFY_API_TOKEN}"}

        # Start the actor run
        start_url = f"{self.APIFY_API_BASE}/acts/{actor_id}/runs"

        with httpx.Client(timeout=timeout) as client:
            # Start the run
            response = client.post(
                start_url,
                headers=headers,
                json=run_input,
                params={"waitForFinish": timeout},  # Wait for completion
            )

            if response.status_code != 201:
                raise ApifyAPIError(f"Failed to start actor: {response.status_code} - {response.text}")

            run_data = response.json()
            run_id = run_data.get("data", {}).get("id")

            if not run_id:
                raise ApifyAPIError("No run ID returned from Apify")

            # Get the dataset items
            dataset_id = run_data.get("data", {}).get("defaultDatasetId")
            if not dataset_id:
                raise ApifyAPIError("No dataset ID returned from Apify")

            items_url = f"{self.APIFY_API_BASE}/datasets/{dataset_id}/items"
            items_response = client.get(items_url, headers=headers)

            if items_response.status_code != 200:
                raise ApifyAPIError(f"Failed to get dataset: {items_response.status_code}")

            return items_response.json()

    def _parse_instagram_followers(self, results: list[dict[str, Any]]) -> list[ScrapedFollower]:
        """Parse Instagram follower data from Apify results."""
        followers = []

        for item in results:
            try:
                follower = ScrapedFollower(
                    platform_user_id=str(item.get("id", "")),
                    username=item.get("username", ""),
                    platform="instagram",
                    display_name=item.get("fullName"),
                    bio=item.get("biography"),
                    avatar_url=item.get("profilePicUrl"),
                    follower_count=item.get("followersCount", 0),
                    following_count=item.get("followsCount", 0),
                    post_count=item.get("postsCount", 0),
                    is_verified=item.get("verified", False),
                    is_private=item.get("private", False),
                )
                followers.append(follower)
            except (KeyError, TypeError) as e:
                logger.debug("Failed to parse Instagram follower: %s", e)
                continue

        logger.info("Parsed %s Instagram followers", len(followers))
        return followers

    def _parse_twitter_followers(self, results: list[dict[str, Any]]) -> list[ScrapedFollower]:
        """Parse Twitter/X follower data from Apify results."""
        followers = []

        for item in results:
            try:
                user_data = item.get("user", item)  # Handle nested structure

                follower = ScrapedFollower(
                    platform_user_id=str(user_data.get("id", user_data.get("id_str", ""))),
                    username=user_data.get("screen_name", user_data.get("username", "")),
                    platform="x",
                    display_name=user_data.get("name"),
                    bio=user_data.get("description"),
                    avatar_url=user_data.get("profile_image_url_https"),
                    follower_count=user_data.get("followers_count", 0),
                    following_count=user_data.get("friends_count", user_data.get("following_count", 0)),
                    post_count=user_data.get("statuses_count", user_data.get("tweet_count", 0)),
                    is_verified=user_data.get("verified", False),
                    is_private=user_data.get("protected", False),
                )
                followers.append(follower)
            except (KeyError, TypeError) as e:
                logger.debug("Failed to parse Twitter follower: %s", e)
                continue

        logger.info("Parsed %s Twitter followers", len(followers))
        return followers

    def scrape_profile(
        self,
        platform: str,
        username: str,
        timeout: int = 60,
    ) -> dict[str, Any] | None:
        """
        Scrape profile information for a single account.

        Args:
            platform: Target platform ("x" or "instagram")
            username: Target account username
            timeout: Timeout in seconds

        Returns:
            Profile data dictionary or None if not found
        """
        if not self.is_configured():
            logger.warning("Apify not configured")
            return None

        logger.info("Scraping profile for %s on %s", username, platform)

        try:
            if platform == "instagram":
                return self._scrape_instagram_profile(username, timeout)
            elif platform == "x":
                return self._scrape_twitter_profile(username, timeout)
            else:
                logger.warning("Unsupported platform: %s", platform)
                return None
        except Exception:
            logger.exception("Profile scrape failed for %s on %s", username, platform)
            return None

    def _scrape_instagram_profile(self, username: str, timeout: int) -> dict[str, Any] | None:
        """Scrape Instagram profile."""
        run_input = {
            "usernames": [username],
            "resultsType": "details",
        }

        results = self._run_apify_actor(self.INSTAGRAM_ACTOR, run_input, timeout)
        if results:
            return results[0]
        return None

    def _scrape_twitter_profile(self, username: str, timeout: int) -> dict[str, Any] | None:
        """Scrape Twitter/X profile."""
        run_input = {
            "handles": [username],
            "mode": "user",
        }

        results = self._run_apify_actor(self.TWITTER_ACTOR, run_input, timeout)
        if results:
            return results[0]
        return None


def create_social_scraper_service() -> SocialScraperService:
    """Factory function to create a social scraper service instance."""
    return SocialScraperService()


# =============================================================================
# Follower Scraping Task Integration
# =============================================================================


def scrape_kol_followers(
    tenant_id: str,
    target_kol_id: str,
    platform: str,
    username: str,
    max_followers: int = 1000,
) -> int:
    """
    Scrape followers for a target KOL and store them in the database.

    Args:
        tenant_id: The tenant ID
        target_kol_id: The target KOL ID
        platform: The platform ("x" or "instagram")
        username: The KOL's username
        max_followers: Maximum number of followers to scrape

    Returns:
        Number of followers created in the database
    """
    from services.leads import FollowerTargetService

    scraper = create_social_scraper_service()

    if not scraper.is_configured():
        logger.warning("Social scraper not configured, skipping follower scrape")
        return 0

    try:
        # Scrape followers
        followers = scraper.scrape_followers(
            platform=platform,
            username=username,
            max_followers=max_followers,
        )

        logger.info("Scraped %s followers for KOL %s on %s", len(followers), username, platform)

        if not followers:
            return 0

        # Convert to database format
        followers_data = [
            {
                "platform_user_id": f.platform_user_id,
                "username": f.username,
                "display_name": f.display_name,
                "bio": f.bio,
                "avatar_url": f.avatar_url,
                "follower_count": f.follower_count,
                "following_count": f.following_count,
                "post_count": f.post_count,
                "is_verified": f.is_verified,
                "is_private": f.is_private,
            }
            for f in followers
        ]

        # Store in database
        created_count = FollowerTargetService.create_targets_batch(
            tenant_id=tenant_id,
            target_kol_id=target_kol_id,
            platform=platform,
            targets_data=followers_data,
        )

        logger.info("Created %s follower targets in database", created_count)
        return created_count

    except SocialScraperError:
        logger.exception("Follower scrape failed for KOL %s", target_kol_id)
        return 0
