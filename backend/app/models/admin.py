"""管理后台 RBAC：admin_users / admin_roles / admin_permissions / admin_user_roles / admin_role_permissions。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class AdminUser(IdMixin, TimestampMixin, Base):
    __tablename__ = "admin_users"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(50), default="")
    role_code: Mapped[str] = mapped_column(String(30), default="ADMIN", index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_super: Mapped[bool] = mapped_column(Boolean, default=False)


class AdminRole(IdMixin, TimestampMixin, Base):
    __tablename__ = "admin_roles"

    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(255), default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)


class AdminPermission(IdMixin, TimestampMixin, Base):
    __tablename__ = "admin_permissions"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    group: Mapped[str] = mapped_column(String(30), default="")
    description: Mapped[str] = mapped_column(String(255), default="")


class AdminUserRole(IdMixin, Base):
    __tablename__ = "admin_user_roles"
    __table_args__ = (UniqueConstraint("admin_id", "role_id", name="uq_admin_user_role"),)

    admin_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("admin_roles.id", ondelete="CASCADE"), index=True)


class AdminRolePermission(IdMixin, Base):
    __tablename__ = "admin_role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    role_id: Mapped[int] = mapped_column(ForeignKey("admin_roles.id", ondelete="CASCADE"), index=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("admin_permissions.id", ondelete="CASCADE"), index=True)
