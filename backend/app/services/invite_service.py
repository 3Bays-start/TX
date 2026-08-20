"""邀请码服务。"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.invite import InviteCode
from app.utils.misc import gen_code


async def create_invite_codes(
    db: AsyncSession, creator_id: int | None, count: int, expires_in_days: int | None = None
) -> list[InviteCode]:
    codes: list[InviteCode] = []
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now() + timedelta(days=expires_in_days)
    for _ in range(count):
        code = InviteCode(code=gen_code(8), creator_id=creator_id, status="ACTIVE", expires_at=expires_at)
        db.add(code)
        codes.append(code)
    await db.flush()
    return codes


async def create_user_invite_code(db: AsyncSession, user_id: int) -> InviteCode:
    """为注册账号生成唯一邀请码（每个账号一个，终身有效可复用）。"""
    for _ in range(50):
        code_str = gen_code(8)
        exists = await db.scalar(select(InviteCode).where(InviteCode.code == code_str))
        if not exists:
            invite = InviteCode(code=code_str, creator_id=user_id, status="ACTIVE")
            db.add(invite)
            await db.flush()
            return invite
    raise AppError("INVITE_CODE_GEN_FAILED", "邀请码生成失败，请重试")


async def use_invite_code(db: AsyncSession, code_str: str) -> InviteCode:
    """校验邀请码（账号专属邀请码，可复用，不标记为已使用）。"""
    invite = await db.scalar(select(InviteCode).where(InviteCode.code == code_str))
    if not invite:
        raise AppError("INVITE_CODE_INVALID", "邀请码无效")
    if invite.status == "DISABLED":
        raise AppError("INVITE_CODE_INVALID", "邀请码已被禁用")
    if invite.expires_at and invite.expires_at < datetime.now():
        raise AppError("INVITE_CODE_EXPIRED", "邀请码已过期")
    return invite


async def disable_invite_code(db: AsyncSession, invite_id: int) -> InviteCode | None:
    invite = await db.get(InviteCode, invite_id)
    if invite and invite.status == "ACTIVE":
        invite.status = "DISABLED"
        await db.flush()
    return invite


async def get_invite_code(db: AsyncSession, code_str: str) -> InviteCode | None:
    return await db.scalar(select(InviteCode).where(InviteCode.code == code_str))


async def user_invite_codes(db: AsyncSession, user_id: int) -> list[InviteCode]:
    stmt = select(InviteCode).where(InviteCode.creator_id == user_id).order_by(InviteCode.id.desc())
    return list((await db.execute(stmt)).scalars().all())
