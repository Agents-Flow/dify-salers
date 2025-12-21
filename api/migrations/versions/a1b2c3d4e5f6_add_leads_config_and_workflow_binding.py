"""Add leads_configs and leads_workflow_bindings tables

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2024-12-21

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Create leads_configs table
    op.create_table(
        "leads_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("config_key", sa.String(length=100), nullable=False),
        sa.Column("config_value", sa.JSON(), nullable=False),
        sa.Column("is_encrypted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="leads_config_pkey"),
    )
    op.create_index("leads_config_tenant_idx", "leads_configs", ["tenant_id"])
    op.create_unique_constraint(
        "unique_leads_config_tenant_key", "leads_configs", ["tenant_id", "config_key"]
    )

    # Create leads_workflow_bindings table
    op.create_table(
        "leads_workflow_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("app_id", sa.String(length=36), nullable=False),
        sa.Column("app_mode", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="leads_workflow_binding_pkey"),
    )
    op.create_index("leads_workflow_binding_tenant_idx", "leads_workflow_bindings", ["tenant_id"])
    op.create_unique_constraint(
        "unique_leads_binding_tenant_action", "leads_workflow_bindings", ["tenant_id", "action_type"]
    )


def downgrade() -> None:
    # Drop leads_workflow_bindings table
    op.drop_constraint("unique_leads_binding_tenant_action", "leads_workflow_bindings", type_="unique")
    op.drop_index("leads_workflow_binding_tenant_idx", "leads_workflow_bindings")
    op.drop_table("leads_workflow_bindings")

    # Drop leads_configs table
    op.drop_constraint("unique_leads_config_tenant_key", "leads_configs", type_="unique")
    op.drop_index("leads_config_tenant_idx", "leads_configs")
    op.drop_table("leads_configs")
