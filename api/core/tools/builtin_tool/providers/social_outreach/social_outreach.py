"""
Social Outreach tool provider for Dify.
Integrates leads management and outreach automation services.
"""

from core.tools.builtin_tool.provider import BuiltinToolProviderController


class SocialOutreachProvider(BuiltinToolProviderController):
    """
    Social Outreach tool provider.
    Provides tools for social media automation and lead generation.
    """

    def _validate_credentials(self, credentials: dict) -> None:
        """
        Validate provider credentials.
        Apify API key is optional - tools will work with limited functionality without it.
        """
        # Credentials are optional for this provider
        pass
