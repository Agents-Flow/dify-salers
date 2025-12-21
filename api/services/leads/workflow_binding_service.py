"""
Workflow binding service.
Manages bindings between leads actions and Dify apps (Workflows, Agents, etc.).
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.leads import LeadsActionType, LeadsWorkflowBinding

logger = logging.getLogger(__name__)


class WorkflowBindingService:
    """Service for managing workflow bindings."""

    @staticmethod
    def get_bindings(tenant_id: str) -> list[dict[str, Any]]:
        """Get all workflow bindings for a tenant."""
        with Session(db.engine) as session:
            stmt = select(LeadsWorkflowBinding).where(
                LeadsWorkflowBinding.tenant_id == tenant_id
            )
            bindings = session.scalars(stmt).all()

            return [
                {
                    "id": b.id,
                    "action_type": b.action_type,
                    "app_id": b.app_id,
                    "app_mode": b.app_mode,
                    "is_enabled": b.is_enabled,
                    "config": b.config,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
                for b in bindings
            ]

    @staticmethod
    def get_binding(tenant_id: str, action_type: str) -> dict[str, Any] | None:
        """Get a specific binding by action type."""
        with Session(db.engine) as session:
            stmt = select(LeadsWorkflowBinding).where(
                LeadsWorkflowBinding.tenant_id == tenant_id,
                LeadsWorkflowBinding.action_type == action_type,
            )
            binding = session.scalar(stmt)

            if not binding:
                return None

            return {
                "id": binding.id,
                "action_type": binding.action_type,
                "app_id": binding.app_id,
                "app_mode": binding.app_mode,
                "is_enabled": binding.is_enabled,
                "config": binding.config,
                "created_at": binding.created_at.isoformat() if binding.created_at else None,
            }

    @staticmethod
    def bind_app(
        tenant_id: str,
        action_type: str,
        app_id: str,
        app_mode: str,
        config: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        """Bind a Dify app to an action type."""
        if action_type not in [at.value for at in LeadsActionType]:
            raise ValueError(f"Invalid action type: {action_type}")

        with Session(db.engine) as session:
            stmt = select(LeadsWorkflowBinding).where(
                LeadsWorkflowBinding.tenant_id == tenant_id,
                LeadsWorkflowBinding.action_type == action_type,
            )
            binding = session.scalar(stmt)

            if binding:
                binding.app_id = app_id
                binding.app_mode = app_mode
                binding.config = config or {}
                binding.is_enabled = True
            else:
                binding = LeadsWorkflowBinding(
                    tenant_id=tenant_id,
                    action_type=action_type,
                    app_id=app_id,
                    app_mode=app_mode,
                    config=config or {},
                    created_by=created_by,
                )
                session.add(binding)

            session.commit()
            session.refresh(binding)

            return {
                "id": binding.id,
                "action_type": binding.action_type,
                "app_id": binding.app_id,
                "app_mode": binding.app_mode,
                "is_enabled": binding.is_enabled,
                "config": binding.config,
            }

    @staticmethod
    def unbind_app(tenant_id: str, action_type: str) -> bool:
        """Remove a binding for an action type."""
        with Session(db.engine) as session:
            stmt = select(LeadsWorkflowBinding).where(
                LeadsWorkflowBinding.tenant_id == tenant_id,
                LeadsWorkflowBinding.action_type == action_type,
            )
            binding = session.scalar(stmt)

            if not binding:
                return False

            session.delete(binding)
            session.commit()
            return True

    @staticmethod
    def toggle_binding(tenant_id: str, action_type: str, is_enabled: bool) -> bool:
        """Enable or disable a binding."""
        with Session(db.engine) as session:
            stmt = select(LeadsWorkflowBinding).where(
                LeadsWorkflowBinding.tenant_id == tenant_id,
                LeadsWorkflowBinding.action_type == action_type,
            )
            binding = session.scalar(stmt)

            if not binding:
                return False

            binding.is_enabled = is_enabled
            session.commit()
            return True

    @staticmethod
    def execute_bound_workflow(
        tenant_id: str,
        action_type: str,
        inputs: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        """
        Execute the workflow bound to an action type.

        This method triggers the Dify app associated with the action,
        passing the leads-specific inputs.
        """
        binding = WorkflowBindingService.get_binding(tenant_id, action_type)

        if not binding:
            raise ValueError(f"No binding found for action: {action_type}")

        if not binding["is_enabled"]:
            raise ValueError(f"Binding for {action_type} is disabled")

        app_id = binding["app_id"]
        app_mode = binding["app_mode"]

        # Import here to avoid circular imports
        from services.app_generate_service import AppGenerateService

        # Prepare inputs based on action type
        merged_inputs = {**inputs, **binding.get("config", {})}

        try:
            if app_mode == "workflow":
                result = AppGenerateService.generate_workflow(
                    app_model_id=app_id,
                    user_id=user_id,
                    inputs=merged_inputs,
                )
            elif app_mode == "completion":
                result = AppGenerateService.generate_completion(
                    app_model_id=app_id,
                    user_id=user_id,
                    inputs=merged_inputs,
                )
            else:
                # For agent-chat and advanced-chat, we need conversation context
                result = AppGenerateService.generate_chat(
                    app_model_id=app_id,
                    user_id=user_id,
                    inputs=merged_inputs,
                    query=inputs.get("query", ""),
                )

            return {
                "success": True,
                "action_type": action_type,
                "app_id": app_id,
                "result": result,
            }
        except Exception as e:
            logger.exception("Failed to execute workflow for action %s", action_type)
            return {
                "success": False,
                "action_type": action_type,
                "app_id": app_id,
                "error": str(e),
            }

    @staticmethod
    def get_available_apps(tenant_id: str) -> list[dict[str, Any]]:
        """Get list of Dify apps available for binding."""
        from models.model import App

        with Session(db.engine) as session:
            stmt = select(App).where(
                App.tenant_id == tenant_id,
                App.is_deleted.is_(False),
            )
            apps = session.scalars(stmt).all()

            return [
                {
                    "id": app.id,
                    "name": app.name,
                    "mode": app.mode,
                    "icon": app.icon,
                    "icon_type": app.icon_type,
                    "icon_background": app.icon_background,
                }
                for app in apps
            ]

    @staticmethod
    def get_action_types() -> list[dict[str, str]]:
        """Get list of all action types with descriptions."""
        return [
            {
                "value": LeadsActionType.SCRAPE_FOLLOWERS,
                "label": "Scrape Followers",
                "description": "Scrape followers from target KOL accounts",
            },
            {
                "value": LeadsActionType.SEND_FOLLOW,
                "label": "Send Follow",
                "description": "Send follow requests to follower targets",
            },
            {
                "value": LeadsActionType.CHECK_FOLLOWBACK,
                "label": "Check Follow-back",
                "description": "Check if targets have followed back",
            },
            {
                "value": LeadsActionType.SEND_DM,
                "label": "Send DM",
                "description": "Send direct messages to targets",
            },
            {
                "value": LeadsActionType.PROCESS_CONVERSATION,
                "label": "Process Conversation",
                "description": "Process incoming DM with AI",
            },
            {
                "value": LeadsActionType.GENERATE_MESSAGE,
                "label": "Generate Message",
                "description": "Generate personalized message content",
            },
        ]
