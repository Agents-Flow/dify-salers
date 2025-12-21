"""
CLI command to import pre-built outreach app templates into Dify.
Usage: flask import-outreach-apps
"""

import logging

import click
from flask import Flask
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models import Account
from services.app_dsl_service import AppDslService
from services.leads.app_templates import TEMPLATES, get_template_content

logger = logging.getLogger(__name__)


def register_import_commands(app: Flask):
    """Register import commands with the Flask app."""

    @app.cli.command("import-outreach-apps", help="Import pre-built outreach app templates")
    @click.option("--tenant-id", required=True, help="Tenant ID to import apps into")
    @click.option("--user-id", required=True, help="User ID who will own the apps")
    @click.option("--template", default=None, help="Specific template to import (optional)")
    @click.option("--dry-run", is_flag=True, help="Show what would be imported")
    def import_outreach_apps(tenant_id: str, user_id: str, template: str | None, dry_run: bool):
        """Import pre-built outreach app templates."""
        click.echo(click.style("=== Import Outreach App Templates ===", fg="green", bold=True))

        account = db.session.query(Account).filter_by(id=user_id).first()
        if not account:
            click.echo(click.style(f"Error: User not found: {user_id}", fg="red"))
            return

        if template:
            if template not in TEMPLATES:
                click.echo(click.style(f"Error: Template not found: {template}", fg="red"))
                for name, info in TEMPLATES.items():
                    click.echo(f"  - {name}: {info['title']}")
                return
            templates_to_import = [(template, TEMPLATES[template])]
        else:
            templates_to_import = list(TEMPLATES.items())

        click.echo(f"Tenant ID: {tenant_id}")
        click.echo(f"User: {account.email}")
        click.echo(f"Templates: {len(templates_to_import)}")

        if dry_run:
            click.echo(click.style("DRY RUN", fg="yellow"))

        imported = 0
        for name, info in templates_to_import:
            click.echo(f"📦 {info['title']} ({info['mode']})")

            if dry_run:
                continue

            try:
                yaml_content = get_template_content(name)
                with Session(db.engine) as session:
                    svc = AppDslService(session)
                    result = svc.import_app(
                        account=account,
                        import_mode="yaml-content",
                        yaml_content=yaml_content,
                    )
                    if result.status == "pending":
                        result = svc.confirm_import(result.id, account)
                    session.commit()

                if result.status == "completed":
                    click.echo(click.style(f"   ✓ App ID: {result.app_id}", fg="green"))
                    imported += 1
                else:
                    click.echo(click.style(f"   ✗ {result.error}", fg="red"))
            except Exception as e:
                click.echo(click.style(f"   ✗ {e}", fg="red"))

        click.echo(f"\nImported: {imported}/{len(templates_to_import)}")

    @app.cli.command("list-outreach-templates", help="List outreach templates")
    def list_outreach_templates():
        """List all available outreach app templates."""
        click.echo(click.style("=== Outreach Templates ===", fg="green", bold=True))
        for name, info in TEMPLATES.items():
            click.echo(f"📦 {name}: {info['title']} ({info['mode']})")
