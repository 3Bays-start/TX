"""推广体系：promotion_rules / promotion_records。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class PromotionRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "promotion_rules"

    rule_type: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50), default="")
    rate: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    effective_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PromotionRecord(IdMixin, TimestampMixin, Base):
    __tablename__ = "promotion_records"

    record_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    source_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    beneficiary_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rule_type: Mapped[str] = mapped_column(String(30), default="")
    reward_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("account_transactions.id"), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
