"""introduce_leads

Revision ID: a1b2c3d4e5f6
Revises: 7bb281b7a422
Create Date: 2025-11-30 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
import models as models


def _is_pg(conn):
    return conn.dialect.name == "postgresql"


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '7bb281b7a422'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    
    # Create lead_tasks table
    if _is_pg(conn):
        op.create_table(
            'lead_tasks',
            sa.Column('id', models.types.StringUUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
            sa.Column('tenant_id', models.types.StringUUID(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('platform', sa.String(length=50), server_default=sa.text("'douyin'"), nullable=False),
            sa.Column('task_type', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=50), server_default=sa.text("'pending'"), nullable=False),
            sa.Column('config', sa.JSON(), nullable=False),
            sa.Column('result_summary', sa.JSON(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('total_leads', sa.Integer(), server_default=sa.text('0'), nullable=False),
            sa.Column('created_by', models.types.StringUUID(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id', name='lead_task_pkey')
        )
    else:
        op.create_table(
            'lead_tasks',
            sa.Column('id', models.types.StringUUID(), nullable=False),
            sa.Column('tenant_id', models.types.StringUUID(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('platform', sa.String(length=50), server_default=sa.text("'douyin'"), nullable=False),
            sa.Column('task_type', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=50), server_default=sa.text("'pending'"), nullable=False),
            sa.Column('config', sa.JSON(), nullable=False),
            sa.Column('result_summary', sa.JSON(), nullable=True),
            sa.Column('error_message', models.types.LongText(), nullable=True),
            sa.Column('total_leads', sa.Integer(), server_default=sa.text('0'), nullable=False),
            sa.Column('created_by', models.types.StringUUID(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
            sa.PrimaryKeyConstraint('id', name='lead_task_pkey')
        )
    
    with op.batch_alter_table('lead_tasks', schema=None) as batch_op:
        batch_op.create_index('lead_task_tenant_idx', ['tenant_id'], unique=False)
        batch_op.create_index('lead_task_status_idx', ['status'], unique=False)
        batch_op.create_index('lead_task_created_at_idx', ['created_at'], unique=False)

    # Create leads table
    if _is_pg(conn):
        op.create_table(
            'leads',
            sa.Column('id', models.types.StringUUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
            sa.Column('tenant_id', models.types.StringUUID(), nullable=False),
            sa.Column('task_id', models.types.StringUUID(), nullable=True),
            sa.Column('platform', sa.String(length=50), server_default=sa.text("'douyin'"), nullable=False),
            sa.Column('platform_user_id', sa.String(length=255), nullable=True),
            sa.Column('nickname', sa.String(length=255), nullable=True),
            sa.Column('avatar_url', sa.Text(), nullable=True),
            sa.Column('region', sa.String(length=255), nullable=True),
            sa.Column('comment_content', sa.Text(), nullable=True),
            sa.Column('source_video_url', sa.Text(), nullable=True),
            sa.Column('source_video_title', sa.Text(), nullable=True),
            sa.Column('intent_score', sa.Integer(), server_default=sa.text('0'), nullable=False),
            sa.Column('intent_tags', sa.JSON(), nullable=True),
            sa.Column('intent_reason', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=50), server_default=sa.text("'new'"), nullable=False),
            sa.Column('contacted_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id', name='lead_pkey'),
            sa.UniqueConstraint('tenant_id', 'platform', 'platform_user_id', name='unique_lead_platform_user')
        )
    else:
        op.create_table(
            'leads',
            sa.Column('id', models.types.StringUUID(), nullable=False),
            sa.Column('tenant_id', models.types.StringUUID(), nullable=False),
            sa.Column('task_id', models.types.StringUUID(), nullable=True),
            sa.Column('platform', sa.String(length=50), server_default=sa.text("'douyin'"), nullable=False),
            sa.Column('platform_user_id', sa.String(length=255), nullable=True),
            sa.Column('nickname', sa.String(length=255), nullable=True),
            sa.Column('avatar_url', sa.Text(), nullable=True),
            sa.Column('region', sa.String(length=255), nullable=True),
            sa.Column('comment_content', models.types.LongText(), nullable=True),
            sa.Column('source_video_url', sa.Text(), nullable=True),
            sa.Column('source_video_title', sa.Text(), nullable=True),
            sa.Column('intent_score', sa.Integer(), server_default=sa.text('0'), nullable=False),
            sa.Column('intent_tags', sa.JSON(), nullable=True),
            sa.Column('intent_reason', models.types.LongText(), nullable=True),
            sa.Column('status', sa.String(length=50), server_default=sa.text("'new'"), nullable=False),
            sa.Column('contacted_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
            sa.PrimaryKeyConstraint('id', name='lead_pkey'),
            sa.UniqueConstraint('tenant_id', 'platform', 'platform_user_id', name='unique_lead_platform_user')
        )
    
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.create_index('lead_tenant_idx', ['tenant_id'], unique=False)
        batch_op.create_index('lead_task_idx', ['task_id'], unique=False)
        batch_op.create_index('lead_status_idx', ['status'], unique=False)
        batch_op.create_index('lead_intent_idx', ['intent_score'], unique=False)
        batch_op.create_index('lead_created_at_idx', ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.drop_index('lead_created_at_idx')
        batch_op.drop_index('lead_intent_idx')
        batch_op.drop_index('lead_status_idx')
        batch_op.drop_index('lead_task_idx')
        batch_op.drop_index('lead_tenant_idx')
    
    op.drop_table('leads')
    
    with op.batch_alter_table('lead_tasks', schema=None) as batch_op:
        batch_op.drop_index('lead_task_created_at_idx')
        batch_op.drop_index('lead_task_status_idx')
        batch_op.drop_index('lead_task_tenant_idx')
    
    op.drop_table('lead_tasks')

