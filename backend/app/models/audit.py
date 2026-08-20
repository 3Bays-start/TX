"""审计与系统：operation_logs / idempotency_records / system_configs。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class OperationLog(IdMixin, Base):
    __tablename__ = "operation_logs"

    operator_type: Mapped[str] = mapped_column(String(20), default="SYSTEM")
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    module: Mapped[str] = mapped_column(String(30), default="")
    target_type: Mapped[str] = mapped_column(String(30), default="")
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    before_data: Mapped[str] = mapped_column(Text, default="")
    after_data: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(String(255), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(255), default="")
    request_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class IdempotencyRecord(IdMixin, TimestampMixin, Base):
    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(String(128), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    business_type: Mapped[str] = mapped_column(String(30), index=True)
    business_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    response_data: Mapped[str] = mapped_column(Text, default="")


class SystemConfig(IdMixin, TimestampMixin, Base):
    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(String(255), default="")
