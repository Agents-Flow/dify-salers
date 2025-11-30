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
        init=False,
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
