"""
Workflow result handler service.
Processes results from Dify workflow executions and updates leads data accordingly.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.leads import (
    FollowerTarget,
    FollowerTargetStatus,
    LeadsActionType,
    OutreachConversation,
    OutreachMessage,
)

logger = logging.getLogger(__name__)


class WorkflowResultHandler:
    """Handles workflow execution results and updates leads data."""

    @staticmethod
    def handle_result(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Process a workflow execution result.

        Args:
            payload: The result payload from the workflow execution
                - action_type: The action that was executed
                - result: The workflow output
                - target_id: Optional target entity ID
                - metadata: Additional context

        Returns:
            A dict with processing status
        """
        action_type = payload.get("action_type")
        result = payload.get("result", {})
        target_id = payload.get("target_id")
        metadata = payload.get("metadata", {})

        if not action_type:
            return {"success": False, "error": "action_type is required"}

        try:
            if action_type == LeadsActionType.SEND_FOLLOW:
                return WorkflowResultHandler._handle_follow_result(target_id, result, metadata)
            elif action_type == LeadsActionType.CHECK_FOLLOWBACK:
                return WorkflowResultHandler._handle_followback_result(target_id, result, metadata)
            elif action_type == LeadsActionType.SEND_DM:
                return WorkflowResultHandler._handle_dm_result(target_id, result, metadata)
            elif action_type == LeadsActionType.PROCESS_CONVERSATION:
                return WorkflowResultHandler._handle_conversation_result(target_id, result, metadata)
            elif action_type == LeadsActionType.GENERATE_MESSAGE:
                return WorkflowResultHandler._handle_message_result(target_id, result, metadata)
            elif action_type == LeadsActionType.SCRAPE_FOLLOWERS:
                return WorkflowResultHandler._handle_scrape_result(result, metadata)
            else:
                return {"success": False, "error": f"Unknown action type: {action_type}"}
        except Exception as e:
            logger.exception("Failed to handle result for %s", action_type)
            return {"success": False, "error": str(e)}

    @staticmethod
    def _handle_follow_result(
        target_id: str | None,
        result: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle follow action result."""
        if not target_id:
            return {"success": False, "error": "target_id is required for follow result"}

        success = result.get("success", False)

        with Session(db.engine) as session:
            stmt = select(FollowerTarget).where(FollowerTarget.id == target_id)
            target = session.scalar(stmt)

            if not target:
                return {"success": False, "error": f"Target not found: {target_id}"}

            if success:
                target.status = FollowerTargetStatus.FOLLOWED
                target.followed_at = datetime.utcnow()
                target.assigned_sub_account_id = metadata.get("sub_account_id")

                # Set follow-back timeout
                timeout_hours = metadata.get("timeout_hours", 72)
                from datetime import timedelta

                target.follow_timeout_at = datetime.utcnow() + timedelta(hours=timeout_hours)
            else:
                target.status = FollowerTargetStatus.FAILED

            session.commit()

        return {"success": True, "target_id": target_id, "status": target.status}

    @staticmethod
    def _handle_followback_result(
        target_id: str | None,
        result: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle follow-back check result."""
        if not target_id:
            return {"success": False, "error": "target_id is required"}

        followed_back = result.get("followed_back", False)

        with Session(db.engine) as session:
            stmt = select(FollowerTarget).where(FollowerTarget.id == target_id)
            target = session.scalar(stmt)

            if not target:
                return {"success": False, "error": f"Target not found: {target_id}"}

            if followed_back:
                target.status = FollowerTargetStatus.FOLLOW_BACK
                target.follow_back_at = datetime.utcnow()
            elif result.get("timeout_reached"):
                target.status = FollowerTargetStatus.UNFOLLOWED

            session.commit()

        return {"success": True, "target_id": target_id, "followed_back": followed_back}

    @staticmethod
    def _handle_dm_result(
        target_id: str | None,
        result: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle DM send result."""
        if not target_id:
            return {"success": False, "error": "target_id is required"}

        success = result.get("success", False)
        message_content = result.get("message_content", "")

        with Session(db.engine) as session:
            stmt = select(FollowerTarget).where(FollowerTarget.id == target_id)
            target = session.scalar(stmt)

            if not target:
                return {"success": False, "error": f"Target not found: {target_id}"}

            if success:
                target.status = FollowerTargetStatus.DM_SENT
                target.dm_sent_at = datetime.utcnow()

                # Create or update conversation
                conv_stmt = select(OutreachConversation).where(
                    OutreachConversation.follower_target_id == target_id
                )
                conversation = session.scalar(conv_stmt)

                sub_account_id = metadata.get("sub_account_id") or target.assigned_sub_account_id

                if not conversation and sub_account_id:
                    conversation = OutreachConversation(
                        tenant_id=target.tenant_id,
                        sub_account_id=sub_account_id,
                        follower_target_id=target_id,
                        platform=target.platform,
                    )
                    session.add(conversation)
                    session.flush()

                # Record the message
                if conversation and message_content:
                    message = OutreachMessage(
                        conversation_id=conversation.id,
                        direction="outbound",
                        content=message_content,
                        sender_type="ai",
                    )
                    session.add(message)
                    conversation.last_message_at = datetime.utcnow()
                    conversation.last_message_from = "us"
            else:
                target.status = FollowerTargetStatus.FAILED

            session.commit()

        return {"success": True, "target_id": target_id, "dm_sent": success}

    @staticmethod
    def _handle_conversation_result(
        target_id: str | None,
        result: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle conversation processing result."""
        conversation_id = metadata.get("conversation_id")
        if not conversation_id:
            return {"success": False, "error": "conversation_id is required"}

        response_message = result.get("response_message", "")
        needs_human = result.get("needs_human", False)
        intent_detected = result.get("intent_detected", "")

        with Session(db.engine) as session:
            stmt = select(OutreachConversation).where(OutreachConversation.id == conversation_id)
            conversation = session.scalar(stmt)

            if not conversation:
                return {"success": False, "error": f"Conversation not found: {conversation_id}"}

            if needs_human:
                conversation.status = "needs_human"
                conversation.human_takeover_reason = result.get("reason", "AI detected handoff needed")
            else:
                conversation.ai_turns += 1

            # Record outbound message
            if response_message:
                message = OutreachMessage(
                    conversation_id=conversation_id,
                    direction="outbound",
                    content=response_message,
                    sender_type="ai",
                    ai_intent_detected=intent_detected,
                )
                session.add(message)
                conversation.last_message_at = datetime.utcnow()
                conversation.last_message_from = "us"

            session.commit()

        return {
            "success": True,
            "conversation_id": conversation_id,
            "needs_human": needs_human,
        }

    @staticmethod
    def _handle_message_result(
        target_id: str | None,
        result: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle message generation result."""
        generated_message = result.get("message", "")
        template_used = result.get("template", "")

        return {
            "success": True,
            "message": generated_message,
            "template": template_used,
        }

    @staticmethod
    def _handle_scrape_result(
        result: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle scrape followers result."""
        scraped_count = result.get("scraped_count", 0)
        created_count = result.get("created_count", 0)
        kol_id = metadata.get("kol_id")

        return {
            "success": True,
            "kol_id": kol_id,
            "scraped_count": scraped_count,
            "created_count": created_count,
        }

    @staticmethod
    def record_incoming_message(
        conversation_id: str,
        content: str,
        platform_message_id: str | None = None,
    ) -> dict[str, Any]:
        """Record an incoming message from a follower."""
        with Session(db.engine) as session:
            stmt = select(OutreachConversation).where(OutreachConversation.id == conversation_id)
            conversation = session.scalar(stmt)

            if not conversation:
                return {"success": False, "error": f"Conversation not found: {conversation_id}"}

            message = OutreachMessage(
                conversation_id=conversation_id,
                direction="inbound",
                content=content,
                sender_type="follower",
                platform_message_id=platform_message_id,
            )
            session.add(message)

            conversation.last_message_at = datetime.utcnow()
            conversation.last_message_from = "them"

            # Update target status to conversing
            target_stmt = select(FollowerTarget).where(
                FollowerTarget.id == conversation.follower_target_id
            )
            target = session.scalar(target_stmt)
            if target and target.status == FollowerTargetStatus.DM_SENT:
                target.status = FollowerTargetStatus.CONVERSING

            session.commit()

        return {"success": True, "message_id": message.id}
