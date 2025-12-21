"""
Lead acquisition API controllers.
Provides REST endpoints for managing lead tasks, leads, and social outreach.
"""

from flask import request
from flask_restx import Resource, fields
from werkzeug.exceptions import BadRequest, NotFound

from controllers.console import console_ns
from controllers.console.wraps import (
    account_initialization_required,
    setup_required,
)
from libs.login import current_account_with_tenant, login_required
from services.leads import (
    FollowerTargetService,
    OutreachTaskService,
    SubAccountService,
    TargetKOLService,
)
from services.leads_service import LeadService, LeadTaskRunService, LeadTaskService

# === API Models for Swagger Documentation ===

lead_task_config_model = console_ns.model(
    "LeadTaskConfig",
    {
        "video_urls": fields.List(fields.String, description="List of video URLs to crawl"),
        "keywords": fields.List(fields.String, description="Search keywords"),
        "comment_keywords": fields.List(fields.String, description="Keywords to filter comments"),
        "city": fields.String(description="Target city"),
        "max_comments": fields.Integer(description="Maximum comments to crawl"),
    },
)

lead_task_model = console_ns.model(
    "LeadTask",
    {
        "id": fields.String(description="Task ID"),
        "name": fields.String(description="Task name"),
        "platform": fields.String(description="Platform (douyin, xiaohongshu, kuaishou, bilibili, weibo)"),
        "task_type": fields.String(description="Task type"),
        "status": fields.String(description="Task status"),
        "config": fields.Nested(lead_task_config_model),
        "total_leads": fields.Integer(description="Total leads collected"),
        "created_at": fields.String(description="Creation timestamp"),
    },
)

platform_model = console_ns.model(
    "Platform",
    {
        "value": fields.String(description="Platform value/key"),
        "label": fields.String(description="Platform display label"),
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
                "platform": fields.String(description="Platform (douyin, xiaohongshu, kuaishou, bilibili, weibo)"),
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
            platform=data.get("platform", "douyin"),
            config=data.get("config", {}),
        )
        return task, 201


@console_ns.route("/lead-platforms")
class LeadPlatformsApi(Resource):
    """Supported platforms endpoint."""

    @console_ns.doc("list_lead_platforms")
    @console_ns.doc(description="Get list of supported platforms for lead crawling")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get list of supported platforms."""
        platforms = LeadTaskService.get_supported_platforms()
        return {"data": platforms}, 200


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

    @console_ns.doc("update_lead_task")
    @console_ns.doc(description="Update a lead task")
    @console_ns.doc(params={"task_id": "Task ID"})
    @console_ns.expect(
        console_ns.model(
            "UpdateLeadTaskRequest",
            {
                "name": fields.String(description="Task name"),
                "platform": fields.String(description="Platform (douyin, xiaohongshu, kuaishou, bilibili, weibo)"),
                "config": fields.Nested(lead_task_config_model, description="Task configuration"),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def patch(self, task_id):
        """Update task name, platform and/or configuration."""
        _, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        task = LeadTaskService.update_task(
            tenant_id=tenant_id,
            task_id=str(task_id),
            name=data.get("name"),
            platform=data.get("platform"),
            config=data.get("config"),
        )

        if not task:
            return {"error": "Task not found or cannot be edited"}, 400
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


@console_ns.route("/lead-tasks/<uuid:task_id>/restart")
class LeadTaskRestartApi(Resource):
    """Lead task restart endpoint."""

    @console_ns.doc("restart_lead_task")
    @console_ns.doc(description="Restart a completed or failed task")
    @console_ns.doc(params={"task_id": "Task ID"})
    @console_ns.expect(
        console_ns.model(
            "RestartLeadTaskRequest",
            {
                "clear_leads": fields.Boolean(description="Clear existing leads before restart", default=False),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, task_id):
        """Restart a completed or failed task."""
        _, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}
        clear_leads = data.get("clear_leads", False)

        success = LeadTaskService.restart_task(tenant_id, str(task_id), clear_leads=clear_leads)

        if not success:
            return {"error": "Task not found or cannot be restarted"}, 400
        return {"result": "success", "message": "Task restarted"}, 200


@console_ns.route("/lead-tasks/<uuid:task_id>/leads")
class LeadTaskLeadsApi(Resource):
    """Get leads for a specific task."""

    @console_ns.doc("get_task_leads")
    @console_ns.doc(description="Get all leads collected by a task")
    @console_ns.doc(
        params={
            "task_id": "Task ID",
            "page": "Page number (default: 1)",
            "limit": "Items per page (default: 50)",
            "task_run_id": "Filter by specific task run ID",
        }
    )
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, task_id):
        """Get paginated list of leads for a task."""
        _, tenant_id = current_account_with_tenant()

        # Verify task exists and belongs to tenant
        task = LeadTaskService.get_task(tenant_id, str(task_id))
        if not task:
            raise NotFound("Task not found")

        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 50, type=int)
        task_run_id = request.args.get("task_run_id", type=str)

        result = LeadService.get_leads(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            task_id=str(task_id),
            task_run_id=task_run_id,
        )
        return result, 200


@console_ns.route("/lead-tasks/<uuid:task_id>/runs")
class LeadTaskRunsApi(Resource):
    """Get execution history for a task."""

    @console_ns.doc("get_task_runs")
    @console_ns.doc(description="Get execution history (runs) for a task")
    @console_ns.doc(
        params={
            "task_id": "Task ID",
            "limit": "Number of runs to return (default: 10)",
        }
    )
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, task_id):
        """Get task execution history."""
        _, tenant_id = current_account_with_tenant()

        # Verify task exists and belongs to tenant
        task = LeadTaskService.get_task(tenant_id, str(task_id))
        if not task:
            raise NotFound("Task not found")

        limit = request.args.get("limit", 10, type=int)
        runs = LeadTaskRunService.get_task_runs(str(task_id), limit)
        return {"data": runs}, 200


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
            "platform": "Filter by platform (douyin/xiaohongshu/kuaishou/bilibili/weibo)",
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
        platform = request.args.get("platform", type=str)

        result = LeadService.get_leads(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            status=status,
            min_intent=min_intent,
            task_id=task_id,
            keyword=keyword,
            platform=platform,
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


# =============================================================================
# Social Outreach APIs - Target KOL Management
# =============================================================================


@console_ns.route("/target-kols")
class TargetKOLListApi(Resource):
    """Target KOL list and creation endpoint."""

    @console_ns.doc("list_target_kols")
    @console_ns.doc(description="Get list of target KOL accounts")
    @console_ns.doc(
        params={
            "page": "Page number (default: 1)",
            "limit": "Items per page (default: 20)",
            "platform": "Filter by platform (x/instagram)",
            "status": "Filter by status (active/paused/archived)",
        }
    )
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get paginated list of target KOLs."""
        _, tenant_id = current_account_with_tenant()
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        platform = request.args.get("platform", type=str)
        status = request.args.get("status", type=str)

        result = TargetKOLService.get_kols(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            platform=platform,
            status=status,
        )
        return result, 200

    @console_ns.doc("create_target_kol")
    @console_ns.doc(description="Create a new target KOL account")
    @console_ns.expect(
        console_ns.model(
            "CreateTargetKOLRequest",
            {
                "platform": fields.String(required=True, description="Platform (x/instagram)"),
                "username": fields.String(required=True, description="KOL username"),
                "display_name": fields.String(description="Display name"),
                "profile_url": fields.String(description="Profile URL"),
                "bio": fields.String(description="Bio"),
                "follower_count": fields.Integer(description="Follower count"),
                "region": fields.String(description="Region"),
                "language": fields.String(description="Language code"),
                "niche": fields.String(description="Niche (stocks/crypto/finance)"),
                "timezone": fields.String(description="Timezone"),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        """Create a new target KOL."""
        account, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        if not data.get("platform") or not data.get("username"):
            raise BadRequest("platform and username are required")

        kol = TargetKOLService.create_kol(
            tenant_id=tenant_id,
            platform=data["platform"],
            username=data["username"],
            created_by=account.id,
            display_name=data.get("display_name"),
            profile_url=data.get("profile_url"),
            bio=data.get("bio"),
            follower_count=data.get("follower_count", 0),
            region=data.get("region"),
            language=data.get("language", "en"),
            niche=data.get("niche"),
            timezone=data.get("timezone"),
        )
        return kol, 201


@console_ns.route("/target-kols/<uuid:kol_id>")
class TargetKOLApi(Resource):
    """Single target KOL endpoint."""

    @console_ns.doc("get_target_kol")
    @console_ns.doc(description="Get target KOL details")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, kol_id):
        """Get KOL details by ID."""
        _, tenant_id = current_account_with_tenant()
        kol = TargetKOLService.get_kol(tenant_id, str(kol_id))

        if not kol:
            raise NotFound("Target KOL not found")
        return kol, 200

    @console_ns.doc("update_target_kol")
    @console_ns.doc(description="Update target KOL information")
    @setup_required
    @login_required
    @account_initialization_required
    def patch(self, kol_id):
        """Update KOL information."""
        _, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        kol = TargetKOLService.update_kol(tenant_id, str(kol_id), **data)

        if not kol:
            raise NotFound("Target KOL not found")
        return kol, 200

    @console_ns.doc("delete_target_kol")
    @console_ns.doc(description="Delete a target KOL and all associated data")
    @setup_required
    @login_required
    @account_initialization_required
    def delete(self, kol_id):
        """Delete a target KOL."""
        _, tenant_id = current_account_with_tenant()
        success = TargetKOLService.delete_kol(tenant_id, str(kol_id))

        if not success:
            raise NotFound("Target KOL not found")
        return {"result": "success"}, 204


@console_ns.route("/target-kols/<uuid:kol_id>/stats")
class TargetKOLStatsApi(Resource):
    """Target KOL statistics endpoint."""

    @console_ns.doc("get_target_kol_stats")
    @console_ns.doc(description="Get statistics for a target KOL")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, kol_id):
        """Get KOL statistics."""
        _, tenant_id = current_account_with_tenant()

        # Verify KOL exists
        kol = TargetKOLService.get_kol(tenant_id, str(kol_id))
        if not kol:
            raise NotFound("Target KOL not found")

        stats = TargetKOLService.get_kol_stats(tenant_id, str(kol_id))
        return stats, 200


# =============================================================================
# Social Outreach APIs - Sub-Account Management
# =============================================================================


@console_ns.route("/sub-accounts")
class SubAccountListApi(Resource):
    """Sub-account list and creation endpoint."""

    @console_ns.doc("list_sub_accounts")
    @console_ns.doc(description="Get list of sub-accounts")
    @console_ns.doc(
        params={
            "page": "Page number (default: 1)",
            "limit": "Items per page (default: 20)",
            "target_kol_id": "Filter by target KOL ID",
            "platform": "Filter by platform (x/instagram)",
            "status": "Filter by status (healthy/needs_verification/banned/cooling)",
        }
    )
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get paginated list of sub-accounts."""
        _, tenant_id = current_account_with_tenant()
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        target_kol_id = request.args.get("target_kol_id", type=str)
        platform = request.args.get("platform", type=str)
        status = request.args.get("status", type=str)

        result = SubAccountService.get_accounts(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            target_kol_id=target_kol_id,
            platform=platform,
            status=status,
        )
        return result, 200

    @console_ns.doc("create_sub_account")
    @console_ns.doc(description="Create a new sub-account")
    @console_ns.expect(
        console_ns.model(
            "CreateSubAccountRequest",
            {
                "platform": fields.String(required=True, description="Platform (x/instagram)"),
                "username": fields.String(required=True, description="Account username"),
                "email": fields.String(description="Account email"),
                "password": fields.String(description="Account password"),
                "target_kol_id": fields.String(description="Assigned target KOL ID"),
                "daily_limit_follows": fields.Integer(description="Daily follow limit"),
                "daily_limit_dms": fields.Integer(description="Daily DM limit"),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        """Create a new sub-account."""
        account, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        if not data.get("platform") or not data.get("username"):
            raise BadRequest("platform and username are required")

        sub_account = SubAccountService.create_account(
            tenant_id=tenant_id,
            platform=data["platform"],
            username=data["username"],
            created_by=account.id,
            email=data.get("email"),
            password_encrypted=data.get("password"),
            target_kol_id=data.get("target_kol_id"),
            daily_limit_follows=data.get("daily_limit_follows", 50),
            daily_limit_dms=data.get("daily_limit_dms", 30),
        )
        return sub_account, 201


@console_ns.route("/sub-accounts/import")
class SubAccountImportApi(Resource):
    """Sub-account CSV import endpoint."""

    @console_ns.doc("import_sub_accounts")
    @console_ns.doc(description="Import sub-accounts from CSV")
    @console_ns.expect(
        console_ns.model(
            "ImportSubAccountsRequest",
            {
                "platform": fields.String(required=True, description="Platform (x/instagram)"),
                "csv_content": fields.String(required=True, description="CSV content"),
                "target_kol_id": fields.String(description="Assign to target KOL"),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        """Import sub-accounts from CSV content."""
        account, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        if not data.get("platform") or not data.get("csv_content"):
            raise BadRequest("platform and csv_content are required")

        result = SubAccountService.import_accounts_csv(
            tenant_id=tenant_id,
            csv_content=data["csv_content"],
            platform=data["platform"],
            target_kol_id=data.get("target_kol_id"),
            created_by=account.id,
        )

        return {
            "total_rows": result.total_rows,
            "imported": result.imported,
            "skipped": result.skipped,
            "errors": result.errors[:10],  # Limit errors in response
        }, 200


@console_ns.route("/sub-accounts/<uuid:account_id>")
class SubAccountApi(Resource):
    """Single sub-account endpoint."""

    @console_ns.doc("get_sub_account")
    @console_ns.doc(description="Get sub-account details")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, account_id):
        """Get sub-account details by ID."""
        _, tenant_id = current_account_with_tenant()
        sub_account = SubAccountService.get_account(tenant_id, str(account_id))

        if not sub_account:
            raise NotFound("Sub-account not found")
        return sub_account, 200

    @console_ns.doc("delete_sub_account")
    @console_ns.doc(description="Delete a sub-account")
    @setup_required
    @login_required
    @account_initialization_required
    def delete(self, account_id):
        """Delete a sub-account."""
        _, tenant_id = current_account_with_tenant()
        success = SubAccountService.delete_account(tenant_id, str(account_id))

        if not success:
            raise NotFound("Sub-account not found")
        return {"result": "success"}, 204


@console_ns.route("/sub-accounts/<uuid:account_id>/health-check")
class SubAccountHealthCheckApi(Resource):
    """Sub-account health check endpoint."""

    @console_ns.doc("health_check_sub_account")
    @console_ns.doc(description="Perform health check on a sub-account")
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, account_id):
        """Perform health check on a sub-account."""
        _, tenant_id = current_account_with_tenant()

        # Verify account exists and belongs to tenant
        sub_account = SubAccountService.get_account(tenant_id, str(account_id))
        if not sub_account:
            raise NotFound("Sub-account not found")

        result = SubAccountService.health_check(str(account_id))
        return {
            "account_id": result.account_id,
            "previous_status": result.previous_status,
            "current_status": result.current_status,
            "message": result.message,
        }, 200


@console_ns.route("/sub-accounts/<uuid:account_id>/cooling")
class SubAccountCoolingApi(Resource):
    """Sub-account cooling endpoint."""

    @console_ns.doc("mark_sub_account_cooling")
    @console_ns.doc(description="Mark a sub-account as cooling (temporary rest)")
    @console_ns.expect(
        console_ns.model(
            "CoolingRequest",
            {
                "duration_hours": fields.Integer(description="Cooling duration in hours", default=24),
                "reason": fields.String(description="Reason for cooling"),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, account_id):
        """Mark sub-account as cooling."""
        _, tenant_id = current_account_with_tenant()

        # Verify account exists and belongs to tenant
        sub_account = SubAccountService.get_account(tenant_id, str(account_id))
        if not sub_account:
            raise NotFound("Sub-account not found")

        data = request.get_json() or {}
        SubAccountService.mark_cooling(
            account_id=str(account_id),
            duration_hours=data.get("duration_hours", 24),
            reason=data.get("reason"),
        )
        return {"result": "success", "message": "Account marked as cooling"}, 200


# =============================================================================
# Social Outreach APIs - Follower Target Management
# =============================================================================


@console_ns.route("/follower-targets")
class FollowerTargetListApi(Resource):
    """Follower target list endpoint."""

    @console_ns.doc("list_follower_targets")
    @console_ns.doc(description="Get list of follower targets")
    @console_ns.doc(
        params={
            "page": "Page number (default: 1)",
            "limit": "Items per page (default: 20)",
            "target_kol_id": "Filter by target KOL ID",
            "status": "Filter by status",
            "quality_tier": "Filter by quality tier (high/medium/low)",
        }
    )
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get paginated list of follower targets."""
        _, tenant_id = current_account_with_tenant()
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        target_kol_id = request.args.get("target_kol_id", type=str)
        status = request.args.get("status", type=str)
        quality_tier = request.args.get("quality_tier", type=str)

        result = FollowerTargetService.get_targets(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            target_kol_id=target_kol_id,
            status=status,
            quality_tier=quality_tier,
        )
        return result, 200


@console_ns.route("/follower-targets/funnel-stats")
class FollowerFunnelStatsApi(Resource):
    """Follower conversion funnel statistics endpoint."""

    @console_ns.doc("get_funnel_stats")
    @console_ns.doc(description="Get conversion funnel statistics")
    @console_ns.doc(
        params={
            "target_kol_id": "Filter by target KOL ID (optional)",
        }
    )
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get conversion funnel statistics."""
        _, tenant_id = current_account_with_tenant()
        target_kol_id = request.args.get("target_kol_id", type=str)

        stats = FollowerTargetService.get_funnel_stats(tenant_id, target_kol_id)
        return stats, 200


# =============================================================================
# Social Outreach APIs - Outreach Task Management
# =============================================================================


@console_ns.route("/outreach-tasks")
class OutreachTaskListApi(Resource):
    """Outreach task list and creation endpoint."""

    @console_ns.doc("list_outreach_tasks")
    @console_ns.doc(description="Get list of outreach tasks")
    @console_ns.doc(
        params={
            "page": "Page number (default: 1)",
            "limit": "Items per page (default: 20)",
            "target_kol_id": "Filter by target KOL ID",
            "status": "Filter by status",
        }
    )
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get paginated list of outreach tasks."""
        _, tenant_id = current_account_with_tenant()
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        target_kol_id = request.args.get("target_kol_id", type=str)
        status = request.args.get("status", type=str)

        result = OutreachTaskService.get_tasks(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            target_kol_id=target_kol_id,
            status=status,
        )
        return result, 200

    @console_ns.doc("create_outreach_task")
    @console_ns.doc(description="Create a new outreach task")
    @console_ns.expect(
        console_ns.model(
            "CreateOutreachTaskRequest",
            {
                "target_kol_id": fields.String(required=True, description="Target KOL ID"),
                "name": fields.String(required=True, description="Task name"),
                "task_type": fields.String(required=True, description="Task type (follow/dm/follow_dm)"),
                "platform": fields.String(required=True, description="Platform (x/instagram)"),
                "config": fields.Raw(description="Task configuration"),
                "message_templates": fields.List(fields.String, description="DM message templates"),
                "scheduled_at": fields.String(description="Scheduled execution time (ISO format)"),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        """Create a new outreach task."""
        account, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        required_fields = ["target_kol_id", "name", "task_type", "platform"]
        for field in required_fields:
            if not data.get(field):
                raise BadRequest(f"{field} is required")

        # Parse scheduled_at if provided
        scheduled_at = None
        if data.get("scheduled_at"):
            from datetime import datetime

            try:
                scheduled_at = datetime.fromisoformat(data["scheduled_at"])
            except ValueError:
                raise BadRequest("Invalid scheduled_at format. Use ISO format.")

        task = OutreachTaskService.create_task(
            tenant_id=tenant_id,
            target_kol_id=data["target_kol_id"],
            name=data["name"],
            task_type=data["task_type"],
            platform=data["platform"],
            config=data.get("config", {}),
            message_templates=data.get("message_templates"),
            scheduled_at=scheduled_at,
            created_by=account.id,
        )
        return task, 201


@console_ns.route("/outreach-tasks/<uuid:task_id>/start")
class OutreachTaskStartApi(Resource):
    """Outreach task start endpoint."""

    @console_ns.doc("start_outreach_task")
    @console_ns.doc(description="Start execution of an outreach task")
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, task_id):
        """Start task execution."""
        success = OutreachTaskService.start_task(str(task_id))

        if not success:
            return {"error": "Task not found or cannot be started"}, 400
        return {"result": "success", "message": "Task started"}, 200


# =============================================================================
# Social Outreach APIs - Follower Scraping
# =============================================================================


@console_ns.route("/target-kols/<uuid:kol_id>/scrape-followers")
class TargetKOLScrapeFollowersApi(Resource):
    """Scrape followers for a target KOL."""

    @console_ns.doc("scrape_kol_followers")
    @console_ns.doc(description="Scrape followers from a target KOL account")
    @console_ns.expect(
        console_ns.model(
            "ScrapeFollowersRequest",
            {
                "max_followers": fields.Integer(description="Maximum followers to scrape", default=1000),
            },
        )
    )
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, kol_id):
        """Scrape followers for a target KOL."""
        from services.leads import SocialScraperService, scrape_kol_followers

        _, tenant_id = current_account_with_tenant()

        # Verify KOL exists
        kol = TargetKOLService.get_kol(tenant_id, str(kol_id))
        if not kol:
            raise NotFound("Target KOL not found")

        # Check if scraper is configured
        if not SocialScraperService.is_configured():
            return {
                "error": "Follower scraping not configured",
                "message": "Set APIFY_API_TOKEN and APIFY_ENABLED=true to enable",
            }, 400

        data = request.get_json() or {}
        max_followers = data.get("max_followers", 1000)

        # Scrape followers (this will be async in production)
        created_count = scrape_kol_followers(
            tenant_id=tenant_id,
            target_kol_id=str(kol_id),
            platform=kol["platform"],
            username=kol["username"],
            max_followers=max_followers,
        )

        return {
            "result": "success",
            "created_count": created_count,
            "message": f"Scraped and created {created_count} follower targets",
        }, 200


@console_ns.route("/scraper/status")
class ScraperStatusApi(Resource):
    """Check scraper service status."""

    @console_ns.doc("get_scraper_status")
    @console_ns.doc(description="Check if the follower scraper service is configured and enabled")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get scraper status."""
        from services.leads import SocialScraperService

        is_configured = SocialScraperService.is_configured()
        return {
            "configured": is_configured,
            "enabled": SocialScraperService.APIFY_ENABLED,
            "has_token": bool(SocialScraperService.APIFY_API_TOKEN),
        }, 200


# =============================================================================
# App Templates APIs
# =============================================================================


@console_ns.route("/leads/app-templates")
class AppTemplateListApi(Resource):
    """List all available app templates."""

    @console_ns.doc("list_app_templates")
    @console_ns.doc(description="Get list of available outreach app templates")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get list of all available templates."""
        from services.leads.app_templates import list_templates

        templates = list_templates()
        return {
            "templates": templates,
            "total": len(templates),
        }


@console_ns.route("/leads/app-templates/<string:template_name>")
class AppTemplateDetailApi(Resource):
    """Get a specific app template."""

    @console_ns.doc("get_app_template")
    @console_ns.doc(description="Get template YAML content for import")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, template_name: str):
        """Get template YAML content for import."""
        from services.leads.app_templates import TEMPLATES, get_template_content

        try:
            content = get_template_content(template_name)
            info = TEMPLATES.get(template_name, {})
            return {
                "name": template_name,
                "title": info.get("title", template_name),
                "mode": info.get("mode", "unknown"),
                "description": info.get("description", ""),
                "use_case": info.get("use_case", ""),
                "yaml_content": content,
            }
        except FileNotFoundError:
            raise NotFound(f"Template not found: {template_name}")


# =============================================================================
# Configuration APIs
# =============================================================================


@console_ns.route("/leads/configs")
class LeadsConfigListApi(Resource):
    """List all leads configurations."""

    @console_ns.doc("list_leads_configs")
    @console_ns.doc(description="Get all configuration values for the tenant")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get all configuration values."""
        from services.leads import LeadsConfigService

        _, tenant_id = current_account_with_tenant()
        configs = LeadsConfigService.get_all_configs(tenant_id)
        schema = LeadsConfigService.get_config_schema()
        return {
            "configs": configs,
            "schema": schema,
        }


@console_ns.route("/leads/configs/<string:config_key>")
class LeadsConfigApi(Resource):
    """Get or update a specific configuration."""

    @console_ns.doc("get_leads_config")
    @console_ns.doc(description="Get a specific configuration value")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, config_key: str):
        """Get a specific configuration value."""
        from services.leads import LeadsConfigService

        _, tenant_id = current_account_with_tenant()
        config = LeadsConfigService.get_config(tenant_id, config_key)
        if config is None:
            return {"config_key": config_key, "config_value": None}
        return {"config_key": config_key, "config_value": config}

    @console_ns.doc("update_leads_config")
    @console_ns.doc(description="Update a configuration value")
    @setup_required
    @login_required
    @account_initialization_required
    def put(self, config_key: str):
        """Update a configuration value."""
        from services.leads import LeadsConfigService

        account, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        if "config_value" not in data:
            raise BadRequest("config_value is required")

        LeadsConfigService.set_config(
            tenant_id=tenant_id,
            config_key=config_key,
            config_value=data["config_value"],
            created_by=account.id,
        )
        return {"result": "success", "config_key": config_key}

    @console_ns.doc("delete_leads_config")
    @console_ns.doc(description="Delete a configuration value")
    @setup_required
    @login_required
    @account_initialization_required
    def delete(self, config_key: str):
        """Delete a configuration value."""
        from services.leads import LeadsConfigService

        _, tenant_id = current_account_with_tenant()
        success = LeadsConfigService.delete_config(tenant_id, config_key)
        if not success:
            raise NotFound(f"Config not found: {config_key}")
        return {"result": "success"}, 204


@console_ns.route("/leads/configs/test-connection")
class LeadsConfigTestConnectionApi(Resource):
    """Test API connections."""

    @console_ns.doc("test_leads_connection")
    @console_ns.doc(description="Test connection to configured services")
    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        """Test connection to Apify API."""
        from services.leads import LeadsConfigService

        _, tenant_id = current_account_with_tenant()
        result = LeadsConfigService.test_apify_connection(tenant_id)
        return result


# =============================================================================
# Workflow Binding APIs
# =============================================================================


@console_ns.route("/leads/workflow-bindings")
class WorkflowBindingListApi(Resource):
    """List and create workflow bindings."""

    @console_ns.doc("list_workflow_bindings")
    @console_ns.doc(description="Get all workflow bindings for the tenant")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get all workflow bindings."""
        from services.leads import WorkflowBindingService

        _, tenant_id = current_account_with_tenant()
        bindings = WorkflowBindingService.get_bindings(tenant_id)
        action_types = WorkflowBindingService.get_action_types()
        return {
            "bindings": bindings,
            "action_types": action_types,
        }

    @console_ns.doc("create_workflow_binding")
    @console_ns.doc(description="Create or update a workflow binding")
    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        """Create or update a workflow binding."""
        from services.leads import WorkflowBindingService

        account, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        required_fields = ["action_type", "app_id", "app_mode"]
        for field in required_fields:
            if not data.get(field):
                raise BadRequest(f"{field} is required")

        binding = WorkflowBindingService.bind_app(
            tenant_id=tenant_id,
            action_type=data["action_type"],
            app_id=data["app_id"],
            app_mode=data["app_mode"],
            config=data.get("config"),
            created_by=account.id,
        )
        return binding, 201


@console_ns.route("/leads/workflow-bindings/<string:action_type>")
class WorkflowBindingApi(Resource):
    """Get or delete a specific workflow binding."""

    @console_ns.doc("get_workflow_binding")
    @console_ns.doc(description="Get a specific workflow binding")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, action_type: str):
        """Get a specific workflow binding."""
        from services.leads import WorkflowBindingService

        _, tenant_id = current_account_with_tenant()
        binding = WorkflowBindingService.get_binding(tenant_id, action_type)
        if not binding:
            raise NotFound(f"Binding not found: {action_type}")
        return binding

    @console_ns.doc("delete_workflow_binding")
    @console_ns.doc(description="Delete a workflow binding")
    @setup_required
    @login_required
    @account_initialization_required
    def delete(self, action_type: str):
        """Delete a workflow binding."""
        from services.leads import WorkflowBindingService

        _, tenant_id = current_account_with_tenant()
        success = WorkflowBindingService.unbind_app(tenant_id, action_type)
        if not success:
            raise NotFound(f"Binding not found: {action_type}")
        return {"result": "success"}, 204


@console_ns.route("/leads/workflow-bindings/<string:action_type>/toggle")
class WorkflowBindingToggleApi(Resource):
    """Toggle workflow binding enabled status."""

    @console_ns.doc("toggle_workflow_binding")
    @console_ns.doc(description="Enable or disable a workflow binding")
    @setup_required
    @login_required
    @account_initialization_required
    def post(self, action_type: str):
        """Toggle binding enabled status."""
        from services.leads import WorkflowBindingService

        _, tenant_id = current_account_with_tenant()
        data = request.get_json() or {}

        is_enabled = data.get("is_enabled", True)
        success = WorkflowBindingService.toggle_binding(tenant_id, action_type, is_enabled)
        if not success:
            raise NotFound(f"Binding not found: {action_type}")
        return {"result": "success", "is_enabled": is_enabled}


@console_ns.route("/leads/available-apps")
class AvailableAppsApi(Resource):
    """List Dify apps available for binding."""

    @console_ns.doc("list_available_apps")
    @console_ns.doc(description="Get list of Dify apps available for workflow binding")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get available Dify apps."""
        from services.leads import WorkflowBindingService

        _, tenant_id = current_account_with_tenant()
        apps = WorkflowBindingService.get_available_apps(tenant_id)
        return {"apps": apps, "total": len(apps)}


# =============================================================================
# Webhook APIs
# =============================================================================


@console_ns.route("/leads/webhook/workflow-result")
class WorkflowResultWebhookApi(Resource):
    """Receive workflow execution results."""

    @console_ns.doc("receive_workflow_result")
    @console_ns.doc(description="Receive and process workflow execution results")
    def post(self):
        """Receive workflow result and update leads data."""
        from services.leads.workflow_result_handler import WorkflowResultHandler

        data = request.get_json() or {}

        if not data.get("action_type"):
            raise BadRequest("action_type is required")

        result = WorkflowResultHandler.handle_result(data)
        return result


@console_ns.route("/leads/webhook/incoming-message")
class IncomingMessageWebhookApi(Resource):
    """Receive incoming messages from followers."""

    @console_ns.doc("receive_incoming_message")
    @console_ns.doc(description="Record an incoming message from a follower")
    def post(self):
        """Record incoming message."""
        from services.leads.workflow_result_handler import WorkflowResultHandler

        data = request.get_json() or {}

        if not data.get("conversation_id") or not data.get("content"):
            raise BadRequest("conversation_id and content are required")

        result = WorkflowResultHandler.record_incoming_message(
            conversation_id=data["conversation_id"],
            content=data["content"],
            platform_message_id=data.get("platform_message_id"),
        )
        return result


# =============================================================================
# Analytics APIs
# =============================================================================


@console_ns.route("/leads/analytics/overview")
class AnalyticsOverviewApi(Resource):
    """Get dashboard overview analytics."""

    @console_ns.doc("get_analytics_overview")
    @console_ns.doc(description="Get dashboard overview statistics")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get dashboard overview."""
        from services.leads import LeadsAnalyticsService

        _, tenant_id = current_account_with_tenant()
        overview = LeadsAnalyticsService.get_dashboard_overview(tenant_id)
        return overview


@console_ns.route("/leads/analytics/funnel")
class AnalyticsFunnelApi(Resource):
    """Get conversion funnel analytics."""

    @console_ns.doc("get_analytics_funnel")
    @console_ns.doc(description="Get conversion funnel statistics")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get conversion funnel."""
        from services.leads import LeadsAnalyticsService

        _, tenant_id = current_account_with_tenant()
        target_kol_id = request.args.get("target_kol_id")

        funnel = LeadsAnalyticsService.get_conversion_funnel(
            tenant_id=tenant_id,
            target_kol_id=target_kol_id,
        )
        return funnel


@console_ns.route("/leads/analytics/kol-performance")
class AnalyticsKOLPerformanceApi(Resource):
    """Get KOL performance analytics."""

    @console_ns.doc("get_kol_performance")
    @console_ns.doc(description="Get performance metrics for each KOL")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get KOL performance."""
        from services.leads import LeadsAnalyticsService

        _, tenant_id = current_account_with_tenant()
        performance = LeadsAnalyticsService.get_kol_performance(tenant_id)
        return {"data": performance}


@console_ns.route("/leads/analytics/account-health")
class AnalyticsAccountHealthApi(Resource):
    """Get account health analytics."""

    @console_ns.doc("get_account_health")
    @console_ns.doc(description="Get account health statistics")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get account health trend."""
        from services.leads import LeadsAnalyticsService

        _, tenant_id = current_account_with_tenant()
        days = request.args.get("days", 7, type=int)
        health = LeadsAnalyticsService.get_account_health_trend(tenant_id, days)
        return {"data": health}


@console_ns.route("/leads/analytics/daily-stats")
class AnalyticsDailyStatsApi(Resource):
    """Get daily statistics."""

    @console_ns.doc("get_daily_stats")
    @console_ns.doc(description="Get daily statistics for the past N days")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get daily stats."""
        from services.leads import LeadsAnalyticsService

        _, tenant_id = current_account_with_tenant()
        days = request.args.get("days", 30, type=int)
        stats = LeadsAnalyticsService.get_daily_stats(tenant_id, days)
        return {"data": stats}


@console_ns.route("/leads/analytics/task-summary")
class AnalyticsTaskSummaryApi(Resource):
    """Get task execution summary."""

    @console_ns.doc("get_task_summary")
    @console_ns.doc(description="Get outreach task execution summary")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get task execution summary."""
        from services.leads import LeadsAnalyticsService

        _, tenant_id = current_account_with_tenant()
        summary = LeadsAnalyticsService.get_task_execution_summary(tenant_id)
        return summary


@console_ns.route("/leads/ai-status")
class AIStatusApi(Resource):
    """Get AI service status."""

    @console_ns.doc("get_ai_status")
    @console_ns.doc(description="Get AI service configuration status")
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get AI status."""
        from services.leads import LeadsAnalyticsService

        _, tenant_id = current_account_with_tenant()
        status = LeadsAnalyticsService.get_ai_status(tenant_id)
        return status
