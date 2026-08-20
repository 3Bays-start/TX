"""申诉：appeals / appeal_logs。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class Appeal(IdMixin, TimestampMixin, Base):
    __tablename__ = "appeals"

    appeal_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    result: Mapped[str] = mapped_column(String(255), default="")
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AppealLog(IdMixin, Base):
    __tablename__ = "appeal_logs"

    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(30))
    operator_type: Mapped[str] = mapped_column(String(20), default="USER")
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    detail: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
