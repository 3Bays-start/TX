"""推广服务：奖励必须与真实商品/服务成交绑定，退款/取消时冲销。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import UserRelation
from app.models.order import Order
from app.models.promotion import PromotionRecord, PromotionRule
from app.services import account_service
from app.utils.misc import gen_no


async def get_promotion_rule(db: AsyncSession, rule_type: str = "ORDER_COMMISSION") -> PromotionRule | None:
    return await db.scalar(
        select(PromotionRule).where(PromotionRule.rule_type == rule_type, PromotionRule.status == "ACTIVE")
    )


async def settle_order_reward(db: AsyncSession, order: Order) -> PromotionRecord | None:
    """订单成交后，给上级发放推广奖励（与真实成交绑定）。"""
    if order.order_type != "BUY" or order.total_amount <= 0:
        return None
    rule = await get_promotion_rule(db)
    if not rule or rule.rate <= 0:
        return None

    parent = await db.scalar(
        select(UserRelation).where(
            UserRelation.user_id == order.user_id, UserRelation.level == 1
        )
    )
    if not parent:
        return None

    reward = (Decimal(order.total_amount) * rule.rate).quantize(Decimal("0.01"))
    if reward <= 0:
        return None

    record = PromotionRecord(
        record_no=gen_no("PR", 24),
        source_user_id=order.user_id,
        source_order_id=order.id,
        beneficiary_user_id=parent.parent_id,
        rule_type=rule.rule_type,
        reward_amount=reward,
        status="PENDING",
    )
    db.add(record)
    await db.flush()

    tx = await account_service.credit(
        db,
        parent.parent_id,
        reward,
        "PROMOTION_REWARD",
        order.id,
        f"推广奖励(订单 {order.order_no})",
    )
    record.status = "SETTLED"
    record.transaction_id = tx.id
    record.settled_at = datetime.now()
    return record


async def reverse_order_reward(db: AsyncSession, order: Order) -> int:
    """订单退款/取消时冲销已发放的推广奖励。"""
    records = list(
        (
            await db.execute(
                select(PromotionRecord).where(
                    PromotionRecord.source_order_id == order.id,
                    PromotionRecord.status == "SETTLED",
                )
            )
        ).scalars().all()
    )
    for record in records:
        await account_service.debit(
            db,
            record.beneficiary_user_id,
            record.reward_amount,
            "PROMOTION_REWARD",
            order.id,
            "退款冲销推广奖励",
        )
        record.status = "REVERSED"
    return len(records)
