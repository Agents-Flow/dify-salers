"""
Create outreach task tool.
"""

from collections.abc import Generator
from typing import Any

from core.tools.builtin_tool.tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


class CreateOutreachTaskTool(BuiltinTool):
    """Tool for creating outreach tasks."""

    def _invoke(
        self,
        user_id: str,
        tool_parameters: dict[str, Any],
        conversation_id: str | None = None,
        app_id: str | None = None,
        message_id: str | None = None,
    ) -> Generator[ToolInvokeMessage, None, None]:
        """Create an outreach task."""
        from services.leads import OutreachTaskService

        task_type = tool_parameters.get("task_type", "follow")
        target_kol_id = tool_parameters.get("target_kol_id", "")
        target_count = int(tool_parameters.get("target_count", 50))
        priority = tool_parameters.get("priority", "normal")

        if not target_kol_id:
            yield self.create_text_message("target_kol_id is required")
            return

        try:
            # Get tenant_id from runtime context
            tenant_id = self.runtime.tenant_id if self.runtime else ""

            if not tenant_id:
                yield self.create_text_message("Tenant context not available")
                return

            # Create task via service
            task = OutreachTaskService.create_task(
                tenant_id=tenant_id,
                target_kol_id=target_kol_id,
                task_type=task_type,
                target_count=min(target_count, 500),
                priority=priority,
            )

            result = {
                "task_id": task.id,
                "task_type": task_type,
                "target_kol_id": target_kol_id,
                "target_count": task.target_count,
                "status": task.status,
                "priority": priority,
                "message": f"Outreach task created successfully. Task ID: {task.id}",
            }

            yield self.create_json_message(result)
            yield self.create_text_message(
                f"Created {task_type} task for {target_count} targets. "
                f"Task ID: {task.id}"
            )

        except Exception as e:
            yield self.create_text_message(f"Error creating task: {e}")
