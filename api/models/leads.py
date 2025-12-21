"""
Lead acquisition models for the Dify Sales module.
Following Dify's existing model patterns with TypeBase and StringUUID.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import TypeBase
from .types import LongText, StringUUID


class LeadTaskStatus(StrEnum):
    """Lead task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LeadStatus(StrEnum):
    """Lead customer status."""

    NEW = "new"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    INVALID = "invalid"


class SupportedPlatform(StrEnum):
    """Supported social media platforms for lead crawling."""

    DOUYIN = "douyin"  # 抖音
    XIAOHONGSHU = "xiaohongshu"  # 小红书
    KUAISHOU = "kuaishou"  # 快手
    BILIBILI = "bilibili"  # B站
    WEIBO = "weibo"  # 微博
    X = "x"  # X (formerly Twitter)
    INSTAGRAM = "instagram"  # Instagram


class SubAccountStatus(StrEnum):
    """Sub-account health status."""

    HEALTHY = "healthy"
    NEEDS_VERIFICATION = "needs_verification"
    BANNED = "banned"
    COOLING = "cooling"
    PASSWORD_ERROR = "password_error"


class FollowerTargetStatus(StrEnum):
    """Follower target conversion status."""

    NEW = "new"  # Newly scraped, not touched
    FOLLOWED = "followed"  # Follow request sent
    FOLLOW_BACK = "follow_back"  # Mutual follow achieved (for Instagram)
    DM_SENT = "dm_sent"  # DM sent
    CONVERSING = "conversing"  # AI conversation in progress
    NEEDS_HUMAN = "needs_human"  # Requires human intervention
    CONVERTED = "converted"  # Successfully converted to private domain
    FAILED = "failed"  # Conversion failed
    UNFOLLOWED = "unfollowed"  # Auto-unfollowed due to timeout


class ConversationStatus(StrEnum):
    """Outreach conversation status."""

    AI_HANDLING = "ai_handling"
    NEEDS_HUMAN = "needs_human"
    HUMAN_HANDLING = "human_handling"
    CLOSED = "closed"


class QualityTier(StrEnum):
    """Follower quality tier for filtering."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LeadTask(TypeBase):
    """
    Lead acquisition task model.
    Stores crawling task configuration and execution status.
    """

    __tablename__ = "lead_tasks"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="lead_task_pkey"),
        sa.Index("lead_task_tenant_idx", "tenant_id"),
        sa.Index("lead_task_status_idx", "status"),
        sa.Index("lead_task_created_at_idx", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(
        String(50),
        default="douyin",
        server_default=sa.text("'douyin'"),
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="comment_crawl",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        server_default=sa.text("'pending'"),
        init=False,
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        init=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        LongText,
        nullable=True,
        default=None,
        init=False,
    )
    total_leads: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
        server_default=sa.text("0"),
        init=False,
    )
    created_by: Mapped[str | None] = mapped_column(
        StringUUID,
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<LeadTask(id={self.id}, name={self.name}, status={self.status})>"


class LeadTaskRun(TypeBase):
    """
    Lead task execution record.
    Tracks each individual run of a task for history and filtering.
    """

    __tablename__ = "lead_task_runs"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="lead_task_run_pkey"),
        sa.Index("lead_task_run_task_idx", "task_id"),
        sa.Index("lead_task_run_started_at_idx", "started_at"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    task_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    run_number: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=1,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="running",
        server_default=sa.text("'running'"),
    )
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime,
        nullable=True,
        default=None,
        init=False,
    )
    total_crawled: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
        server_default=sa.text("0"),
        init=False,
    )
    total_created: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
        server_default=sa.text("0"),
        init=False,
    )
    config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    error_message: Mapped[str | None] = mapped_column(
        LongText,
        nullable=True,
        default=None,
        init=False,
    )

    def __repr__(self) -> str:
        return f"<LeadTaskRun(id={self.id}, task_id={self.task_id}, run={self.run_number})>"


class Lead(TypeBase):
    """
    Lead (potential customer) model.
    Stores customer information crawled from social media platforms.
    """

    __tablename__ = "leads"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="lead_pkey"),
        sa.Index("lead_tenant_idx", "tenant_id"),
        sa.Index("lead_task_idx", "task_id"),
        sa.Index("lead_task_run_idx", "task_run_id"),
        sa.Index("lead_status_idx", "status"),
        sa.Index("lead_intent_idx", "intent_score"),
        sa.Index("lead_created_at_idx", "created_at"),
        sa.UniqueConstraint("tenant_id", "platform", "platform_user_id", name="unique_lead_platform_user"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    task_id: Mapped[str | None] = mapped_column(
        StringUUID,
        nullable=True,
        default=None,
    )
    task_run_id: Mapped[str | None] = mapped_column(
        StringUUID,
        nullable=True,
        default=None,
    )
    platform: Mapped[str] = mapped_column(
        String(50),
        default="douyin",
        server_default=sa.text("'douyin'"),
    )
    platform_user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    # Platform-specific IDs for reply functionality
    platform_comment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    platform_video_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    platform_user_sec_uid: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        default=None,
    )
    nickname: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    region: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    comment_content: Mapped[str | None] = mapped_column(
        LongText,
        nullable=True,
        default=None,
    )
    source_video_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    source_video_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    # Reply tracking
    reply_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    replied_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime,
        nullable=True,
        default=None,
    )
    reply_content: Mapped[str | None] = mapped_column(
        LongText,
        nullable=True,
        default=None,
    )
    intent_score: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
        server_default=sa.text("0"),
    )
    intent_tags: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    intent_reason: Mapped[str | None] = mapped_column(
        LongText,
        nullable=True,
        default=None,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="new",
        server_default=sa.text("'new'"),
    )
    contacted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime,
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, nickname={self.nickname}, intent_score={self.intent_score})>"


class TargetKOL(TypeBase):
    """
    Target KOL account model.
    Represents the influencer accounts whose followers we want to convert.
    Sub-accounts will mimic these KOLs to build trust.
    """

    __tablename__ = "target_kols"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="target_kol_pkey"),
        sa.Index("target_kol_tenant_idx", "tenant_id"),
        sa.Index("target_kol_platform_idx", "platform"),
        sa.Index("target_kol_status_idx", "status"),
        sa.UniqueConstraint("tenant_id", "platform", "username", name="unique_target_kol_platform_user"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # "x" | "instagram"
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    bio: Mapped[str | None] = mapped_column(LongText, nullable=True, default=None)
    follower_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"))
    following_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"))
    region: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    language: Mapped[str] = mapped_column(String(20), default="en", server_default=sa.text("'en'"))
    # Niche category: "stocks" | "crypto" | "finance"
    niche: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(50), default="active", server_default=sa.text("'active'"))
    last_synced_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)
    created_by: Mapped[str | None] = mapped_column(StringUUID, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<TargetKOL(id={self.id}, platform={self.platform}, username={self.username})>"


class SubAccount(TypeBase):
    """
    Sub-account model for outreach operations.
    These accounts perform follow, DM, and engagement tasks.
    Each sub-account is bound to an anti-detect browser profile and proxy.
    """

    __tablename__ = "sub_accounts"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="sub_account_pkey"),
        sa.Index("sub_account_tenant_idx", "tenant_id"),
        sa.Index("sub_account_kol_idx", "target_kol_id"),
        sa.Index("sub_account_status_idx", "status"),
        sa.UniqueConstraint("tenant_id", "platform", "username", name="unique_sub_account_platform_user"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # "x" | "instagram"
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    target_kol_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True, default=None)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    email_password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # Anti-detect browser configuration
    browser_profile_id: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    # Browser provider: "multilogin" | "gologin"
    browser_provider: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)

    # Proxy configuration (stored as JSON)
    proxy_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=None)

    # Status management
    status: Mapped[str] = mapped_column(String(50), default="healthy", server_default=sa.text("'healthy'"))
    last_health_check: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)
    cooling_until: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)
    ban_reason: Mapped[str | None] = mapped_column(Text, nullable=True, default=None, init=False)

    # Daily limits and counters (reset daily)
    daily_follows: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)
    daily_dms: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)
    daily_limit_follows: Mapped[int] = mapped_column(sa.Integer, default=50, server_default=sa.text("50"))
    daily_limit_dms: Mapped[int] = mapped_column(sa.Integer, default=30, server_default=sa.text("30"))

    # Lifetime statistics
    total_follows: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)
    total_dms: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)
    total_conversions: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)

    # Account age for warming strategy
    account_created_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None)
    is_warmed: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=sa.text("false"))

    created_by: Mapped[str | None] = mapped_column(StringUUID, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<SubAccount(id={self.id}, platform={self.platform}, username={self.username}, status={self.status})>"


class FollowerTarget(TypeBase):
    """
    Follower target model.
    Represents followers of target KOLs that we want to convert.
    Tracks the full conversion funnel status.
    """

    __tablename__ = "follower_targets"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="follower_target_pkey"),
        sa.Index("follower_target_tenant_idx", "tenant_id"),
        sa.Index("follower_target_kol_idx", "target_kol_id"),
        sa.Index("follower_target_status_idx", "status"),
        sa.Index("follower_target_quality_idx", "quality_tier"),
        sa.UniqueConstraint("tenant_id", "platform", "platform_user_id", name="unique_follower_target_platform_user"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    target_kol_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # "x" | "instagram"
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    bio: Mapped[str | None] = mapped_column(LongText, nullable=True, default=None)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    follower_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"))
    following_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"))
    post_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"))
    is_verified: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=sa.text("false"))
    is_private: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=sa.text("false"))

    # Quality assessment
    quality_tier: Mapped[str] = mapped_column(String(20), default="medium", server_default=sa.text("'medium'"))
    quality_score: Mapped[int] = mapped_column(sa.Integer, default=50, server_default=sa.text("50"))
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=None)

    # Conversion funnel status
    status: Mapped[str] = mapped_column(String(50), default="new", server_default=sa.text("'new'"))

    # Assigned sub-account for this target
    assigned_sub_account_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True, default=None, init=False)

    # Timestamps for each funnel stage
    scraped_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    followed_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)
    follow_back_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)
    dm_sent_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)
    converted_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)

    # Follow-back timeout (for auto-unfollow)
    follow_timeout_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<FollowerTarget(id={self.id}, username={self.username}, status={self.status})>"


class OutreachConversation(TypeBase):
    """
    Outreach conversation model.
    Tracks DM conversations between sub-accounts and follower targets.
    """

    __tablename__ = "outreach_conversations"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="outreach_conversation_pkey"),
        sa.Index("outreach_conversation_tenant_idx", "tenant_id"),
        sa.Index("outreach_conversation_sub_account_idx", "sub_account_id"),
        sa.Index("outreach_conversation_target_idx", "follower_target_id"),
        sa.Index("outreach_conversation_status_idx", "status"),
        sa.UniqueConstraint("sub_account_id", "follower_target_id", name="unique_conversation_sub_target"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    sub_account_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    follower_target_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)

    # Conversation status
    status: Mapped[str] = mapped_column(String(50), default="ai_handling", server_default=sa.text("'ai_handling'"))

    # AI handling metadata
    ai_turns: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)
    ai_failed_turns: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)

    # Human intervention
    human_operator_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True, default=None, init=False)
    human_takeover_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)
    human_takeover_reason: Mapped[str | None] = mapped_column(Text, nullable=True, default=None, init=False)

    # Conversion tracking
    whatsapp_link_sent: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.text("false"), init=False
    )
    whatsapp_link_sent_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime, nullable=True, default=None, init=False
    )
    conversion_confirmed: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.text("false"), init=False
    )
    conversion_confirmed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime, nullable=True, default=None, init=False
    )

    last_message_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime, nullable=True, default=None, init=False
    )
    # Direction: "us" | "them"
    last_message_from: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=None, init=False
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<OutreachConversation(id={self.id}, status={self.status})>"


class OutreachMessage(TypeBase):
    """
    Outreach message model.
    Individual messages within an outreach conversation.
    """

    __tablename__ = "outreach_messages"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="outreach_message_pkey"),
        sa.Index("outreach_message_conversation_idx", "conversation_id"),
        sa.Index("outreach_message_created_at_idx", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    conversation_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # "outbound" | "inbound"
    content: Mapped[str] = mapped_column(LongText, nullable=False)

    # Message source
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "ai" | "human" | "follower"
    sender_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True, default=None)  # operator ID if human

    # AI decision tracking
    ai_intent_detected: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    ai_response_template: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    # Platform message ID for deduplication
    platform_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    # Delivery status
    delivered: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.text("true"))
    delivered_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)
    read_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<OutreachMessage(id={self.id}, direction={self.direction}, sender_type={self.sender_type})>"


class OutreachTask(TypeBase):
    """
    Outreach task model.
    Represents scheduled follow/DM tasks for batch processing.
    """

    __tablename__ = "outreach_tasks"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="outreach_task_pkey"),
        sa.Index("outreach_task_tenant_idx", "tenant_id"),
        sa.Index("outreach_task_kol_idx", "target_kol_id"),
        sa.Index("outreach_task_status_idx", "status"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    target_kol_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "follow" | "dm" | "follow_dm"
    platform: Mapped[str] = mapped_column(String(50), nullable=False)

    # Task configuration
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # Message templates (for DM tasks)
    message_templates: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=None)

    # Execution settings
    target_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"))
    processed_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)
    success_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)
    failed_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"), init=False)

    status: Mapped[str] = mapped_column(String(50), default="pending", server_default=sa.text("'pending'"), init=False)
    error_message: Mapped[str | None] = mapped_column(LongText, nullable=True, default=None, init=False)

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True, default=None, init=False)

    created_by: Mapped[str | None] = mapped_column(StringUUID, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<OutreachTask(id={self.id}, name={self.name}, status={self.status})>"


class LeadsConfigKey(StrEnum):
    """Configuration keys for leads module."""

    APIFY_API_KEY = "apify_api_key"
    PROXY_POOL_SETTINGS = "proxy_pool_settings"
    BROWSER_PROVIDER = "browser_provider"
    BROWSER_CREDENTIALS = "browser_credentials"
    NOTIFICATION_SETTINGS = "notification_settings"
    DEFAULT_MESSAGE_TEMPLATES = "default_message_templates"


class LeadsActionType(StrEnum):
    """Action types for workflow binding."""

    SCRAPE_FOLLOWERS = "scrape_followers"
    SEND_FOLLOW = "send_follow"
    CHECK_FOLLOWBACK = "check_followback"
    SEND_DM = "send_dm"
    PROCESS_CONVERSATION = "process_conversation"
    GENERATE_MESSAGE = "generate_message"


class LeadsConfig(TypeBase):
    """
    Leads module configuration storage.
    Stores tenant-specific settings for API keys, proxies, browser configs, etc.
    """

    __tablename__ = "leads_configs"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="leads_config_pkey"),
        sa.Index("leads_config_tenant_idx", "tenant_id"),
        sa.UniqueConstraint("tenant_id", "config_key", name="unique_leads_config_tenant_key"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    config_key: Mapped[str] = mapped_column(String(100), nullable=False)
    config_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_encrypted: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<LeadsConfig(id={self.id}, key={self.config_key})>"


class LeadsWorkflowBinding(TypeBase):
    """
    Bind leads actions to Dify apps.
    Maps action types (like send_dm, check_followback) to specific Dify Workflows or Agents.
    """

    __tablename__ = "leads_workflow_bindings"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="leads_workflow_binding_pkey"),
        sa.Index("leads_workflow_binding_tenant_idx", "tenant_id"),
        sa.UniqueConstraint("tenant_id", "action_type", name="unique_leads_binding_tenant_action"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    app_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    app_mode: Mapped[str] = mapped_column(String(50), nullable=False)  # workflow, agent-chat, completion
    is_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.text("true")
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str | None] = mapped_column(StringUUID, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    def __repr__(self) -> str:
        return f"<LeadsWorkflowBinding(id={self.id}, action={self.action_type}, app={self.app_id})>"
