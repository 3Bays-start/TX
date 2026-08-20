"""撮合模块：match_orders / match_logs / matching_jobs。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class MatchOrder(IdMixin, TimestampMixin, Base):
    __tablename__ = "match_orders"

    match_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    parent_order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    buyer_order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    buyer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    seller_order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    seller_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    match_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MatchLog(IdMixin, Base):
    __tablename__ = "match_logs"

    match_no: Mapped[str] = mapped_column(String(32), index=True)
    parent_order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str] = mapped_column(String(500), default="")
    operator_type: Mapped[str] = mapped_column(String(20), default="SYSTEM")
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class MatchingJob(IdMixin, TimestampMixin, Base):
    __tablename__ = "matching_jobs"

    job_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
