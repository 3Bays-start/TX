"""业务单号生成与幂等工具。"""

from __future__ import annotations

import secrets
import string
import time
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import IdempotencyRecord

_ALPHABET = string.ascii_uppercase + string.digits


def gen_no(prefix: str, length: int = 20) -> str:
    """生成业务单号，例如 ORDER202408181234560001。至少含 4 位随机串。"""
    rand_len = max(4, length - len(prefix) - 14)
    rand = "".join(secrets.choice(_ALPHABET) for _ in range(rand_len))
    return f"{prefix}{datetime.now():%Y%m%d%H%M%S}{rand}"


def gen_code(length: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def gen_refresh_token() -> str:
    return secrets.token_urlsafe(48)


async def check_idempotency(
    db: AsyncSession, key: str | None, user_id: int, business_type: str
) -> IdempotencyRecord | None:
    """幂等检查：相同 key 返回已存在记录（重复请求直接返回该记录）。"""
    if not key:
        return None
    stmt = select(IdempotencyRecord).where(
        IdempotencyRecord.key == key,
        IdempotencyRecord.user_id == user_id,
        IdempotencyRecord.business_type == business_type,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def save_idempotency(
    db: AsyncSession,
    key: str | None,
    user_id: int,
    business_type: str,
    business_id: int | None = None,
    response_data: str | None = None,
) -> None:
    if not key:
        return
    record = IdempotencyRecord(
        key=key,
        user_id=user_id,
        business_type=business_type,
        business_id=business_id,
        response_data=response_data or "",
    )
    db.add(record)
    await db.flush()


def ttl_expire(seconds: int) -> str:
    return str(int(time.time()) + seconds)
