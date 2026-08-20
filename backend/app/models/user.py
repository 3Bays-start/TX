"""用户相关表：users / user_profiles / user_devices / user_login_logs。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(50), default="")
    avatar: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    role: Mapped[str] = mapped_column(String(20), default="USER")
    allow_parent_switch: Mapped[bool] = mapped_column(Boolean, default=True)
    completed_order_count: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_ip: Mapped[str] = mapped_column(String(64), default="")
    register_ip: Mapped[str] = mapped_column(String(64), default="")
    register_channel: Mapped[str] = mapped_column(String(32), default="")

    profile: Mapped[UserProfile] = relationship(back_populates="user", uselist=False)
    account: Mapped[Account] = relationship(back_populates="user", uselist=False)


class UserProfile(IdMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    gender: Mapped[str] = mapped_column(String(10), default="")
    birth_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email: Mapped[str] = mapped_column(String(100), default="")
    region: Mapped[str] = mapped_column(String(100), default="")
    bio: Mapped[str] = mapped_column(String(255), default="")

    user: Mapped[User] = relationship(back_populates="profile")


class UserDevice(IdMixin, TimestampMixin, Base):
    __tablename__ = "user_devices"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(String(128), index=True)
    platform: Mapped[str] = mapped_column(String(20), default="")
    device_model: Mapped[str] = mapped_column(String(100), default="")
    app_version: Mapped[str] = mapped_column(String(32), default="")
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class UserLoginLog(IdMixin, Base):
    __tablename__ = "user_login_logs"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    login_type: Mapped[str] = mapped_column(String(20), default="PASSWORD")
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(255), default="")
    device_id: Mapped[str] = mapped_column(String(128), default="")
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    fail_reason: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# 前置引用，避免循环
from app.models.account import Account  # noqa: E402
