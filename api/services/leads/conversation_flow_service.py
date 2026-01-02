"""
AI conversation flow orchestration service.
Manages SOP-based conversation flows with intent detection and response generation.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class ConversationIntent(StrEnum):
    """Detected conversation intents."""
    GREETING = "greeting"
    INTEREST = "interest"
    QUESTION = "question"
    OBJECTION = "objection"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    REQUEST_HUMAN = "request_human"
    SPAM = "spam"
    UNKNOWN = "unknown"


class FlowNodeType(StrEnum):
    """Types of nodes in conversation flow."""
    START = "start"
    MESSAGE = "message"
    CONDITION = "condition"
    DELAY = "delay"
    HUMAN_HANDOFF = "human_handoff"
    END = "end"


@dataclass
class FlowNode:
    """A node in the conversation flow."""
    id: str
    node_type: FlowNodeType
    content: str | None = None  # Message content or condition expression
    template_id: str | None = None  # Spintax template ID
    delay_seconds: int = 0
    next_nodes: dict[str, str] = field(default_factory=dict)  # condition -> node_id
    default_next: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationFlow:
    """A complete conversation flow definition."""
    id: str
    name: str
    description: str
    nodes: dict[str, FlowNode] = field(default_factory=dict)
    start_node_id: str = "start"
    variables: dict[str, str] = field(default_factory=dict)
    platform: str = "all"
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "node_count": len(self.nodes),
            "platform": self.platform,
            "is_active": self.is_active,
        }


@dataclass
class ConversationState:
    """Current state of a conversation."""
    conversation_id: str
    flow_id: str
    current_node_id: str
    variables: dict[str, str] = field(default_factory=dict)
    message_count: int = 0
    failed_intents: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)


@dataclass
class FlowResponse:
    """Response from processing a message through the flow."""
    should_respond: bool
    response_text: str | None = None
    next_node_id: str | None = None
    detected_intent: ConversationIntent = ConversationIntent.UNKNOWN
    requires_human: bool = False
    end_conversation: bool = False
    delay_seconds: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ConversationFlowService:
    """
    Service for managing AI conversation flows.
    Supports keyword-based intent detection and SOP-driven responses.
    """

    # Intent detection patterns
    INTENT_PATTERNS = {
        ConversationIntent.GREETING: [
            r"\b(hi|hello|hey|hola|sup|what'?s up)\b",
            r"^(hi|hello|hey)\s*[!.?]*$",
        ],
        ConversationIntent.INTEREST: [
            r"\b(interested|tell me more|sounds good|sounds interesting)\b",
            r"\b(want to know|curious|learn more)\b",
            r"\b(yes please|sure|definitely|absolutely)\b",
        ],
        ConversationIntent.POSITIVE: [
            r"\b(yes|yeah|yep|yup|ok|okay|sure|great|cool|nice|awesome)\b",
            r"\b(thanks|thank you|appreciate)\b",
            r"👍|❤️|🙌|💯|✅",
        ],
        ConversationIntent.NEGATIVE: [
            r"\b(no|nope|not interested|no thanks|stop|leave me alone)\b",
            r"\b(unsubscribe|remove|block)\b",
        ],
        ConversationIntent.OBJECTION: [
            r"\b(why|how|what if|but|however|scam|fake|spam)\b",
            r"\b(is this legit|are you real|prove it)\b",
            r"\b(too good to be true|sounds fishy)\b",
        ],
        ConversationIntent.QUESTION: [
            r"\?$",
            r"\b(what|who|where|when|how|why|which)\b.*\?",
            r"\b(can you|could you|would you)\b",
        ],
        ConversationIntent.REQUEST_HUMAN: [
            r"\b(real person|human|agent|representative|manager)\b",
            r"\b(speak to someone|talk to|connect me)\b",
        ],
        ConversationIntent.SPAM: [
            r"\b(buy followers|make money fast|crypto giveaway)\b",
            r"bit\.ly|tinyurl\.com",
        ],
    }

    # Negative keywords that should trigger human intervention
    NEGATIVE_KEYWORDS = [
        "scam", "fraud", "report", "block", "lawsuit",
        "police", "complaint", "harassment", "stop messaging",
    ]

    def __init__(self, spintax_service=None):
        self.spintax_service = spintax_service
        self._flows: dict[str, ConversationFlow] = {}
        self._states: dict[str, ConversationState] = {}
        self._load_default_flows()

    def _load_default_flows(self) -> None:
        """Load default conversation flows."""
        # Standard outreach flow
        standard_flow = ConversationFlow(
            id="standard_outreach",
            name="Standard Outreach Flow",
            description="Basic flow for converting followers to WhatsApp",
        )

        # Define nodes
        nodes = [
            FlowNode(
                id="start",
                node_type=FlowNodeType.START,
                default_next="opening",
            ),
            FlowNode(
                id="opening",
                node_type=FlowNodeType.MESSAGE,
                template_id="opening_friendly",
                next_nodes={
                    "positive": "value_prop",
                    "interest": "value_prop",
                    "question": "answer_question",
                    "negative": "polite_end",
                    "request_human": "human_handoff",
                },
                default_next="follow_up_1",
            ),
            FlowNode(
                id="value_prop",
                node_type=FlowNodeType.MESSAGE,
                template_id="value_proposition",
                next_nodes={
                    "positive": "whatsapp_invite",
                    "interest": "whatsapp_invite",
                    "objection": "handle_objection",
                    "negative": "polite_end",
                },
                default_next="follow_up_2",
            ),
            FlowNode(
                id="handle_objection",
                node_type=FlowNodeType.MESSAGE,
                template_id="objection_why_whatsapp",
                next_nodes={
                    "positive": "whatsapp_invite",
                    "negative": "polite_end",
                },
                default_next="whatsapp_invite",
            ),
            FlowNode(
                id="answer_question",
                node_type=FlowNodeType.MESSAGE,
                content="That's a great question! [kol_name] shares insights on [niche] "
                "that you won't find anywhere else. Would you like to learn more?",
                next_nodes={
                    "positive": "value_prop",
                    "negative": "polite_end",
                },
                default_next="value_prop",
            ),
            FlowNode(
                id="whatsapp_invite",
                node_type=FlowNodeType.MESSAGE,
                template_id="whatsapp_invite",
                default_next="conversion_check",
            ),
            FlowNode(
                id="conversion_check",
                node_type=FlowNodeType.MESSAGE,
                content="Did you manage to join? Let me know if you have any issues! 😊",
                next_nodes={
                    "positive": "success_end",
                    "negative": "retry_invite",
                },
                default_next="end",
            ),
            FlowNode(
                id="follow_up_1",
                node_type=FlowNodeType.DELAY,
                delay_seconds=3600,  # 1 hour
                default_next="follow_up_message_1",
            ),
            FlowNode(
                id="follow_up_message_1",
                node_type=FlowNodeType.MESSAGE,
                template_id="follow_up_no_reply",
                default_next="end",
            ),
            FlowNode(
                id="follow_up_2",
                node_type=FlowNodeType.DELAY,
                delay_seconds=86400,  # 24 hours
                default_next="follow_up_message_2",
            ),
            FlowNode(
                id="follow_up_message_2",
                node_type=FlowNodeType.MESSAGE,
                content="Hey! Just wanted to check in one more time. The invite is still open if you're interested! 🙌",
                default_next="end",
            ),
            FlowNode(
                id="retry_invite",
                node_type=FlowNodeType.MESSAGE,
                content="No worries! Here's the link again: [whatsapp_link]. Feel free to join whenever you're ready!",
                default_next="end",
            ),
            FlowNode(
                id="human_handoff",
                node_type=FlowNodeType.HUMAN_HANDOFF,
                content="I'll connect you with someone who can help better. One moment!",
            ),
            FlowNode(
                id="polite_end",
                node_type=FlowNodeType.MESSAGE,
                content="No problem at all! Thanks for your time. Take care! 👋",
                default_next="end",
            ),
            FlowNode(
                id="success_end",
                node_type=FlowNodeType.MESSAGE,
                content="Awesome! Welcome aboard! 🎉 See you in the group!",
                default_next="end",
            ),
            FlowNode(
                id="end",
                node_type=FlowNodeType.END,
            ),
        ]

        for node in nodes:
            standard_flow.nodes[node.id] = node

        self._flows[standard_flow.id] = standard_flow

    def add_flow(self, flow: ConversationFlow) -> None:
        """Add a custom conversation flow."""
        self._flows[flow.id] = flow
        logger.info("Added conversation flow: %s", flow.id)

    def get_flow(self, flow_id: str) -> ConversationFlow | None:
        """Get a flow by ID."""
        return self._flows.get(flow_id)

    def list_flows(self, active_only: bool = True) -> list[ConversationFlow]:
        """List all conversation flows."""
        flows = list(self._flows.values())
        if active_only:
            flows = [f for f in flows if f.is_active]
        return flows

    def detect_intent(self, message: str) -> ConversationIntent:
        """Detect the intent of an incoming message."""
        message_lower = message.lower().strip()

        # Check for negative keywords first (highest priority)
        for keyword in self.NEGATIVE_KEYWORDS:
            if keyword in message_lower:
                return ConversationIntent.REQUEST_HUMAN

        # Check each intent pattern
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return intent

        return ConversationIntent.UNKNOWN

    def start_conversation(
        self,
        conversation_id: str,
        flow_id: str = "standard_outreach",
        variables: dict[str, str] | None = None,
    ) -> ConversationState:
        """Start a new conversation with a flow."""
        flow = self._flows.get(flow_id)
        if not flow:
            raise ValueError(f"Flow not found: {flow_id}")

        state = ConversationState(
            conversation_id=conversation_id,
            flow_id=flow_id,
            current_node_id=flow.start_node_id,
            variables=variables or {},
        )
        self._states[conversation_id] = state
        return state

    def get_state(self, conversation_id: str) -> ConversationState | None:
        """Get the current state of a conversation."""
        return self._states.get(conversation_id)

    def process_message(
        self,
        conversation_id: str,
        incoming_message: str,
    ) -> FlowResponse:
        """Process an incoming message and generate a response."""
        state = self._states.get(conversation_id)
        if not state:
            return FlowResponse(
                should_respond=False,
                requires_human=True,
                metadata={"error": "Conversation not found"},
            )

        flow = self._flows.get(state.flow_id)
        if not flow:
            return FlowResponse(
                should_respond=False,
                requires_human=True,
                metadata={"error": "Flow not found"},
            )

        current_node = flow.nodes.get(state.current_node_id)
        if not current_node:
            return FlowResponse(
                should_respond=False,
                end_conversation=True,
            )

        # Detect intent
        intent = self.detect_intent(incoming_message)
        state.message_count += 1
        state.last_activity = datetime.now()

        # Track failed intents (unknown responses)
        if intent == ConversationIntent.UNKNOWN:
            state.failed_intents += 1
            # If too many unknowns, hand off to human
            if state.failed_intents >= 3:
                return FlowResponse(
                    should_respond=True,
                    response_text=(
                        "I want to make sure I give you the best answer. "
                        "Let me connect you with someone who can help!"
                    ),
                    requires_human=True,
                    detected_intent=intent,
                )

        # Determine next node based on intent
        next_node_id = current_node.next_nodes.get(
            intent.value, current_node.default_next
        )

        if not next_node_id:
            return FlowResponse(
                should_respond=False,
                end_conversation=True,
                detected_intent=intent,
            )

        next_node = flow.nodes.get(next_node_id)
        if not next_node:
            return FlowResponse(
                should_respond=False,
                end_conversation=True,
            )

        # Generate response based on node type
        response = self._process_node(next_node, state)
        response.detected_intent = intent

        # Update state
        state.current_node_id = next_node_id

        return response

    def _process_node(
        self,
        node: FlowNode,
        state: ConversationState,
    ) -> FlowResponse:
        """Process a flow node and generate response."""
        if node.node_type == FlowNodeType.END:
            return FlowResponse(
                should_respond=False,
                end_conversation=True,
            )

        if node.node_type == FlowNodeType.HUMAN_HANDOFF:
            return FlowResponse(
                should_respond=True,
                response_text=self._replace_variables(node.content or "", state.variables),
                requires_human=True,
                next_node_id=node.id,
            )

        if node.node_type == FlowNodeType.DELAY:
            return FlowResponse(
                should_respond=False,
                delay_seconds=node.delay_seconds,
                next_node_id=node.default_next,
            )

        if node.node_type == FlowNodeType.MESSAGE:
            # Generate message content
            if node.template_id and self.spintax_service:
                generated = self.spintax_service.generate_message(
                    node.template_id, state.variables
                )
                response_text = generated.content if generated else ""
            elif node.content:
                response_text = self._replace_variables(node.content, state.variables)
            else:
                response_text = ""

            return FlowResponse(
                should_respond=True,
                response_text=response_text,
                next_node_id=node.id,
            )

        return FlowResponse(should_respond=False)

    def _replace_variables(self, text: str, variables: dict[str, str]) -> str:
        """Replace [variable] placeholders in text."""
        result = text
        for var_name, value in variables.items():
            result = result.replace(f"[{var_name}]", value)
        return result

    def get_initial_message(
        self,
        flow_id: str,
        variables: dict[str, str],
    ) -> str | None:
        """Get the initial outreach message for a flow."""
        flow = self._flows.get(flow_id)
        if not flow:
            return None

        # Navigate to first message node
        current_node = flow.nodes.get(flow.start_node_id)
        while current_node and current_node.node_type != FlowNodeType.MESSAGE:
            next_id = current_node.default_next
            if not next_id:
                break
            current_node = flow.nodes.get(next_id)

        if not current_node or current_node.node_type != FlowNodeType.MESSAGE:
            return None

        # Generate message
        if current_node.template_id and self.spintax_service:
            generated = self.spintax_service.generate_message(
                current_node.template_id, variables
            )
            return generated.content if generated else None
        elif current_node.content:
            return self._replace_variables(current_node.content, variables)

        return None


def create_conversation_flow_service(
    spintax_service=None,
) -> ConversationFlowService:
    """Factory function to create ConversationFlowService."""
    return ConversationFlowService(spintax_service=spintax_service)
