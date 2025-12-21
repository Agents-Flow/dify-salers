"""
API endpoints for leads app templates.
Provides access to pre-built app templates for social outreach automation.
"""

from flask_restful import Resource

from controllers.console import api
from controllers.console.wraps import account_initialization_required, setup_required
from libs.login import login_required
from services.leads.app_templates import (
    TEMPLATES,
    get_template_content,
    get_templates_by_mode,
    get_templates_by_use_case,
    list_templates,
)


class AppTemplateListApi(Resource):
    """List all available app templates."""

    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """Get list of all available templates."""
        templates = list_templates()
        return {
            "templates": templates,
            "total": len(templates),
        }


class AppTemplateDetailApi(Resource):
    """Get a specific app template."""

    @setup_required
    @login_required
    @account_initialization_required
    def get(self, template_name: str):
        """Get template YAML content for import."""
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
            return {"error": f"Template not found: {template_name}"}, 404


class AppTemplatesByModeApi(Resource):
    """Get templates filtered by app mode."""

    @setup_required
    @login_required
    @account_initialization_required
    def get(self, mode: str):
        """Get templates by mode (workflow, agent-chat, completion, etc.)."""
        templates = get_templates_by_mode(mode)
        return {
            "mode": mode,
            "templates": templates,
            "total": len(templates),
        }


class AppTemplatesByUseCaseApi(Resource):
    """Get templates filtered by use case."""

    @setup_required
    @login_required
    @account_initialization_required
    def get(self, use_case: str):
        """Get templates by use case (获客, 对话, 自动化, etc.)."""
        templates = get_templates_by_use_case(use_case)
        return {
            "use_case": use_case,
            "templates": templates,
            "total": len(templates),
        }


# Register API routes
api.add_resource(AppTemplateListApi, "/leads/app-templates")
api.add_resource(AppTemplateDetailApi, "/leads/app-templates/<string:template_name>")
api.add_resource(AppTemplatesByModeApi, "/leads/app-templates/mode/<string:mode>")
api.add_resource(AppTemplatesByUseCaseApi, "/leads/app-templates/use-case/<string:use_case>")
