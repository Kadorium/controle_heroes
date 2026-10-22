"""Persistência de visões pessoais do painel (Alembic 030)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.foundation.database import Base


class ReportingDashboardView(Base):
    __tablename__ = "reporting_dashboard_views"
    __table_args__ = (
        UniqueConstraint("actor_id", "name", name="uq_reporting_dashboard_views_actor_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_preset: Mapped[str] = mapped_column(String(32), nullable=False)
    layout_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    filters_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # FK opcional: users.id como texto opaco — sem join Identity (DEC actor).
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
