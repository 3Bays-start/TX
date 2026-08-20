"""账户与账务：accounts / account_transactions。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import DECIMAL, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class Account(IdMixin, TimestampMixin, Base):
    __tablename__ = "accounts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    account_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    available_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    frozen_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    pending_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="account")  # noqa: F821


class AccountTransaction(IdMixin, TimestampMixin, Base):
    __tablename__ = "account_transactions"

    transaction_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    business_type: Mapped[str] = mapped_column(String(30), index=True)
    business_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    before_balance: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    after_balance: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    direction: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    operator_type: Mapped[str] = mapped_column(String(20), default="SYSTEM")
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(String(255), default="")
