"""订单模块：orders / order_items / order_status_logs / buy_orders / sell_orders。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class Order(IdMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_type: Mapped[str] = mapped_column(String(20), index=True)
    product_name: Mapped[str] = mapped_column(String(100), default="")
    unit_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    service_fee: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    payable_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    matched_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(30), default="CREATED", index=True)
    reservation_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str] = mapped_column(String(255), default="")
    version: Mapped[int] = mapped_column(Integer, default=0)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 撮合完成后的服务凭证（逗号分隔的 /uploads/ 相对 URL）
    proof_urls: Mapped[str] = mapped_column(String(2000), default="")
    proof_submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OrderStatusLog(IdMixin, Base):
    __tablename__ = "order_status_logs"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str] = mapped_column(String(30), default="")
    to_status: Mapped[str] = mapped_column(String(30))
    operator_type: Mapped[str] = mapped_column(String(20), default="SYSTEM")
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BuyOrder(IdMixin, TimestampMixin, Base):
    __tablename__ = "buy_orders"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    matched_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="WAITING_MATCH")


class SellOrder(IdMixin, TimestampMixin, Base):
    __tablename__ = "sell_orders"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    available_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    matched_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="WAITING_MATCH")
