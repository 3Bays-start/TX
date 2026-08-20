"""首页轮播广告：banners。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class Banner(IdMixin, TimestampMixin, Base):
    __tablename__ = "banners"

    title: Mapped[str] = mapped_column(String(100))
    subtitle: Mapped[str] = mapped_column(String(200), default="")
    image_url: Mapped[str] = mapped_column(String(500), default="")
    link_type: Mapped[str] = mapped_column(String(20), default="NONE")
    link_value: Mapped[str] = mapped_column(String(255), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
