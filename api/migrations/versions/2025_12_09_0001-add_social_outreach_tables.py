"""Add social outreach tables for X/Instagram funnel conversion

Revision ID: b3c4d5e6f7a8
Revises: ff077a92e2e2
Create Date: 2025-12-09 00:01:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = 'ff077a92e2e2'
branch_labels = None
depends_on = None


def upgrade():
    """Create tables for social outreach funnel conversion system."""
    
    # Create target_kols table - KOL accounts to mimic
    op.create_table('target_kols',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('profile_url', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('follower_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('following_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('language', sa.String(length=20), server_default=sa.text("'en'"), nullable=False),
        sa.Column('niche', sa.String(length=100), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'active'"), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='target_kol_pkey'),
        sa.UniqueConstraint('tenant_id', 'platform', 'username', name='unique_target_kol_platform_user')
    )
    with op.batch_alter_table('target_kols', schema=None) as batch_op:
        batch_op.create_index('target_kol_tenant_idx', ['tenant_id'], unique=False)
        batch_op.create_index('target_kol_platform_idx', ['platform'], unique=False)
        batch_op.create_index('target_kol_status_idx', ['status'], unique=False)

    # Create sub_accounts table - accounts for outreach operations
    op.create_table('sub_accounts',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(), nullable=False),
        sa.Column('target_kol_id', postgresql.UUID(), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('email_password_encrypted', sa.Text(), nullable=True),
        sa.Column('password_encrypted', sa.Text(), nullable=True),
        sa.Column('browser_profile_id', sa.String(length=255), nullable=True),
        sa.Column('browser_provider', sa.String(length=50), nullable=True),
        sa.Column('proxy_config', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'healthy'"), nullable=False),
        sa.Column('last_health_check', sa.DateTime(), nullable=True),
        sa.Column('cooling_until', sa.DateTime(), nullable=True),
        sa.Column('ban_reason', sa.Text(), nullable=True),
        sa.Column('daily_follows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('daily_dms', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('daily_limit_follows', sa.Integer(), server_default=sa.text('50'), nullable=False),
        sa.Column('daily_limit_dms', sa.Integer(), server_default=sa.text('30'), nullable=False),
        sa.Column('total_follows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_dms', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_conversions', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('account_created_at', sa.DateTime(), nullable=True),
        sa.Column('is_warmed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='sub_account_pkey'),
        sa.UniqueConstraint('tenant_id', 'platform', 'username', name='unique_sub_account_platform_user')
    )
    with op.batch_alter_table('sub_accounts', schema=None) as batch_op:
        batch_op.create_index('sub_account_tenant_idx', ['tenant_id'], unique=False)
        batch_op.create_index('sub_account_kol_idx', ['target_kol_id'], unique=False)
        batch_op.create_index('sub_account_status_idx', ['status'], unique=False)

    # Create follower_targets table - followers to convert
    op.create_table('follower_targets',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(), nullable=False),
        sa.Column('target_kol_id', postgresql.UUID(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('platform_user_id', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('follower_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('following_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('post_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_private', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('quality_tier', sa.String(length=20), server_default=sa.text("'medium'"), nullable=False),
        sa.Column('quality_score', sa.Integer(), server_default=sa.text('50'), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'new'"), nullable=False),
        sa.Column('assigned_sub_account_id', postgresql.UUID(), nullable=True),
        sa.Column('scraped_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('followed_at', sa.DateTime(), nullable=True),
        sa.Column('follow_back_at', sa.DateTime(), nullable=True),
        sa.Column('dm_sent_at', sa.DateTime(), nullable=True),
        sa.Column('converted_at', sa.DateTime(), nullable=True),
        sa.Column('follow_timeout_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='follower_target_pkey'),
        sa.UniqueConstraint('tenant_id', 'platform', 'platform_user_id', name='unique_follower_target_platform_user')
    )
    with op.batch_alter_table('follower_targets', schema=None) as batch_op:
        batch_op.create_index('follower_target_tenant_idx', ['tenant_id'], unique=False)
        batch_op.create_index('follower_target_kol_idx', ['target_kol_id'], unique=False)
        batch_op.create_index('follower_target_status_idx', ['status'], unique=False)
        batch_op.create_index('follower_target_quality_idx', ['quality_tier'], unique=False)

    # Create outreach_conversations table - DM conversations
    op.create_table('outreach_conversations',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(), nullable=False),
        sa.Column('sub_account_id', postgresql.UUID(), nullable=False),
        sa.Column('follower_target_id', postgresql.UUID(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'ai_handling'"), nullable=False),
        sa.Column('ai_turns', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('ai_failed_turns', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('human_operator_id', postgresql.UUID(), nullable=True),
        sa.Column('human_takeover_at', sa.DateTime(), nullable=True),
        sa.Column('human_takeover_reason', sa.Text(), nullable=True),
        sa.Column('whatsapp_link_sent', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('whatsapp_link_sent_at', sa.DateTime(), nullable=True),
        sa.Column('conversion_confirmed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('conversion_confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('last_message_from', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='outreach_conversation_pkey'),
        sa.UniqueConstraint('sub_account_id', 'follower_target_id', name='unique_conversation_sub_target')
    )
    with op.batch_alter_table('outreach_conversations', schema=None) as batch_op:
        batch_op.create_index('outreach_conversation_tenant_idx', ['tenant_id'], unique=False)
        batch_op.create_index('outreach_conversation_sub_account_idx', ['sub_account_id'], unique=False)
        batch_op.create_index('outreach_conversation_target_idx', ['follower_target_id'], unique=False)
        batch_op.create_index('outreach_conversation_status_idx', ['status'], unique=False)

    # Create outreach_messages table - individual messages
    op.create_table('outreach_messages',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sender_type', sa.String(length=20), nullable=False),
        sa.Column('sender_id', postgresql.UUID(), nullable=True),
        sa.Column('ai_intent_detected', sa.String(length=100), nullable=True),
        sa.Column('ai_response_template', sa.String(length=255), nullable=True),
        sa.Column('platform_message_id', sa.String(length=255), nullable=True),
        sa.Column('delivered', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='outreach_message_pkey')
    )
    with op.batch_alter_table('outreach_messages', schema=None) as batch_op:
        batch_op.create_index('outreach_message_conversation_idx', ['conversation_id'], unique=False)
        batch_op.create_index('outreach_message_created_at_idx', ['created_at'], unique=False)

    # Create outreach_tasks table - batch task scheduling
    op.create_table('outreach_tasks',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(), nullable=False),
        sa.Column('target_kol_id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('message_templates', sa.JSON(), nullable=True),
        sa.Column('target_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('processed_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('success_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('failed_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='outreach_task_pkey')
    )
    with op.batch_alter_table('outreach_tasks', schema=None) as batch_op:
        batch_op.create_index('outreach_task_tenant_idx', ['tenant_id'], unique=False)
        batch_op.create_index('outreach_task_kol_idx', ['target_kol_id'], unique=False)
        batch_op.create_index('outreach_task_status_idx', ['status'], unique=False)


def downgrade():
    """Drop all social outreach tables."""
    # Drop outreach_tasks
    with op.batch_alter_table('outreach_tasks', schema=None) as batch_op:
        batch_op.drop_index('outreach_task_status_idx')
        batch_op.drop_index('outreach_task_kol_idx')
        batch_op.drop_index('outreach_task_tenant_idx')
    op.drop_table('outreach_tasks')

    # Drop outreach_messages
    with op.batch_alter_table('outreach_messages', schema=None) as batch_op:
        batch_op.drop_index('outreach_message_created_at_idx')
        batch_op.drop_index('outreach_message_conversation_idx')
    op.drop_table('outreach_messages')

    # Drop outreach_conversations
    with op.batch_alter_table('outreach_conversations', schema=None) as batch_op:
        batch_op.drop_index('outreach_conversation_status_idx')
        batch_op.drop_index('outreach_conversation_target_idx')
        batch_op.drop_index('outreach_conversation_sub_account_idx')
        batch_op.drop_index('outreach_conversation_tenant_idx')
    op.drop_table('outreach_conversations')

    # Drop follower_targets
    with op.batch_alter_table('follower_targets', schema=None) as batch_op:
        batch_op.drop_index('follower_target_quality_idx')
        batch_op.drop_index('follower_target_status_idx')
        batch_op.drop_index('follower_target_kol_idx')
        batch_op.drop_index('follower_target_tenant_idx')
    op.drop_table('follower_targets')

    # Drop sub_accounts
    with op.batch_alter_table('sub_accounts', schema=None) as batch_op:
        batch_op.drop_index('sub_account_status_idx')
        batch_op.drop_index('sub_account_kol_idx')
        batch_op.drop_index('sub_account_tenant_idx')
    op.drop_table('sub_accounts')

    # Drop target_kols
    with op.batch_alter_table('target_kols', schema=None) as batch_op:
        batch_op.drop_index('target_kol_status_idx')
        batch_op.drop_index('target_kol_platform_idx')
        batch_op.drop_index('target_kol_tenant_idx')
    op.drop_table('target_kols')
