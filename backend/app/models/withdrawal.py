"""提现：withdrawal_orders / withdrawal_logs。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class WithdrawalOrder(IdMixin, TimestampMixin, Base):
    __tablename__ = "withdrawal_orders"

    withdrawal_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    fee: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    actual_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    usdt_address: Mapped[str] = mapped_column(String(100), default="")
    bank_account: Mapped[str] = mapped_column(String(64), default="")
    bank_name: Mapped[str] = mapped_column(String(50), default="")
    account_name: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    review_reason: Mapped[str] = mapped_column(String(255), default="")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WithdrawalLog(IdMixin, Base):
    __tablename__ = "withdrawal_logs"

    withdrawal_id: Mapped[int] = mapped_column(ForeignKey("withdrawal_orders.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(30))
    operator_type: Mapped[str] = mapped_column(String(20), default="USER")
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    detail: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
