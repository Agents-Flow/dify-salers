"""Add reply fields to leads table

Revision ID: 0b71d12af5e2
Revises: a1b2c3d4e5f6
Create Date: 2025-11-30 17:09:28.148733

"""
from alembic import op
import models as models
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0b71d12af5e2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    """Add platform-specific IDs and reply tracking fields to leads table."""
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.add_column(sa.Column('platform_comment_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('platform_video_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('platform_user_sec_uid', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('reply_url', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('replied_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('reply_content', models.types.LongText(), nullable=True))


def downgrade():
    """Remove platform-specific IDs and reply tracking fields from leads table."""
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.drop_column('reply_content')
        batch_op.drop_column('replied_at')
        batch_op.drop_column('reply_url')
        batch_op.drop_column('platform_user_sec_uid')
        batch_op.drop_column('platform_video_id')
        batch_op.drop_column('platform_comment_id')
