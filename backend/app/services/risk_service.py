"""风控服务：风险检查、事件记录、等级动作。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk import RiskEvent, RiskUser
from app.models.user import User
from app.utils.misc import gen_no


async def get_user_risk(db: AsyncSession, user_id: int) -> RiskUser | None:
    return await db.scalar(select(RiskUser).where(RiskUser.user_id == user_id))


async def create_risk_event(
    db: AsyncSession,
    user_id: int,
    rule_code: str,
    level: str,
    action: str,
    detail: str = "",
) -> RiskEvent:
    event = RiskEvent(
        event_no=gen_no("RISK", 24),
        user_id=user_id,
        rule_code=rule_code,
        level=level,
        action=action,
        detail=detail,
    )
    db.add(event)
    await db.flush()

    # 联动用户风险等级
    user = await db.get(User, user_id)
    if user and _level_rank(level) > _level_rank(user.risk_level):
        user.risk_level = level
    risk_user = await get_user_risk(db, user_id)
    if not risk_user:
        risk_user = RiskUser(user_id=user_id, risk_level=level)
        db.add(risk_user)
    else:
        if _level_rank(level) > _level_rank(risk_user.risk_level):
            risk_user.risk_level = level
        risk_user.review_count += 1
    return event


def _level_rank(level: str) -> int:
    return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}.get(level, 0)


async def apply_risk_action(db: AsyncSession, user_id: int, action: str, reason: str = "") -> None:
    """风控动作：FREEZE -> 冻结用户；BLOCK -> 禁用用户。"""
    from datetime import datetime

    user = await db.get(User, user_id)
    if not user:
        return
    if action == "FREEZE":
        user.status = "FROZEN"
    elif action == "BLOCK":
        user.status = "DISABLED"
    risk_user = await get_user_risk(db, user_id)
    if risk_user:
        risk_user.status = action
        risk_user.last_review_at = datetime.now()
        if reason:
            risk_user.remark = reason


async def list_risk_events(
    db: AsyncSession, page: int, page_size: int, status: str | None = None
) -> tuple[list[RiskEvent], int]:
    base = select(RiskEvent)
    if status:
        base = base.where(RiskEvent.status == status)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(RiskEvent.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def check_order_risk(db: AsyncSession, user_id: int) -> tuple[bool, str]:
    """订单风控检查：短期内高频创建/取消触发 REVIEW。"""
    from datetime import datetime, timedelta

    from sqlalchemy import func

    from app.models.order import Order

    since = datetime.now() - timedelta(days=1)
    today_orders = await db.scalar(
        select(func.count(Order.id)).where(
            Order.user_id == user_id,
            Order.created_at >= since,
        )
    )
    if today_orders and today_orders >= 20:
        await create_risk_event(db, user_id, "ORDER_FREQUENCY", "MEDIUM", "REVIEW", "24小时内订单数量异常")
        return True, "ORDER_FREQUENCY"

    cancellations = await db.scalar(
        select(func.count(Order.id)).where(
            Order.user_id == user_id,
            Order.status == "CANCELLED",
            Order.created_at >= since,
        )
    )
    if cancellations and cancellations >= 10:
        await create_risk_event(db, user_id, "ORDER_CANCEL_FREQUENCY", "MEDIUM", "REVIEW", "短时间大量取消订单")
        return True, "ORDER_CANCEL_FREQUENCY"
    return False, ""
