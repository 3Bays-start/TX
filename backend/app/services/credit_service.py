"""信用等级服务：按已完成订单数计算信用等级。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit import CreditLevel


async def list_credit_levels(db: AsyncSession) -> list[CreditLevel]:
    stmt = (
        select(CreditLevel)
        .where(CreditLevel.status == "ACTIVE")
        .order_by(CreditLevel.min_orders)
    )
    return list((await db.execute(stmt)).scalars().all())


def compute_credit(completed_orders: int, levels: list[CreditLevel]) -> dict:
    """根据已完成订单数与信用等级配置计算信用等级信息（纯函数，便于测试）。"""
    current = levels[0] if levels else None
    for level in levels:
        if level.min_orders <= completed_orders:
            current = level
    next_level = None
    for level in levels:
        if level.min_orders > completed_orders:
            next_level = level
            break
    if next_level and current:
        current_min = current.min_orders
        next_min = next_level.min_orders
        span = max(next_min - current_min, 1)
        progress = max(min(completed_orders - current_min, span) / span, 0)
        progress = round(progress * 100)
        need = next_min - completed_orders
    else:
        progress = 100
        need = 0
    return {
        "completed_order_count": completed_orders,
        "current": {
            "name": current.name if current else "普通",
            "code": current.code if current else "BASIC",
            "min_orders": current.min_orders if current else 0,
        },
        "next": (
            {
                "name": next_level.name,
                "code": next_level.code,
                "min_orders": next_level.min_orders,
            }
            if next_level
            else None
        ),
        "progress": progress,
        "need": need,
        "levels": [
            {"name": level.name, "code": level.code, "min_orders": level.min_orders, "description": level.description}
            for level in levels
        ],
    }


async def get_credit_info(db: AsyncSession, completed_orders: int) -> dict:
    levels = await list_credit_levels(db)
    return compute_credit(completed_orders, levels)
