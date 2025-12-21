"""
Analyze message intent tool for conversation flow.
"""

from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class AnalyzeIntentTool(BuiltinTool):
    """Tool for analyzing the intent of incoming messages."""

    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        """Analyze the intent of an incoming message."""
        from services.leads import create_conversation_flow_service

        message = tool_parameters.get("message", "")

        if not message:
            yield self.create_text_message("No message provided for analysis")
            return

        try:
            flow_service = create_conversation_flow_service()
            intent = flow_service.detect_intent(message)

            # Intent descriptions
            intent_descriptions = {
                "greeting": "User is saying hello or initiating conversation",
                "interest": "User shows interest in learning more",
                "positive": "User responds positively",
                "negative": "User is not interested or wants to stop",
                "objection": "User has concerns or objections",
                "question": "User is asking a question",
                "request_human": "User wants to speak with a real person",
                "spam": "Message appears to be spam",
                "unknown": "Intent could not be determined",
            }

            # Recommended actions
            recommended_actions = {
                "greeting": "respond_friendly",
                "interest": "send_value_proposition",
                "positive": "send_conversion_invite",
                "negative": "end_politely",
                "objection": "handle_objection",
                "question": "answer_question",
                "request_human": "escalate_to_human",
                "spam": "ignore",
                "unknown": "ask_clarification",
            }

            result = {
                "intent": intent.value,
                "description": intent_descriptions.get(intent.value, "Unknown"),
                "recommended_action": recommended_actions.get(intent.value, "review"),
                "requires_human": intent.value in ("request_human", "unknown"),
                "is_negative": intent.value in ("negative", "spam"),
            }

            yield self.create_json_message(result)
            yield self.create_text_message(
                f"Intent: {intent.value}\n"
                f"Action: {result['recommended_action']}\n"
                f"Requires Human: {result['requires_human']}"
            )

        except Exception as e:
            yield self.create_text_message(f"Error analyzing intent: {e}")
