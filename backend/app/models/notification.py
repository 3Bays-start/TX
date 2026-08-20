"""通知与公告：notifications / announcements。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class Notification(IdMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="UNREAD", index=True)
    business_type: Mapped[str] = mapped_column(String(30), default="")
    business_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Announcement(IdMixin, TimestampMixin, Base):
    __tablename__ = "announcements"

    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(20), default="NOTICE")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    publisher_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
