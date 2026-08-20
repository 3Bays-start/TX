"""邀请码与用户关系树：invite_codes / user_relations。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class InviteCode(IdMixin, TimestampMixin, Base):
    __tablename__ = "invite_codes"

    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    # 系统邀请码 creator_id 为空（NULL），避免使用不存在的外键 id
    creator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    used_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserRelation(IdMixin, TimestampMixin, Base):
    __tablename__ = "user_relations"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    level: Mapped[int] = mapped_column(default=1)
    path: Mapped[str] = mapped_column(String(1024), default="")


# 供用户树查询使用的辅助表字段
class UserRelationStat(IdMixin, TimestampMixin, Base):
    """用户团队统计缓存表。"""

    __tablename__ = "user_relation_stats"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    total_team: Mapped[int] = mapped_column(default=0)
    direct_count: Mapped[int] = mapped_column(default=0)
    active_count: Mapped[int] = mapped_column(default=0)
    team_order_count: Mapped[int] = mapped_column(default=0)
    team_order_amount: Mapped[int] = mapped_column(default=0)
