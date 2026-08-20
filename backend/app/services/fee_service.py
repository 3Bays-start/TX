"""平台服务费计算。费率变更不影响历史订单（历史快照）。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fee import FeeRecord, FeeRule
from app.utils.misc import gen_no

DEFAULT_FEE_TYPE = "ORDER_SERVICE_FEE"


def calc_fee(amount: Decimal, rate: Decimal, min_fee: Decimal, max_fee: Decimal) -> Decimal:
    fee = Decimal(amount) * Decimal(rate)
    if min_fee and fee < min_fee:
        fee = min_fee
    if max_fee and fee > max_fee:
        fee = max_fee
    return fee.quantize(Decimal("0.01"))


async def get_fee_rule(db: AsyncSession, fee_type: str = DEFAULT_FEE_TYPE) -> FeeRule:
    rule = await db.scalar(
        select(FeeRule)
        .where(FeeRule.fee_type == fee_type, FeeRule.status == "ACTIVE")
        .order_by(FeeRule.id.desc())
    )
    if not rule:
        # 默认 5% 服务费率兜底
        rule = FeeRule(
            fee_type=fee_type,
            name="订单服务费",
            rate=Decimal("0.05"),
            min_fee=Decimal("0"),
            max_fee=Decimal("0"),
            status="ACTIVE",
        )
        db.add(rule)
        await db.flush()
    return rule


async def calc_fee_for_amount(db: AsyncSession, amount: Decimal) -> Decimal:
    rule = await get_fee_rule(db)
    return calc_fee(amount, rule.rate, rule.min_fee, rule.max_fee)


async def create_fee_record(
    db: AsyncSession,
    order_id: int,
    base_amount: Decimal,
    fee_type: str = DEFAULT_FEE_TYPE,
) -> FeeRecord:
    rule = await get_fee_rule(db, fee_type)
    fee_amount = calc_fee(base_amount, rule.rate, rule.min_fee, rule.max_fee)
    record = FeeRecord(
        fee_no=gen_no("FEE", 24),
        order_id=order_id,
        fee_type=fee_type,
        base_amount=base_amount,
        rate=rule.rate,
        fee_amount=fee_amount,
    )
    db.add(record)
    await db.flush()
    return record
