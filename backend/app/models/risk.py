"""风控：risk_rules / risk_events / risk_users。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class RiskRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "risk_rules"

    rule_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(255), default="")
    level: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    action: Mapped[str] = mapped_column(String(20), default="REVIEW")
    threshold: Mapped[str] = mapped_column(String(255), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class RiskEvent(IdMixin, TimestampMixin, Base):
    __tablename__ = "risk_events"

    event_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rule_code: Mapped[str] = mapped_column(String(40), index=True)
    level: Mapped[str] = mapped_column(String(20), index=True)
    action: Mapped[str] = mapped_column(String(20))
    detail: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RiskUser(IdMixin, TimestampMixin, Base):
    __tablename__ = "risk_users"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    status: Mapped[str] = mapped_column(String(20), default="NORMAL")
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str] = mapped_column(String(255), default="")
