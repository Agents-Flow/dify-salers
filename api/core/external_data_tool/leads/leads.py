"""
Leads external data tool.
Provides leads-specific data (KOL info, follower targets, conversations)
as variables for Dify apps.
"""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.external_data_tool.base import ExternalDataTool
from extensions.ext_database import db
from models.leads import (
    FollowerTarget,
    OutreachConversation,
    OutreachMessage,
    TargetKOL,
)

logger = logging.getLogger(__name__)


class LeadsExternalDataTool(ExternalDataTool):
    """
    External data tool that provides leads-related context to Dify apps.
    """

    name: str = "leads"

    @classmethod
    def validate_config(cls, tenant_id: str, config: dict) -> None:
        """
        Validate the incoming form config data.

        :param tenant_id: the id of workspace
        :param config: the form config data
        """
        data_type = config.get("data_type")
        if not data_type:
            raise ValueError("data_type is required")

        valid_types = ["kol_info", "follower_target", "conversation_context", "message_history"]
        if data_type not in valid_types:
            raise ValueError(f"data_type must be one of: {', '.join(valid_types)}")

    def query(self, inputs: dict[str, Any], query: str | None = None) -> str:
        """
        Query leads data based on configuration.

        :param inputs: user inputs (may contain target_id, conversation_id, etc.)
        :param query: the query of chat app
        :return: JSON string with leads data
        """
        if not self.config:
            return json.dumps({"error": "Configuration is required"})

        data_type = self.config.get("data_type", "")

        try:
            if data_type == "kol_info":
                return self._get_kol_info(inputs)
            elif data_type == "follower_target":
                return self._get_follower_target(inputs)
            elif data_type == "conversation_context":
                return self._get_conversation_context(inputs)
            elif data_type == "message_history":
                return self._get_message_history(inputs)
            else:
                return json.dumps({"error": f"Unknown data_type: {data_type}"})
        except Exception as e:
            logger.exception("Failed to query leads data")
            return json.dumps({"error": str(e)})

    def _get_kol_info(self, inputs: dict[str, Any]) -> str:
        """Get KOL information."""
        kol_id = inputs.get("kol_id") or self.config.get("kol_id")  # type: ignore
        if not kol_id:
            return json.dumps({"error": "kol_id is required"})

        with Session(db.engine) as session:
            stmt = select(TargetKOL).where(
                TargetKOL.tenant_id == self.tenant_id,
                TargetKOL.id == kol_id,
            )
            kol = session.scalar(stmt)

            if not kol:
                return json.dumps({"error": f"KOL not found: {kol_id}"})

            return json.dumps({
                "kol_id": kol.id,
                "username": kol.username,
                "platform": kol.platform,
                "display_name": kol.display_name,
                "bio": kol.bio,
                "follower_count": kol.follower_count,
                "niche": kol.niche,
                "region": kol.region,
                "language": kol.language,
            })

    def _get_follower_target(self, inputs: dict[str, Any]) -> str:
        """Get follower target information."""
        target_id = inputs.get("target_id") or self.config.get("target_id")  # type: ignore
        if not target_id:
            return json.dumps({"error": "target_id is required"})

        with Session(db.engine) as session:
            stmt = select(FollowerTarget).where(
                FollowerTarget.tenant_id == self.tenant_id,
                FollowerTarget.id == target_id,
            )
            target = session.scalar(stmt)

            if not target:
                return json.dumps({"error": f"Target not found: {target_id}"})

            return json.dumps({
                "target_id": target.id,
                "username": target.username,
                "platform": target.platform,
                "display_name": target.display_name,
                "bio": target.bio,
                "follower_count": target.follower_count,
                "following_count": target.following_count,
                "is_verified": target.is_verified,
                "quality_tier": target.quality_tier,
                "status": target.status,
                "tags": target.tags,
            })

    def _get_conversation_context(self, inputs: dict[str, Any]) -> str:
        """Get conversation context including recent messages."""
        conversation_id = inputs.get("conversation_id") or self.config.get("conversation_id")  # type: ignore
        if not conversation_id:
            return json.dumps({"error": "conversation_id is required"})

        with Session(db.engine) as session:
            conv_stmt = select(OutreachConversation).where(
                OutreachConversation.tenant_id == self.tenant_id,
                OutreachConversation.id == conversation_id,
            )
            conversation = session.scalar(conv_stmt)

            if not conversation:
                return json.dumps({"error": f"Conversation not found: {conversation_id}"})

            # Get the follower target info
            target_stmt = select(FollowerTarget).where(
                FollowerTarget.id == conversation.follower_target_id
            )
            target = session.scalar(target_stmt)

            # Get recent messages
            msg_stmt = (
                select(OutreachMessage)
                .where(OutreachMessage.conversation_id == conversation_id)
                .order_by(OutreachMessage.created_at.desc())
                .limit(10)
            )
            messages = list(session.scalars(msg_stmt).all())
            messages.reverse()

            return json.dumps({
                "conversation_id": conversation.id,
                "status": conversation.status,
                "ai_turns": conversation.ai_turns,
                "platform": conversation.platform,
                "target": {
                    "username": target.username if target else None,
                    "display_name": target.display_name if target else None,
                    "bio": target.bio if target else None,
                } if target else None,
                "messages": [
                    {
                        "direction": msg.direction,
                        "content": msg.content,
                        "sender_type": msg.sender_type,
                        "intent_detected": msg.ai_intent_detected,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    }
                    for msg in messages
                ],
            })

    def _get_message_history(self, inputs: dict[str, Any]) -> str:
        """Get message history for a conversation."""
        conversation_id = inputs.get("conversation_id") or self.config.get("conversation_id")  # type: ignore
        limit = inputs.get("limit", 20)

        if not conversation_id:
            return json.dumps({"error": "conversation_id is required"})

        with Session(db.engine) as session:
            msg_stmt = (
                select(OutreachMessage)
                .where(OutreachMessage.conversation_id == conversation_id)
                .order_by(OutreachMessage.created_at.desc())
                .limit(limit)
            )
            messages = list(session.scalars(msg_stmt).all())
            messages.reverse()

            return json.dumps({
                "conversation_id": conversation_id,
                "message_count": len(messages),
                "messages": [
                    {
                        "id": msg.id,
                        "direction": msg.direction,
                        "content": msg.content,
                        "sender_type": msg.sender_type,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    }
                    for msg in messages
                ],
            })
