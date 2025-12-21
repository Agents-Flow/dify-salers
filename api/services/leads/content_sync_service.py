"""
Content synchronization service for KOL impersonation.
Syncs content from target KOLs to sub-accounts for trust building.
"""

import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ContentType(StrEnum):
    """Content types."""
    POST = "post"
    STORY = "story"
    REEL = "reel"
    TWEET = "tweet"
    THREAD = "thread"


class SyncStatus(StrEnum):
    """Content sync status."""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScrapedContent:
    """Scraped content from a KOL."""
    id: str
    platform: str
    kol_username: str
    content_type: ContentType
    text: str | None
    media_urls: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    posted_at: datetime | None = None
    scraped_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "platform": self.platform, "kol_username": self.kol_username,
            "content_type": self.content_type, "text": self.text,
            "media_urls": self.media_urls, "hashtags": self.hashtags,
            "likes_count": self.likes_count, "comments_count": self.comments_count,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
        }


@dataclass
class ContentSyncJob:
    """A content sync job."""
    id: str
    kol_id: str
    sub_account_id: str
    source_content: ScrapedContent
    modified_text: str | None = None
    scheduled_at: datetime | None = None
    status: SyncStatus = SyncStatus.PENDING
    synced_at: datetime | None = None
    error_message: str | None = None


class ContentSyncError(Exception):
    """Content sync error."""
    pass


class ContentSyncService:
    """
    Service for syncing KOL content to sub-accounts.
    Implements content spinning and scheduling for authentic account building.
    """

    # Spintax patterns for text variation
    GREETING_VARIANTS = [
        "{Hey|Hi|Hello|What's up}",
        "{everyone|folks|friends|people}",
        "{!|!!|...}",
    ]

    # Common word replacements for spinning
    WORD_REPLACEMENTS = {
        "amazing": ["incredible", "awesome", "fantastic", "great"],
        "important": ["crucial", "vital", "essential", "key"],
        "think": ["believe", "feel", "consider", "reckon"],
        "share": ["post", "put out", "drop"],
        "check out": ["take a look at", "have a look at", "see"],
    }

    def __init__(self, apify_api_token: str | None = None):
        self.apify_api_token = apify_api_token
        self._content_cache: dict[str, list[ScrapedContent]] = {}
        self._sync_jobs: list[ContentSyncJob] = []

    async def scrape_kol_posts(
        self,
        platform: str,
        username: str,
        count: int = 10,
    ) -> list[ScrapedContent]:
        """Scrape recent posts from a KOL account."""
        cache_key = f"{platform}:{username}"

        # Check cache first
        if cache_key in self._content_cache:
            cached = self._content_cache[cache_key]
            if cached and len(cached) >= count:
                return cached[:count]

        # Scrape using Apify
        if platform == "instagram":
            contents = await self._scrape_instagram_posts(username, count)
        elif platform == "x":
            contents = await self._scrape_x_posts(username, count)
        else:
            raise ContentSyncError(f"Unsupported platform: {platform}")

        self._content_cache[cache_key] = contents
        return contents

    async def _scrape_instagram_posts(
        self, username: str, count: int
    ) -> list[ScrapedContent]:
        """Scrape Instagram posts using Apify."""
        if not self.apify_api_token:
            logger.warning("Apify API token not configured, using mock data")
            return self._generate_mock_posts("instagram", username, count)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items",
                    headers={"Authorization": f"Bearer {self.apify_api_token}"},
                    json={
                        "directUrls": [f"https://www.instagram.com/{username}/"],
                        "resultsType": "posts",
                        "resultsLimit": count,
                    },
                )
                response.raise_for_status()
                data = response.json()

                return [
                    ScrapedContent(
                        id=item.get("id", f"ig_{i}"),
                        platform="instagram",
                        kol_username=username,
                        content_type=ContentType.POST,
                        text=item.get("caption", ""),
                        media_urls=[item.get("displayUrl")] if item.get("displayUrl") else [],
                        hashtags=item.get("hashtags", []),
                        likes_count=item.get("likesCount", 0),
                        comments_count=item.get("commentsCount", 0),
                        posted_at=datetime.fromisoformat(item["timestamp"]) if item.get("timestamp") else None,
                    )
                    for i, item in enumerate(data)
                ]
        except Exception as e:
            logger.exception("Failed to scrape Instagram posts")
            return []

    async def _scrape_x_posts(self, username: str, count: int) -> list[ScrapedContent]:
        """Scrape X/Twitter posts using Apify."""
        if not self.apify_api_token:
            logger.warning("Apify API token not configured, using mock data")
            return self._generate_mock_posts("x", username, count)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items",
                    headers={"Authorization": f"Bearer {self.apify_api_token}"},
                    json={
                        "handles": [username],
                        "tweetsDesired": count,
                        "proxyConfig": {"useApifyProxy": True},
                    },
                )
                response.raise_for_status()
                data = response.json()

                return [
                    ScrapedContent(
                        id=item.get("id", f"x_{i}"),
                        platform="x",
                        kol_username=username,
                        content_type=ContentType.TWEET,
                        text=item.get("full_text", ""),
                        media_urls=[m.get("url") for m in item.get("media", []) if m.get("url")],
                        hashtags=[h.get("text") for h in item.get("hashtags", [])],
                        likes_count=item.get("favorite_count", 0),
                        shares_count=item.get("retweet_count", 0),
                        posted_at=datetime.fromisoformat(item["created_at"]) if item.get("created_at") else None,
                    )
                    for i, item in enumerate(data)
                ]
        except Exception as e:
            logger.exception("Failed to scrape X posts")
            return []

    def _generate_mock_posts(
        self, platform: str, username: str, count: int
    ) -> list[ScrapedContent]:
        """Generate mock posts for testing."""
        content_type = ContentType.TWEET if platform == "x" else ContentType.POST
        return [
            ScrapedContent(
                id=f"mock_{platform}_{i}",
                platform=platform,
                kol_username=username,
                content_type=content_type,
                text=f"This is mock post #{i} from @{username}. Great insights on market trends!",
                hashtags=["crypto", "investing", "finance"],
                likes_count=random.randint(100, 10000),  # noqa: S311
                comments_count=random.randint(10, 500),  # noqa: S311
                posted_at=datetime.now() - timedelta(days=i),
            )
            for i in range(count)
        ]

    def spin_text(self, text: str, variation_level: float = 0.3) -> str:
        """
        Apply text spinning to create variations.
        variation_level: 0.0 (no change) to 1.0 (maximum variation)
        """
        if not text:
            return text

        result = text

        # Apply word replacements with probability based on variation level
        for word, replacements in self.WORD_REPLACEMENTS.items():
            if random.random() < variation_level:  # noqa: S311
                pattern = re.compile(rf"\b{word}\b", re.IGNORECASE)
                if pattern.search(result):
                    replacement = random.choice(replacements)  # noqa: S311
                    # Preserve case
                    if word[0].isupper():
                        replacement = replacement.capitalize()
                    result = pattern.sub(replacement, result, count=1)

        # Randomly add/remove punctuation
        if random.random() < variation_level * 0.5:  # noqa: S311
            if result.endswith("!"):
                result = result[:-1] + "."
            elif result.endswith(".") and random.random() < 0.5:  # noqa: S311
                result = result[:-1] + "!"

        return result

    def create_sync_jobs(
        self,
        kol_id: str,
        sub_account_ids: list[str],
        contents: list[ScrapedContent],
        start_delay_hours: int = 1,
        interval_hours: tuple[int, int] = (2, 6),
    ) -> list[ContentSyncJob]:
        """
        Create sync jobs to distribute content to sub-accounts.
        Schedules posts at random intervals for authenticity.
        """
        jobs = []
        current_time = datetime.now() + timedelta(hours=start_delay_hours)

        for sub_account_id in sub_account_ids:
            account_contents = contents.copy()
            random.shuffle(account_contents)

            for content in account_contents:
                # Create spun version of text
                modified_text = self.spin_text(content.text or "", variation_level=0.4)

                # Schedule at random interval
                scheduled_at = current_time + timedelta(
                    hours=random.randint(*interval_hours),  # noqa: S311
                    minutes=random.randint(0, 59),  # noqa: S311
                )

                job = ContentSyncJob(
                    id=f"sync_{sub_account_id}_{content.id}",
                    kol_id=kol_id,
                    sub_account_id=sub_account_id,
                    source_content=content,
                    modified_text=modified_text,
                    scheduled_at=scheduled_at,
                )
                jobs.append(job)
                self._sync_jobs.append(job)

                current_time = scheduled_at

        logger.info("Created %d content sync jobs for %d accounts", len(jobs), len(sub_account_ids))
        return jobs

    def get_pending_sync_jobs(
        self,
        sub_account_id: str | None = None,
        limit: int = 100,
    ) -> list[ContentSyncJob]:
        """Get pending sync jobs ready for execution."""
        now = datetime.now()
        jobs = [
            j for j in self._sync_jobs
            if j.status == SyncStatus.PENDING
            and j.scheduled_at
            and j.scheduled_at <= now
        ]
        if sub_account_id:
            jobs = [j for j in jobs if j.sub_account_id == sub_account_id]
        return sorted(jobs, key=lambda j: j.scheduled_at or now)[:limit]

    def mark_job_completed(self, job_id: str) -> bool:
        """Mark a sync job as completed."""
        for job in self._sync_jobs:
            if job.id == job_id:
                job.status = SyncStatus.SYNCED
                job.synced_at = datetime.now()
                return True
        return False

    def mark_job_failed(self, job_id: str, error: str) -> bool:
        """Mark a sync job as failed."""
        for job in self._sync_jobs:
            if job.id == job_id:
                job.status = SyncStatus.FAILED
                job.error_message = error
                return True
        return False

    async def sync_profile_info(
        self,
        platform: str,
        kol_username: str,
    ) -> dict[str, Any]:
        """Scrape KOL profile info for sub-account impersonation."""
        if not self.apify_api_token:
            return {
                "username": kol_username,
                "display_name": f"{kol_username.title()} Finance",
                "bio": "Financial analyst | Sharing insights on markets | Not financial advice",
                "avatar_url": None,
            }

        try:
            if platform == "instagram":
                endpoint = "apify~instagram-profile-scraper"
                payload = {"usernames": [kol_username]}
            else:  # x/twitter
                endpoint = "apidojo~twitter-user-scraper"
                payload = {"handles": [kol_username]}

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"https://api.apify.com/v2/acts/{endpoint}/run-sync-get-dataset-items",
                    headers={"Authorization": f"Bearer {self.apify_api_token}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                if data:
                    profile = data[0]
                    return {
                        "username": profile.get("username", kol_username),
                        "display_name": profile.get("fullName") or profile.get("name"),
                        "bio": profile.get("biography") or profile.get("description"),
                        "avatar_url": profile.get("profilePicUrlHD") or profile.get("profilePicUrl"),
                        "follower_count": profile.get("followersCount") or profile.get("followers_count"),
                        "following_count": profile.get("followingCount") or profile.get("following_count"),
                    }
        except Exception as e:
            logger.exception("Failed to scrape profile")

        return {"username": kol_username}

    def generate_bio_variation(self, original_bio: str, sub_account_name: str) -> str:
        """Generate a variation of a bio for a sub-account."""
        if not original_bio:
            return f"Sharing insights on markets | Fan of quality content | {sub_account_name}"

        # Simple variations
        bio = self.spin_text(original_bio, variation_level=0.5)

        # Add assistant suffix
        suffixes = [
            f" | Managed by {sub_account_name}",
            f" ✨ {sub_account_name}",
            f" | {sub_account_name}'s insights",
        ]
        if len(bio) + len(suffixes[0]) <= 150:  # Bio length limit
            bio += random.choice(suffixes)  # noqa: S311

        return bio[:150]  # Truncate to bio limit


def create_content_sync_service(apify_api_token: str | None = None) -> ContentSyncService:
    """Factory function to create ContentSyncService."""
    return ContentSyncService(apify_api_token=apify_api_token)
