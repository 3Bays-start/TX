"""会员模块：membership_levels / memberships / membership_orders。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class MembershipLevel(IdMixin, TimestampMixin, Base):
    __tablename__ = "membership_levels"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    duration_days: Mapped[int] = mapped_column(Integer, default=0)
    benefits: Mapped[list] = mapped_column(JSON, default=list)
    order_limits: Mapped[dict] = mapped_column(JSON, default=dict)
    service_permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class Membership(IdMixin, TimestampMixin, Base):
    __tablename__ = "memberships"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("membership_levels.id"))
    level_name: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MembershipOrder(IdMixin, TimestampMixin, Base):
    __tablename__ = "membership_orders"

    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("membership_levels.id"))
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
