"""
Lead acquisition API controllers.
Provides REST endpoints for managing lead tasks and leads.
"""

from flask import request
from flask_restx import Resource, fields
from werkzeug.exceptions import NotFound

from controllers.console import console_ns
from controllers.console.wraps import (
    account_initialization_required,
    setup_required,
)
from libs.login import current_account_with_tenant, login_required
from services.leads_service import LeadService, LeadTaskService

# === API Models for Swagger Documentation ===

lead_task_config_model = console_ns.model(
    "LeadTaskConfig",
    {
        "video_urls": fields.List(fields.String, description="List of video URLs to crawl"),
        "keywords": fields.List(fields.String, description="Search keywords"),
        "city": fields.String(description="Target city"),
        "max_comments": fields.Integer(description="Maximum comments to crawl"),
    },
)

lead_task_model = console_ns.model(
    "LeadTask",
    {
        "id": fields.String(description="Task ID"),
        "name": fields.String(description="Task name"),
        "platform": fields.String(description="Platform (douyin)"),
        "task_type": fields.String(description="Task type"),
        "status": fields.String(description="Task status"),
        "config": fields.Nested(lead_task_config_model),
        "total_leads": fields.Integer(description="Total leads collected"),
        "created_at": fields.String(description="Creation timestamp"),
    },
)

lead_model = console_ns.model(
    "Lead",
    {
        "id": fields.String(description="Lead ID"),
        "nickname": fields.String(description="User nickname"),
        "platform_user_id": fields.String(description="Platform user ID"),
        "comment_content": fields.String(description="Comment content"),
        "source_video_title": fields.String(description="Source video title"),
        "intent_score": fields.Integer(description="Intent score (0-100)"),
        "intent_tags": fields.List(fields.String, description="Intent tags"),
        "status": fields.String(description="Lead status"),
        "created_at": fields.String(description="Creation timestamp"),
    },
)


# === Lead Task APIs ===


@console_ns.route("/lead-tasks")
class LeadTaskListApi(Resource):
    """Lead task list and creation endpoint."""

    @console_ns.doc("list_lead_tasks")
    @console_ns.doc(description="Get list of lead acquisition tasks")
    @console_ns.doc(
        params={
            "page": "Page number (default: 1)",
            "limit": "Items per page (default: 20)",
            "status": "Filter by status",
        }
    )
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get paginated list of lead tasks."""
        _, tenant_id = current_account_with_tenant()
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        status = request.args.get("status", type=str)

        result = LeadTaskService.get_tasks(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            status=status,
        )
        return result, 200

    @console_ns.doc("create_lead_task")
    @console_ns.doc(description="Create a new lead acquisition task")
    @console_ns.expect(
        console_ns.model(
            "CreateLeadTaskRequest",
            {
                "name": fields.String(required=True, description="Task name"),
                "task_type": fields.String(description="Task type (default: comment_crawl)"),
                "config": fields.Nested(lead_task_config_model, description="Task configuration"),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        """Create a new lead acquisition task."""
        account, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        if not data.get("name"):
            return {"error": "name is required"}, 400

        task = LeadTaskService.create_task(
            tenant_id=tenant_id,
            created_by=account.id,
            name=data["name"],
            task_type=data.get("task_type", "comment_crawl"),
            config=data.get("config", {}),
        )
        return task, 201


@console_ns.route("/lead-tasks/<uuid:task_id>")
class LeadTaskApi(Resource):
    """Single lead task endpoint."""

    @console_ns.doc("get_lead_task")
    @console_ns.doc(description="Get lead task details")
    @console_ns.doc(params={"task_id": "Task ID"})
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, task_id):
        """Get task details by ID."""
        _, tenant_id = current_account_with_tenant()
        task = LeadTaskService.get_task(tenant_id, str(task_id))

        if not task:
            raise NotFound("Task not found")
        return task, 200

    @console_ns.doc("delete_lead_task")
    @console_ns.doc(description="Delete a lead task")
    @console_ns.doc(params={"task_id": "Task ID"})
    @setup_required
    @login_required
    @account_initialization_required
    def delete(self, task_id):
        """Delete a task and its associated leads."""
        _, tenant_id = current_account_with_tenant()
        success = LeadTaskService.delete_task(tenant_id, str(task_id))

        if not success:
            raise NotFound("Task not found")
        return {"result": "success"}, 204


@console_ns.route("/lead-tasks/<uuid:task_id>/run")
class LeadTaskRunApi(Resource):
    """Lead task execution endpoint."""

    @console_ns.doc("run_lead_task")
    @console_ns.doc(description="Start execution of a lead task")
    @console_ns.doc(params={"task_id": "Task ID"})
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, task_id):
        """Start task execution."""
        _, tenant_id = current_account_with_tenant()
        success = LeadTaskService.run_task(tenant_id, str(task_id))

        if not success:
            return {"error": "Task not found or cannot be started"}, 400
        return {"result": "success", "message": "Task started"}, 200


# === Lead APIs ===


@console_ns.route("/leads")
class LeadListApi(Resource):
    """Lead list endpoint."""

    @console_ns.doc("list_leads")
    @console_ns.doc(description="Get list of leads (potential customers)")
    @console_ns.doc(
        params={
            "page": "Page number (default: 1)",
            "limit": "Items per page (default: 20)",
            "status": "Filter by status (new/contacted/converted/invalid)",
            "min_intent": "Minimum intent score filter",
            "task_id": "Filter by task ID",
            "keyword": "Search keyword",
        }
    )
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get paginated list of leads."""
        _, tenant_id = current_account_with_tenant()

        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        status = request.args.get("status", type=str)
        min_intent = request.args.get("min_intent", type=int)
        task_id = request.args.get("task_id", type=str)
        keyword = request.args.get("keyword", type=str)

        result = LeadService.get_leads(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            status=status,
            min_intent=min_intent,
            task_id=task_id,
            keyword=keyword,
        )
        return result, 200


@console_ns.route("/leads/stats")
class LeadStatsApi(Resource):
    """Lead statistics endpoint."""

    @console_ns.doc("get_lead_stats")
    @console_ns.doc(description="Get lead statistics for the tenant")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get lead statistics."""
        _, tenant_id = current_account_with_tenant()
        stats = LeadService.get_stats(tenant_id)
        return stats, 200


@console_ns.route("/leads/<uuid:lead_id>")
class LeadApi(Resource):
    """Single lead endpoint."""

    @console_ns.doc("get_lead")
    @console_ns.doc(description="Get lead details")
    @console_ns.doc(params={"lead_id": "Lead ID"})
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, lead_id):
        """Get lead details by ID."""
        _, tenant_id = current_account_with_tenant()
        lead = LeadService.get_lead(tenant_id, str(lead_id))

        if not lead:
            raise NotFound("Lead not found")
        return lead, 200

    @console_ns.doc("update_lead")
    @console_ns.doc(description="Update lead status or information")
    @console_ns.doc(params={"lead_id": "Lead ID"})
    @console_ns.expect(
        console_ns.model(
            "UpdateLeadRequest",
            {
                "status": fields.String(description="New status"),
                "intent_score": fields.Integer(description="Intent score"),
                "intent_tags": fields.List(fields.String, description="Intent tags"),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def patch(self, lead_id):
        """Update lead information."""
        _, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        lead = LeadService.update_lead(tenant_id, str(lead_id), **data)

        if not lead:
            raise NotFound("Lead not found")
        return lead, 200
