"""
Process conversation through AI flow tool.
"""

from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class ProcessConversationTool(BuiltinTool):
    """Tool for processing conversations through the AI flow."""

    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        """Process a message through the conversation flow."""
        from services.leads import (
            create_conversation_flow_service,
            create_spintax_service,
        )

        conv_id = tool_parameters.get("conversation_id", "")
        incoming_message = tool_parameters.get("incoming_message", "")
        follower_name = tool_parameters.get("follower_name", "there")
        kol_name = tool_parameters.get("kol_name", "our team")
        whatsapp_link = tool_parameters.get("whatsapp_link", "")

        if not conv_id or not incoming_message:
            yield self.create_text_message(
                "conversation_id and incoming_message are required"
            )
            return

        try:
            spintax = create_spintax_service()
            flow_service = create_conversation_flow_service(spintax_service=spintax)

            # Check if conversation exists, if not start it
            state = flow_service.get_state(conv_id)
            if not state:
                state = flow_service.start_conversation(
                    conversation_id=conv_id,
                    flow_id="standard_outreach",
                    variables={
                        "follower_name": follower_name,
                        "kol_name": kol_name,
                        "whatsapp_link": whatsapp_link,
                    },
                )

            # Process the incoming message
            response = flow_service.process_message(conv_id, incoming_message)

            result = {
                "should_respond": response.should_respond,
                "response_text": response.response_text,
                "detected_intent": response.detected_intent.value,
                "requires_human": response.requires_human,
                "end_conversation": response.end_conversation,
                "delay_seconds": response.delay_seconds,
                "current_node": state.current_node_id,
                "message_count": state.message_count,
            }

            yield self.create_json_message(result)

            if response.should_respond and response.response_text:
                yield self.create_text_message(response.response_text)
            elif response.requires_human:
                yield self.create_text_message(
                    "[ESCALATE TO HUMAN] This conversation needs human attention"
                )
            elif response.end_conversation:
                yield self.create_text_message("[CONVERSATION ENDED]")
            else:
                yield self.create_text_message("[NO RESPONSE NEEDED]")

        except Exception as e:
            yield self.create_text_message(f"Error processing conversation: {e}")
