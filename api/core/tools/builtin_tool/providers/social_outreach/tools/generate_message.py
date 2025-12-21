"""
Generate outreach message tool using Spintax templates.
"""

from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class GenerateMessageTool(BuiltinTool):
    """Tool for generating personalized outreach messages."""

    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        """Generate a personalized outreach message."""
        from services.leads import create_spintax_service

        category = tool_parameters.get("template_category", "opening")
        follower_name = tool_parameters.get("follower_name", "friend")
        kol_name = tool_parameters.get("kol_name", "our team")
        whatsapp_link = tool_parameters.get("whatsapp_link", "")

        variables = {
            "follower_name": follower_name,
            "kol_name": kol_name,
            "whatsapp_link": whatsapp_link,
            "assistant_name": "Assistant",
        }

        try:
            spintax_service = create_spintax_service()
            generated = spintax_service.generate_random_message(
                category=category,
                variables=variables,
            )

            if generated:
                yield self.create_json_message({
                    "message": generated.content,
                    "template_id": generated.template_id,
                    "category": category,
                })
                yield self.create_text_message(generated.content)
            else:
                yield self.create_text_message(
                    f"No template found for category: {category}"
                )

        except Exception as e:
            yield self.create_text_message(f"Error generating message: {e}")
