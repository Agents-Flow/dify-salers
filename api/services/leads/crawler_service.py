"""
Crawler service for lead acquisition.
Wraps MediaCrawler for multi-platform comment crawling.

Supported platforms:
- Douyin (抖音)
- Xiaohongshu (小红书)
- Kuaishou (快手)
- Bilibili (B站)
- Weibo (微博)

MediaCrawler: https://github.com/NanmiCoder/MediaCrawler
"""

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CrawlerPlatform(StrEnum):
    """Supported crawler platforms matching MediaCrawler platform codes."""

    DOUYIN = "dy"
    XIAOHONGSHU = "xhs"
    KUAISHOU = "ks"
    BILIBILI = "bili"
    WEIBO = "wb"


# Platform configuration mappings
PLATFORM_CONFIG_MAP = {
    CrawlerPlatform.DOUYIN: {
        "config_file": "dy_config.py",
        "list_var": "DY_SPECIFIED_ID_LIST",
        "data_dir": "douyin",
    },
    CrawlerPlatform.XIAOHONGSHU: {
        "config_file": "xhs_config.py",
        "list_var": "XHS_SPECIFIED_NOTE_URL_LIST",
        "data_dir": "xhs",
    },
    CrawlerPlatform.KUAISHOU: {
        "config_file": "ks_config.py",
        "list_var": "KS_SPECIFIED_ID_LIST",
        "data_dir": "kuaishou",
    },
    CrawlerPlatform.BILIBILI: {
        "config_file": "bilibili_config.py",
        "list_var": "BILI_SPECIFIED_ID_LIST",
        "data_dir": "bilibili",
    },
    CrawlerPlatform.WEIBO: {
        "config_file": "weibo_config.py",
        "list_var": "WEIBO_SPECIFIED_ID_LIST",
        "data_dir": "weibo",
    },
}

# Map user-facing platform names to crawler platform codes
PLATFORM_NAME_MAP = {
    "douyin": CrawlerPlatform.DOUYIN,
    "xiaohongshu": CrawlerPlatform.XIAOHONGSHU,
    "kuaishou": CrawlerPlatform.KUAISHOU,
    "bilibili": CrawlerPlatform.BILIBILI,
    "weibo": CrawlerPlatform.WEIBO,
}


@dataclass
class CrawledComment:
    """Standardized comment data structure."""

    platform_user_id: str
    nickname: str
    comment_content: str
    platform: str = "douyin"  # Platform identifier
    avatar_url: str | None = None
    region: str | None = None
    source_video_url: str | None = None
    source_video_title: str | None = None
    # Platform-specific IDs for reply functionality
    platform_comment_id: str | None = None
    platform_video_id: str | None = None
    platform_user_sec_uid: str | None = None
    reply_url: str | None = None


class CrawlerServiceError(Exception):
    """Base exception for crawler service errors."""


class CrawlerNotConfiguredError(CrawlerServiceError):
    """MediaCrawler is not properly configured."""


class CrawlerExecutionError(CrawlerServiceError):
    """Error during crawler execution."""


class MultiPlatformCrawlerService:
    """
    Service for crawling comments from multiple social media platforms.

    Supported platforms:
    - Douyin (抖音): dy
    - Xiaohongshu (小红书): xhs
    - Kuaishou (快手): ks
    - Bilibili (B站): bili
    - Weibo (微博): wb

    Usage:
        crawler = MultiPlatformCrawlerService()
        comments = crawler.crawl_video_comments(
            platform="douyin",
            video_url="https://www.douyin.com/video/xxx",
            max_comments=100
        )
    """

    # Path to MediaCrawler installation (configurable via environment)
    # Default: <workspace>/MediaCrawler
    MEDIA_CRAWLER_PATH = os.getenv(
        "MEDIA_CRAWLER_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "MediaCrawler",
        ),
    )

    # Output directory for crawled data
    OUTPUT_DIR = os.getenv("MEDIA_CRAWLER_OUTPUT", "/tmp/media_crawler_output")

    def __init__(self):
        """Initialize the crawler service."""
        self._validate_installation()

    def _get_crawler_platform(self, platform: str) -> CrawlerPlatform:
        """Convert user-facing platform name to crawler platform code."""
        return PLATFORM_NAME_MAP.get(platform, CrawlerPlatform.DOUYIN)

    def _validate_installation(self) -> None:
        """Check if MediaCrawler is properly installed."""
        crawler_path = Path(self.MEDIA_CRAWLER_PATH)
        if not crawler_path.exists():
            logger.warning(
                "MediaCrawler not found at %s. Please install it or set MEDIA_CRAWLER_PATH environment variable.",
                self.MEDIA_CRAWLER_PATH,
            )

    @staticmethod
    def extract_video_id(url: str, platform: str = "douyin") -> str | None:
        """
        Extract video ID from URL for various platforms.

        Args:
            url: Video URL
            platform: Target platform

        Returns:
            Video ID or None if not found
        """
        if platform == "douyin":
            # Standard video URL pattern
            video_pattern = r"douyin\.com/video/(\d+)"
            match = re.search(video_pattern, url)
            if match:
                return match.group(1)

            # Modal ID pattern (from search pages)
            modal_pattern = r"modal_id=(\d+)"
            match = re.search(modal_pattern, url)
            if match:
                return match.group(1)

            # Short URL
            short_pattern = r"v\.douyin\.com/([a-zA-Z0-9]+)"
            match = re.search(short_pattern, url)
            if match:
                return match.group(1)

        elif platform == "xiaohongshu":
            # Xiaohongshu note URL
            xhs_pattern = r"xiaohongshu\.com/(?:explore|discovery/item)/([a-zA-Z0-9]+)"
            match = re.search(xhs_pattern, url)
            if match:
                return match.group(1)
            # Direct note ID
            if re.match(r"^[a-zA-Z0-9]{24}$", url):
                return url

        elif platform == "kuaishou":
            # Kuaishou video URL
            ks_pattern = r"kuaishou\.com/short-video/([a-zA-Z0-9]+)"
            match = re.search(ks_pattern, url)
            if match:
                return match.group(1)
            # Direct video ID
            if re.match(r"^[a-zA-Z0-9]+$", url):
                return url

        elif platform == "bilibili":
            # Bilibili video URL (BV format)
            bili_pattern = r"bilibili\.com/video/(BV[a-zA-Z0-9]+)"
            match = re.search(bili_pattern, url)
            if match:
                return match.group(1)
            # Direct BV ID
            if url.startswith("BV"):
                return url

        elif platform == "weibo":
            # Weibo post ID
            weibo_pattern = r"weibo\.com/\d+/([a-zA-Z0-9]+)"
            match = re.search(weibo_pattern, url)
            if match:
                return match.group(1)
            # Direct ID
            if re.match(r"^\d+$", url):
                return url

        # Fallback: return URL as-is if it looks like an ID
        if re.match(r"^[a-zA-Z0-9_-]+$", url):
            return url

        return None

    def _update_platform_config(self, platform: CrawlerPlatform, video_urls: list[str]) -> str | None:
        """
        Temporarily update platform config with the video URLs to crawl.

        Args:
            platform: Target platform
            video_urls: List of video URLs/IDs to crawl

        Returns:
            Original config content for restoration, or None if failed
        """
        platform_config = PLATFORM_CONFIG_MAP.get(platform)
        if not platform_config:
            logger.warning("Unknown platform: %s", platform)
            return None

        config_file = platform_config["config_file"]
        list_var = platform_config["list_var"]
        config_path = Path(self.MEDIA_CRAWLER_PATH) / "config" / config_file

        if not config_path.exists():
            logger.warning("Config file not found: %s", config_path)
            return None

        try:
            # Read original content
            original_content = config_path.read_text(encoding="utf-8")

            # Build the new ID list
            url_list_str = ",\n    ".join(f'"{url}"' for url in video_urls)
            new_list = f"{list_var} = [\n    {url_list_str},\n]"

            # Replace the list variable in the config
            pattern = rf"{list_var}\s*=\s*\[[\s\S]*?\]"
            new_content = re.sub(pattern, new_list, original_content)

            # Write the updated config
            config_path.write_text(new_content, encoding="utf-8")
            logger.info("Updated %s with %s URLs for platform %s", config_file, len(video_urls), platform)

            return original_content

        except OSError:
            logger.exception("Failed to update %s", config_file)
            return None

    def _restore_platform_config(self, platform: CrawlerPlatform, original_content: str) -> None:
        """Restore platform config to its original content."""
        platform_config = PLATFORM_CONFIG_MAP.get(platform)
        if not platform_config:
            return

        config_file = platform_config["config_file"]
        config_path = Path(self.MEDIA_CRAWLER_PATH) / "config" / config_file

        try:
            config_path.write_text(original_content, encoding="utf-8")
            logger.info("Restored %s to original content", config_file)
        except OSError:
            logger.exception("Failed to restore %s", config_file)

    def crawl_video_comments(
        self,
        video_url: str,
        platform: str = "douyin",
        max_comments: int = 500,
        timeout: int = 300,
    ) -> list[CrawledComment]:
        """
        Crawl comments from a video on any supported platform.

        Args:
            video_url: The video URL
            platform: Target platform (douyin, xiaohongshu, kuaishou, bilibili, weibo)
            max_comments: Maximum number of comments to crawl
            timeout: Timeout in seconds for the crawl operation

        Returns:
            List of CrawledComment objects

        Raises:
            CrawlerNotConfiguredError: If MediaCrawler is not installed
            CrawlerExecutionError: If crawling fails
        """
        crawler_platform = self._get_crawler_platform(platform)
        video_id = self.extract_video_id(video_url, platform)
        if not video_id:
            raise CrawlerExecutionError(f"Could not extract video ID from URL: {video_url}")

        logger.info("Starting crawl for %s video: %s (max: %s comments)", platform, video_id, max_comments)

        # Check if MediaCrawler is available
        crawler_path = Path(self.MEDIA_CRAWLER_PATH)
        if not crawler_path.exists():
            logger.warning("MediaCrawler not installed, returning empty results")
            return []

        original_config = None
        try:
            # Ensure output directory exists
            output_path = Path(self.OUTPUT_DIR)
            output_path.mkdir(parents=True, exist_ok=True)

            # Update platform config with the video URL
            original_config = self._update_platform_config(crawler_platform, [video_url])
            if not original_config:
                logger.warning("Could not update platform config, crawl may not work")

            # Build the command using the same Python as the current process
            cmd = [
                sys.executable,
                str(crawler_path / "main.py"),
                "--platform",
                crawler_platform.value,
                "--type",
                "detail",
                "--save_data_option",
                "json",
                "--get_comment",
                "true",
            ]

            logger.info("Executing crawler command: %s", " ".join(cmd))

            # Execute MediaCrawler
            result = subprocess.run(
                cmd,
                cwd=str(crawler_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "HEADLESS": "true"},
            )

            if result.returncode != 0:
                logger.error("Crawler failed: %s", result.stderr)
                raise CrawlerExecutionError(f"Crawler execution failed: {result.stderr}")

            # Parse results
            comments = self._parse_crawler_output(crawler_platform, video_id, video_url, max_comments)
            logger.info("Crawled %s comments for %s video %s", len(comments), platform, video_id)
            return comments

        except subprocess.TimeoutExpired:
            raise CrawlerExecutionError(f"Crawler timed out after {timeout} seconds")
        except FileNotFoundError:
            raise CrawlerNotConfiguredError(
                "Python or MediaCrawler not found. Please ensure MediaCrawler is properly installed."
            )
        finally:
            # Always restore the original config
            if original_config:
                self._restore_platform_config(crawler_platform, original_config)

    def _parse_crawler_output(
        self,
        platform: CrawlerPlatform,
        video_id: str,
        video_url: str,
        max_comments: int,
    ) -> list[CrawledComment]:
        """Parse the JSON output from MediaCrawler."""
        platform_config = PLATFORM_CONFIG_MAP.get(platform)
        data_dir = platform_config["data_dir"] if platform_config else "douyin"
        # MediaCrawler saves JSON files in data/{platform}/json/ subdirectory
        output_path = Path(self.MEDIA_CRAWLER_PATH) / "data" / data_dir / "json"

        # Find the latest comment files (detail_comments_*.json or search_comments_*.json)
        json_files = list(output_path.glob("*comments*.json"))
        if not json_files:
            # Fallback to parent directory if json subdir doesn't exist
            output_path = Path(self.MEDIA_CRAWLER_PATH) / "data" / data_dir
            json_files = list(output_path.glob("*.json"))

        if not json_files:
            logger.warning("No output files found in %s", output_path)
            return []

        # Sort by modification time, newest first
        json_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        logger.info("Found %s comment files, parsing newest ones", len(json_files))

        comments: list[CrawledComment] = []

        for json_file in json_files[:5]:  # Check the 5 most recent files
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                item_count = len(data) if isinstance(data, list) else 1
                logger.info("Parsing file: %s with %s items", json_file.name, item_count)

                if isinstance(data, list):
                    # Convert CrawlerPlatform enum to platform string
                    platform_str = platform.value if platform else "douyin"
                    for item in data:
                        comment = self._parse_comment_item(item, video_url, platform_str)
                        if comment:
                            comments.append(comment)
                            if len(comments) >= max_comments:
                                return comments
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to parse %s: %s", json_file, e)
                continue

        return comments

    def _parse_comment_item(
        self,
        item: dict[str, Any],
        video_url: str,
        platform: str = "douyin",
    ) -> CrawledComment | None:
        """Parse a single comment item from MediaCrawler output."""
        try:
            # MediaCrawler comment format varies by platform
            # For Douyin: user_id, nickname, content, ip_location, avatar are direct fields
            # For legacy format: user object with uid, nickname, avatar

            # Try new format first (direct fields)
            user_id = item.get("user_id") or item.get("user", {}).get("uid", "")
            nickname = item.get("nickname") or item.get("user", {}).get("nickname", "")
            avatar = item.get("avatar") or item.get("user", {}).get("avatar", "")
            content = item.get("content") or item.get("text", "")
            region = item.get("ip_location") or item.get("ip_label", "")

            # Extract platform-specific IDs for reply functionality
            comment_id = item.get("comment_id", "")
            video_id = item.get("aweme_id") or item.get("note_id", "")
            sec_uid = item.get("sec_uid", "")

            if not content:
                return None

            # Build reply URL and clean video URL based on platform
            reply_url = self._build_reply_url(platform, video_id, comment_id)
            clean_video_url = self._build_video_url(platform, video_id) or video_url

            return CrawledComment(
                platform_user_id=str(user_id),
                nickname=nickname,
                comment_content=content,
                platform=platform,  # Include platform in the comment data
                avatar_url=avatar,
                region=region,
                source_video_url=clean_video_url,
                source_video_title=item.get("aweme_title", ""),
                platform_comment_id=str(comment_id) if comment_id else None,
                platform_video_id=str(video_id) if video_id else None,
                platform_user_sec_uid=sec_uid or None,
                reply_url=reply_url,
            )
        except (KeyError, TypeError) as e:
            logger.debug("Failed to parse comment item: %s", e)
            return None

    def _build_video_url(self, platform: str, video_id: str) -> str | None:
        """Build a clean video URL based on platform and video ID."""
        if not video_id:
            return None

        platform_urls = {
            "douyin": f"https://www.douyin.com/video/{video_id}",
            "xiaohongshu": f"https://www.xiaohongshu.com/explore/{video_id}",
            "kuaishou": f"https://www.kuaishou.com/short-video/{video_id}",
            "bilibili": f"https://www.bilibili.com/video/{video_id}",
            "weibo": f"https://weibo.com/detail/{video_id}",
        }
        return platform_urls.get(platform)

    def _build_reply_url(self, platform: str, video_id: str, comment_id: str) -> str | None:
        """Build a URL for replying to a comment on the platform."""
        if not video_id or not comment_id:
            return None

        # Link to the video page - user can find and reply to the comment
        # Note: Most platforms don't support direct comment deep linking on web
        platform_urls = {
            "douyin": f"https://www.douyin.com/video/{video_id}",
            "xiaohongshu": f"https://www.xiaohongshu.com/explore/{video_id}",
            "kuaishou": f"https://www.kuaishou.com/short-video/{video_id}",
            "bilibili": f"https://www.bilibili.com/video/{video_id}",
            "weibo": f"https://weibo.com/detail/{video_id}",
        }
        return platform_urls.get(platform)

    def crawl_search_comments(
        self,
        keywords: list[str],
        platform: str = "douyin",
        city: str | None = None,
        max_videos: int = 10,
        max_comments_per_video: int = 50,
    ) -> list[CrawledComment]:
        """
        Search for videos by keywords and crawl their comments.

        Args:
            keywords: Search keywords
            platform: Target platform (douyin, xiaohongshu, kuaishou, bilibili, weibo)
            city: Filter by city (optional)
            max_videos: Maximum number of videos to search
            max_comments_per_video: Maximum comments per video

        Returns:
            List of CrawledComment objects
        """
        crawler_platform = self._get_crawler_platform(platform)
        logger.info("Starting keyword search crawl on %s: keywords=%s, city=%s", platform, keywords, city)

        crawler_path = Path(self.MEDIA_CRAWLER_PATH)
        if not crawler_path.exists():
            logger.warning("MediaCrawler not installed, returning empty results")
            return []

        all_comments: list[CrawledComment] = []

        # Join keywords with comma for MediaCrawler
        keywords_str = ",".join(keywords)

        try:
            cmd = [
                sys.executable,
                str(crawler_path / "main.py"),
                "--platform",
                crawler_platform.value,
                "--type",
                "search",
                "--keywords",
                keywords_str,
                "--save_data_option",
                "json",
                "--get_comment",
                "true",
            ]

            logger.info("Executing search crawler command: %s", " ".join(cmd))

            result = subprocess.run(
                cmd,
                cwd=str(crawler_path),
                capture_output=True,
                text=True,
                timeout=600,
                env={**os.environ, "HEADLESS": "true"},
            )

            if result.returncode == 0:
                # Parse search results
                for keyword in keywords:
                    video_comments = self._parse_search_results(
                        crawler_platform, keyword, max_videos, max_comments_per_video
                    )
                    all_comments.extend(video_comments)
            else:
                logger.warning("Search crawler failed: %s", result.stderr[:500] if result.stderr else "No error output")

        except (subprocess.TimeoutExpired, OSError):
            logger.exception("Keyword search failed for '%s'", keywords_str)

        return all_comments

    def _parse_search_results(
        self,
        platform: CrawlerPlatform,
        keyword: str,
        max_videos: int,
        max_comments_per_video: int,
    ) -> list[CrawledComment]:
        """Parse search results from MediaCrawler."""
        platform_config = PLATFORM_CONFIG_MAP.get(platform)
        data_dir = platform_config["data_dir"] if platform_config else "douyin"
        # MediaCrawler saves JSON files in data/{platform}/json/ subdirectory
        output_path = Path(self.MEDIA_CRAWLER_PATH) / "data" / data_dir / "json"
        comments: list[CrawledComment] = []

        # Find search comment files (search_comments_*.json)
        search_files = list(output_path.glob("search_comments*.json"))
        if not search_files:
            # Fallback to parent directory
            output_path = Path(self.MEDIA_CRAWLER_PATH) / "data" / data_dir
            search_files = list(output_path.glob(f"*{keyword}*.json"))

        # Sort by modification time, newest first
        search_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for search_file in search_files[:max_videos]:
            try:
                with open(search_file, encoding="utf-8") as f:
                    data = json.load(f)
                item_count = len(data) if isinstance(data, list) else 1
                logger.info("Parsing search file: %s with %s items", search_file.name, item_count)
                if isinstance(data, list):
                    # Convert CrawlerPlatform enum to platform string
                    platform_str = platform.value if platform else "douyin"
                    for item in data[:max_comments_per_video]:
                        comment = self._parse_comment_item(item, "", platform_str)
                        if comment:
                            comments.append(comment)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to parse %s: %s", search_file, e)

        return comments


def create_crawler_service() -> MultiPlatformCrawlerService:
    """Factory function to create a crawler service instance."""
    return MultiPlatformCrawlerService()


# Backward compatibility alias
DouyinCrawlerService = MultiPlatformCrawlerService
