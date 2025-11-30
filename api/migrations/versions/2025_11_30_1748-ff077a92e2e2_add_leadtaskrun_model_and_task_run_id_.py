"""Add LeadTaskRun model and task_run_id to leads

Revision ID: ff077a92e2e2
Revises: 0b71d12af5e2
Create Date: 2025-11-30 17:48:55.114198

"""
from alembic import op
import models as models
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ff077a92e2e2'
down_revision = '0b71d12af5e2'
branch_labels = None
depends_on = None


def upgrade():
    """Add LeadTaskRun table and task_run_id column to leads."""
    # Create lead_task_runs table for tracking execution history
    op.create_table('lead_task_runs',
        sa.Column('id', models.types.StringUUID(), nullable=False),
        sa.Column('task_id', models.types.StringUUID(), nullable=False),
        sa.Column('run_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'running'"), nullable=False),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_crawled', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_created', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('config_snapshot', sa.JSON(), nullable=True),
        sa.Column('error_message', models.types.LongText(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='lead_task_run_pkey')
    )
    with op.batch_alter_table('lead_task_runs', schema=None) as batch_op:
        batch_op.create_index('lead_task_run_started_at_idx', ['started_at'], unique=False)
        batch_op.create_index('lead_task_run_task_idx', ['task_id'], unique=False)

    # Add task_run_id to leads table
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_run_id', models.types.StringUUID(), nullable=True))
        batch_op.create_index('lead_task_run_idx', ['task_run_id'], unique=False)


def downgrade():
    """Remove LeadTaskRun table and task_run_id column from leads."""
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.drop_index('lead_task_run_idx')
        batch_op.drop_column('task_run_id')

    with op.batch_alter_table('lead_task_runs', schema=None) as batch_op:
        batch_op.drop_index('lead_task_run_task_idx')
        batch_op.drop_index('lead_task_run_started_at_idx')

    op.drop_table('lead_task_runs')
