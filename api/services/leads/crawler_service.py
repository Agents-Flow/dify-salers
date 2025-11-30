"""
Crawler service for lead acquisition.
Wraps MediaCrawler for Douyin comment crawling.

MediaCrawler: https://github.com/NanmiCoder/MediaCrawler
"""

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CrawledComment:
    """Standardized comment data structure."""

    platform_user_id: str
    nickname: str
    comment_content: str
    avatar_url: str | None = None
    region: str | None = None
    source_video_url: str | None = None
    source_video_title: str | None = None


class CrawlerServiceError(Exception):
    """Base exception for crawler service errors."""


class CrawlerNotConfiguredError(CrawlerServiceError):
    """MediaCrawler is not properly configured."""


class CrawlerExecutionError(CrawlerServiceError):
    """Error during crawler execution."""


class DouyinCrawlerService:
    """
    Service for crawling Douyin (TikTok China) comments.

    This service wraps MediaCrawler to provide a clean interface
    for crawling video comments.

    Usage:
        crawler = DouyinCrawlerService()
        comments = crawler.crawl_video_comments(
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

    def _validate_installation(self) -> None:
        """Check if MediaCrawler is properly installed."""
        crawler_path = Path(self.MEDIA_CRAWLER_PATH)
        if not crawler_path.exists():
            logger.warning(
                "MediaCrawler not found at %s. Please install it or set MEDIA_CRAWLER_PATH environment variable.",
                self.MEDIA_CRAWLER_PATH,
            )

    @staticmethod
    def extract_video_id(url: str) -> str | None:
        """
        Extract video ID from Douyin URL.

        Supports formats:
        - https://www.douyin.com/video/7123456789012345678
        - https://v.douyin.com/abc123/
        - https://www.douyin.com/jingxuan/search/xxx?modal_id=7123456789

        Args:
            url: Douyin video URL

        Returns:
            Video ID or None if not found
        """
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

        # Short URL - would need to resolve redirect
        short_pattern = r"v\.douyin\.com/([a-zA-Z0-9]+)"
        match = re.search(short_pattern, url)
        if match:
            return match.group(1)

        return None

    def _update_dy_config(self, video_urls: list[str]) -> str | None:
        """
        Temporarily update dy_config.py with the video URLs to crawl.

        Args:
            video_urls: List of video URLs/IDs to crawl

        Returns:
            Original config content for restoration, or None if failed
        """
        config_path = Path(self.MEDIA_CRAWLER_PATH) / "config" / "dy_config.py"
        if not config_path.exists():
            return None

        try:
            # Read original content
            original_content = config_path.read_text(encoding="utf-8")

            # Build the new DY_SPECIFIED_ID_LIST
            url_list_str = ",\n    ".join(f'"{url}"' for url in video_urls)
            new_list = f"DY_SPECIFIED_ID_LIST = [\n    {url_list_str},\n]"

            # Replace the DY_SPECIFIED_ID_LIST in the config
            import re

            pattern = r"DY_SPECIFIED_ID_LIST\s*=\s*\[[\s\S]*?\]"
            new_content = re.sub(pattern, new_list, original_content)

            # Write the updated config
            config_path.write_text(new_content, encoding="utf-8")
            logger.info("Updated dy_config.py with %s video URLs", len(video_urls))

            return original_content

        except OSError:
            logger.exception("Failed to update dy_config.py")
            return None

    def _restore_dy_config(self, original_content: str) -> None:
        """Restore dy_config.py to its original content."""
        config_path = Path(self.MEDIA_CRAWLER_PATH) / "config" / "dy_config.py"
        try:
            config_path.write_text(original_content, encoding="utf-8")
            logger.info("Restored dy_config.py to original content")
        except OSError:
            logger.exception("Failed to restore dy_config.py")

    def crawl_video_comments(
        self,
        video_url: str,
        max_comments: int = 500,
        timeout: int = 300,
    ) -> list[CrawledComment]:
        """
        Crawl comments from a Douyin video.

        Args:
            video_url: The Douyin video URL
            max_comments: Maximum number of comments to crawl
            timeout: Timeout in seconds for the crawl operation

        Returns:
            List of CrawledComment objects

        Raises:
            CrawlerNotConfiguredError: If MediaCrawler is not installed
            CrawlerExecutionError: If crawling fails
        """
        video_id = self.extract_video_id(video_url)
        if not video_id:
            raise CrawlerExecutionError(f"Could not extract video ID from URL: {video_url}")

        logger.info("Starting crawl for video: %s (max: %s comments)", video_id, max_comments)

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

            # Update dy_config.py with the video URL
            original_config = self._update_dy_config([video_url])
            if not original_config:
                logger.warning("Could not update dy_config.py, crawl may not work")

            # Build the command using the same Python as the current process
            # MediaCrawler uses --type detail and reads video IDs from DY_SPECIFIED_ID_LIST
            cmd = [
                sys.executable,
                str(crawler_path / "main.py"),
                "--platform",
                "dy",
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
            comments = self._parse_crawler_output(video_id, video_url, max_comments)
            logger.info("Crawled %s comments for video %s", len(comments), video_id)
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
                self._restore_dy_config(original_config)

    def _parse_crawler_output(
        self,
        video_id: str,
        video_url: str,
        max_comments: int,
    ) -> list[CrawledComment]:
        """Parse the JSON output from MediaCrawler."""
        output_path = Path(self.MEDIA_CRAWLER_PATH) / "data" / "douyin"

        # Find the latest output file
        json_files = list(output_path.glob("*.json"))
        if not json_files:
            logger.warning("No output files found in %s", output_path)
            return []

        # Sort by modification time, newest first
        json_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        comments: list[CrawledComment] = []

        for json_file in json_files[:5]:  # Check the 5 most recent files
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, list):
                    for item in data:
                        comment = self._parse_comment_item(item, video_url)
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
    ) -> CrawledComment | None:
        """Parse a single comment item from MediaCrawler output."""
        try:
            # MediaCrawler comment structure
            user_info = item.get("user", {})

            return CrawledComment(
                platform_user_id=str(user_info.get("uid", "")),
                nickname=user_info.get("nickname", ""),
                avatar_url=user_info.get("avatar", ""),
                comment_content=item.get("text", ""),
                region=item.get("ip_label", ""),
                source_video_url=video_url,
                source_video_title=item.get("aweme_title", ""),
            )
        except (KeyError, TypeError) as e:
            logger.debug("Failed to parse comment item: %s", e)
            return None

    def crawl_search_comments(
        self,
        keywords: list[str],
        city: str | None = None,
        max_videos: int = 10,
        max_comments_per_video: int = 50,
    ) -> list[CrawledComment]:
        """
        Search for videos by keywords and crawl their comments.

        Args:
            keywords: Search keywords
            city: Filter by city (optional)
            max_videos: Maximum number of videos to search
            max_comments_per_video: Maximum comments per video

        Returns:
            List of CrawledComment objects
        """
        logger.info("Starting keyword search crawl: keywords=%s, city=%s", keywords, city)

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
                "dy",
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
                    video_comments = self._parse_search_results(keyword, max_videos, max_comments_per_video)
                    all_comments.extend(video_comments)
            else:
                logger.warning("Search crawler failed: %s", result.stderr[:500] if result.stderr else "No error output")

        except (subprocess.TimeoutExpired, OSError):
            logger.exception("Keyword search failed for '%s'", keywords_str)

        return all_comments

    def _parse_search_results(
        self,
        keyword: str,
        max_videos: int,
        max_comments_per_video: int,
    ) -> list[CrawledComment]:
        """Parse search results from MediaCrawler."""
        # Search results are stored differently
        output_path = Path(self.MEDIA_CRAWLER_PATH) / "data" / "douyin"
        comments: list[CrawledComment] = []

        # Find and parse search result files
        search_files = list(output_path.glob(f"*{keyword}*.json"))
        for search_file in search_files[:max_videos]:
            try:
                with open(search_file, encoding="utf-8") as f:
                    data = json.load(f)
                for item in data[:max_comments_per_video]:
                    comment = self._parse_comment_item(item, "")
                    if comment:
                        comments.append(comment)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to parse %s: %s", search_file, e)

        return comments


def create_crawler_service() -> DouyinCrawlerService:
    """Factory function to create a crawler service instance."""
    return DouyinCrawlerService()
