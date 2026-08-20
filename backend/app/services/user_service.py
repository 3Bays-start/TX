"""用户信息服务：资料、团队树、实名。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import UserRelation
from app.models.order import Order
from app.models.user import User


async def get_credit_level(db: AsyncSession, completed_orders: int) -> tuple[str, str]:
    from app.services.credit_service import list_credit_levels

    levels = await list_credit_levels(db)
    current = levels[0] if levels else None
    for level in levels:
        if level.min_orders <= completed_orders:
            current = level
    if not current:
        return "普通", "BASIC"
    return current.name, current.code


async def team_summary(db: AsyncSession, user_id: int) -> dict:
    from datetime import datetime, timedelta

    from sqlalchemy import func

    active_since = datetime.now() - timedelta(days=30)
    total_team = await db.scalar(
        select(func.count(UserRelation.id)).where(UserRelation.parent_id == user_id)
    )
    direct = await db.scalar(
        select(func.count(UserRelation.id)).where(
            UserRelation.parent_id == user_id, UserRelation.level == 1
        )
    )
    # 活跃 = 团队中最近 30 天有登录的用户
    active = await db.scalar(
        select(func.count(UserRelation.id))
        .join(User, User.id == UserRelation.user_id)
        .where(
            UserRelation.parent_id == user_id,
            User.last_login_at >= active_since,
        )
    )
    team_order_count = await db.scalar(
        select(func.count(Order.id))
        .join(UserRelation, UserRelation.user_id == Order.user_id)
        .where(UserRelation.parent_id == user_id, Order.status == "COMPLETED")
    )
    team_order_amount = await db.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0))
        .join(UserRelation, UserRelation.user_id == Order.user_id)
        .where(UserRelation.parent_id == user_id, Order.status == "COMPLETED")
    )
    return {
        "total_team": total_team or 0,
        "direct_count": direct or 0,
        "active_count": active or 0,
        "team_order_count": team_order_count or 0,
        "team_order_amount": str(team_order_amount or 0),
    }


async def team_members(
    db: AsyncSession, user_id: int, page: int, page_size: int
) -> tuple[list[User], int]:
    base = (
        select(User)
        .join(UserRelation, UserRelation.user_id == User.id)
        .where(UserRelation.parent_id == user_id)
    )
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def team_switchable(db: AsyncSession, user_id: int) -> list[User]:
    """上级可切换登录的直推账号（level=1）。"""
    stmt = (
        select(User)
        .join(UserRelation, UserRelation.user_id == User.id)
        .where(UserRelation.parent_id == user_id, UserRelation.level == 1)
        .order_by(User.id.desc())
    )
    return list((await db.execute(stmt)).scalars().all())
