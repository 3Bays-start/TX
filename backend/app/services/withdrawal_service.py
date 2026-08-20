"""提现服务：申请/审核/完成，余额冻结，风控检查。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError, InsufficientBalanceError, NotFoundError
from app.models.user import User
from app.models.withdrawal import WithdrawalLog, WithdrawalOrder
from app.services import account_service, risk_service
from app.utils.misc import gen_no


async def create_withdrawal(
    db: AsyncSession,
    user: User,
    amount: Decimal,
    usdt_address: str,
) -> WithdrawalOrder:
    if amount <= 0:
        raise AppError("WITHDRAWAL_INVALID", "提现金额无效")
    if amount < Decimal(str(settings.WITHDRAW_MIN_AMOUNT)):
        raise AppError("WITHDRAWAL_INVALID", f"提现金额不能低于 {settings.WITHDRAW_MIN_AMOUNT}")
    if amount > Decimal(str(settings.WITHDRAW_DAILY_LIMIT)):
        raise AppError("WITHDRAWAL_INVALID", f"单笔提现不能超过 {settings.WITHDRAW_DAILY_LIMIT}")

    # 当日提现总额（含待处理/已处理）限制
    from datetime import datetime
    from datetime import time as dtime

    from sqlalchemy import func

    start_of_day = datetime.combine(datetime.now().date(), dtime.min)
    today_sum = await db.scalar(
        select(func.coalesce(func.sum(WithdrawalOrder.amount), 0)).where(
            WithdrawalOrder.user_id == user.id,
            WithdrawalOrder.status.in_(["PENDING", "REVIEWING", "APPROVED", "PROCESSING", "COMPLETED"]),
            WithdrawalOrder.created_at >= start_of_day,
        )
    )
    already = Decimal(str(today_sum or 0))
    if already + amount > Decimal(str(settings.WITHDRAW_DAILY_LIMIT)):
        raise AppError("WITHDRAWAL_INVALID", "今日提现已达到限额")

    # 风控检查
    risk_user = await risk_service.get_user_risk(db, user.id)
    if risk_user and risk_user.risk_level in ("HIGH", "CRITICAL"):
        raise AppError("RISK_REVIEW_REQUIRED", "账户存在风控异常，暂无法提现")

    order = WithdrawalOrder(
        withdrawal_no=gen_no("WD", 24),
        user_id=user.id,
        amount=amount,
        fee=Decimal("0"),
        actual_amount=amount,
        usdt_address=usdt_address,
        status="PENDING",
        risk_level=risk_user.risk_level if risk_user else "LOW",
    )
    db.add(order)
    await db.flush()

    # 冻结可用余额
    await account_service.freeze(db, user.id, amount, "WITHDRAWAL", order.id, "提现冻结")
    db.add(WithdrawalLog(withdrawal_id=order.id, action="CREATE", detail="用户提交提现申请"))
    return order


async def review_withdrawal(
    db: AsyncSession,
    withdrawal_id: int,
    admin_id: int,
    approve: bool,
    reason: str = "",
) -> WithdrawalOrder:
    order = await db.scalar(
        select(WithdrawalOrder).where(WithdrawalOrder.id == withdrawal_id).with_for_update()
    )
    if not order:
        raise NotFoundError("WITHDRAWAL_NOT_FOUND", "提现记录不存在")
    if order.status not in ("PENDING", "REVIEWING"):
        raise AppError("WITHDRAWAL_INVALID", "当前状态不可审核")

    if approve:
        order.status = "APPROVED"
        db.add(WithdrawalLog(withdrawal_id=order.id, action="APPROVE", operator_type="ADMIN", operator_id=admin_id, detail=f"审核通过:{reason}"))
    else:
        order.status = "REJECTED"
        order.review_reason = reason
        await account_service.unfreeze(db, order.user_id, order.amount, "WITHDRAWAL", order.id, "提现驳回解冻")
        db.add(WithdrawalLog(withdrawal_id=order.id, action="REJECT", operator_type="ADMIN", operator_id=admin_id, detail=f"驳回:{reason}"))
    order.reviewed_by = admin_id
    order.reviewed_at = datetime.now()
    return order


async def complete_withdrawal(db: AsyncSession, withdrawal_id: int, admin_id: int) -> WithdrawalOrder:
    order = await db.scalar(
        select(WithdrawalOrder).where(WithdrawalOrder.id == withdrawal_id).with_for_update()
    )
    if not order:
        raise NotFoundError("WITHDRAWAL_NOT_FOUND", "提现记录不存在")
    if order.status not in ("APPROVED", "PROCESSING"):
        raise AppError("WITHDRAWAL_INVALID", "当前状态不可处理")
    # 冻结 → 出账（模拟第三方处理完成）
    await _settle_frozen(db, order)
    order.status = "COMPLETED"
    order.processed_at = datetime.now()
    order.completed_at = datetime.now()
    db.add(WithdrawalLog(withdrawal_id=order.id, action="COMPLETE", operator_type="ADMIN", operator_id=admin_id, detail="提现完成"))
    return order


async def _settle_frozen(db: AsyncSession, order: WithdrawalOrder) -> None:
    """冻结余额在提现完成时正式出账。"""
    from app.services.account_service import get_account_for_update

    account = await get_account_for_update(db, order.user_id)
    if account.frozen_amount < order.amount:
        raise InsufficientBalanceError("FROZEN_INSUFFICIENT", "冻结余额不足")
    before = account.available_amount
    account.frozen_amount -= order.amount
    account.version += 1
    from app.models.account import AccountTransaction

    db.add(
        AccountTransaction(
            transaction_no=gen_no("TX", 24),
            user_id=order.user_id,
            account_id=account.id,
            business_type="WITHDRAWAL",
            business_id=order.id,
            amount=order.amount,
            before_balance=before,
            after_balance=account.available_amount,
            direction="OUT",
            reason=f"提现完成:{order.withdrawal_no}",
        )
    )


async def list_withdrawals(
    db: AsyncSession, user_id: int, page: int, page_size: int, status: str | None = None
) -> tuple[list[WithdrawalOrder], int]:
    base = select(WithdrawalOrder).where(WithdrawalOrder.user_id == user_id)
    if status:
        base = base.where(WithdrawalOrder.status == status)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(WithdrawalOrder.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total
