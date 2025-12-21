"""
Scrape KOL followers tool.
"""

import asyncio
from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class ScrapeFollowersTool(BuiltinTool):
    """Tool for scraping followers from KOL accounts."""

    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        """Scrape followers from a KOL account."""
        from services.leads import create_social_scraper_service

        platform = tool_parameters.get("platform", "instagram")
        username = tool_parameters.get("username", "")
        count = int(tool_parameters.get("count", 20))

        if not username:
            yield self.create_text_message("Username is required")
            return

        # Get API key from credentials
        credentials = self.runtime.credentials or {}
        apify_api_key = credentials.get("apify_api_key", "")

        try:
            scraper = create_social_scraper_service(api_key=apify_api_key)

            # Run async scraping
            async def scrape():
                return await scraper.scrape_kol_followers(
                    platform=platform,
                    kol_username=username,
                    limit=min(count, 100),
                )

            followers = asyncio.get_event_loop().run_until_complete(scrape())

            if not followers:
                yield self.create_text_message(
                    f"No followers found for @{username} on {platform}"
                )
                return

            # Format results
            result = {
                "platform": platform,
                "kol_username": username,
                "total_scraped": len(followers),
                "followers": [
                    {
                        "username": f.username,
                        "display_name": f.display_name,
                        "bio": f.bio[:100] if f.bio else None,
                        "followers_count": f.followers_count,
                        "is_verified": f.is_verified,
                    }
                    for f in followers[:20]  # Limit JSON output
                ],
            }

            yield self.create_json_message(result)
            yield self.create_text_message(
                f"Scraped {len(followers)} followers from @{username} on {platform}"
            )

        except Exception as e:
            yield self.create_text_message(f"Error scraping followers: {e}")
