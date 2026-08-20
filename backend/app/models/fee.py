"""平台服务费：fee_rules / fee_records。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class FeeRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "fee_rules"

    fee_type: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50), default="")
    rate: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), default=0)
    min_fee: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    max_fee: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    effective_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class FeeRecord(IdMixin, TimestampMixin, Base):
    __tablename__ = "fee_records"

    fee_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    fee_type: Mapped[str] = mapped_column(String(30), index=True)
    base_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    rate: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), default=0)
    fee_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")
