"""账户与账务核心服务。

安全原则：
- 任何余额变化必须写流水
- 禁止 float，统一 Decimal
- 调用方需处于同一 DB 事务中（由 get_db 统一提交）
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, InsufficientBalanceError, NotFoundError
from app.models.account import Account, AccountTransaction
from app.utils.misc import gen_no

PLATFORM_USER_ID = 0


async def ensure_account(db: AsyncSession, user_id: int) -> Account:
    account = await db.scalar(select(Account).where(Account.user_id == user_id))
    if account:
        return account
    account = Account(
        user_id=user_id,
        account_no=gen_no("ACC", 20),
        available_amount=Decimal("0"),
        frozen_amount=Decimal("0"),
        pending_amount=Decimal("0"),
    )
    db.add(account)
    await db.flush()
    return account


async def get_account_for_update(db: AsyncSession, user_id: int) -> Account:
    """行锁获取账户。"""
    if user_id is None:
        raise NotFoundError("ACCOUNT_NOT_FOUND", "账户不存在")
    stmt = select(Account).where(Account.user_id == user_id)
    stmt = stmt.with_for_update()
    account = await db.scalar(stmt)
    if not account:
        account = await ensure_account(db, user_id)
    return account


async def _write_transaction(
    db: AsyncSession,
    account: Account,
    amount: Decimal,
    business_type: str,
    business_id: int | None,
    direction: Literal["IN", "OUT"],
    reason: str = "",
    operator_type: str = "SYSTEM",
    operator_id: int | None = None,
) -> AccountTransaction:
    before = account.available_amount
    tx = AccountTransaction(
        transaction_no=gen_no("TX", 24),
        user_id=account.user_id,
        account_id=account.id,
        business_type=business_type,
        business_id=business_id,
        amount=amount,
        before_balance=before,
        after_balance=before,  # 由调用方在余额变化后回填
        direction=direction,
        reason=reason,
        operator_type=operator_type,
        operator_id=operator_id,
    )
    db.add(tx)
    await db.flush()
    return tx


def _amount(v: Decimal) -> Decimal:
    return Decimal(v).quantize(Decimal("0.01"))


async def credit(
    db: AsyncSession,
    user_id: int,
    amount: Decimal,
    business_type: str,
    business_id: int | None = None,
    reason: str = "",
    operator_type: str = "SYSTEM",
    operator_id: int | None = None,
) -> AccountTransaction:
    amount = _amount(amount)
    if amount <= 0:
        raise AppError("MATCH_AMOUNT_INVALID", "入账金额无效")
    account = await get_account_for_update(db, user_id)
    before = account.available_amount
    account.available_amount += amount
    account.version += 1
    tx = AccountTransaction(
        transaction_no=gen_no("TX", 24),
        user_id=account.user_id,
        account_id=account.id,
        business_type=business_type,
        business_id=business_id,
        amount=amount,
        before_balance=before,
        after_balance=account.available_amount,
        direction="IN",
        reason=reason,
        operator_type=operator_type,
        operator_id=operator_id,
    )
    db.add(tx)
    await db.flush()
    return tx


async def debit(
    db: AsyncSession,
    user_id: int,
    amount: Decimal,
    business_type: str,
    business_id: int | None = None,
    reason: str = "",
    operator_type: str = "SYSTEM",
    operator_id: int | None = None,
) -> AccountTransaction:
    amount = _amount(amount)
    if amount <= 0:
        raise AppError("MATCH_AMOUNT_INVALID", "出账金额无效")
    account = await get_account_for_update(db, user_id)
    if account.available_amount < amount:
        raise InsufficientBalanceError()
    before = account.available_amount
    account.available_amount -= amount
    account.version += 1
    tx = AccountTransaction(
        transaction_no=gen_no("TX", 24),
        user_id=account.user_id,
        account_id=account.id,
        business_type=business_type,
        business_id=business_id,
        amount=amount,
        before_balance=before,
        after_balance=account.available_amount,
        direction="OUT",
        reason=reason,
        operator_type=operator_type,
        operator_id=operator_id,
    )
    db.add(tx)
    await db.flush()
    return tx


async def freeze(
    db: AsyncSession,
    user_id: int,
    amount: Decimal,
    business_type: str,
    business_id: int | None = None,
    reason: str = "",
) -> AccountTransaction:
    """可用余额 -> 冻结余额。"""
    amount = _amount(amount)
    account = await get_account_for_update(db, user_id)
    if account.available_amount < amount:
        raise InsufficientBalanceError()
    before = account.available_amount
    account.available_amount -= amount
    account.frozen_amount += amount
    account.version += 1
    tx = AccountTransaction(
        transaction_no=gen_no("TX", 24),
        user_id=account.user_id,
        account_id=account.id,
        business_type=business_type,
        business_id=business_id,
        amount=amount,
        before_balance=before,
        after_balance=account.available_amount,
        direction="OUT",
        reason=f"冻结:{reason}",
    )
    db.add(tx)
    await db.flush()
    return tx


async def unfreeze(
    db: AsyncSession,
    user_id: int,
    amount: Decimal,
    business_type: str,
    business_id: int | None = None,
    reason: str = "",
) -> AccountTransaction:
    """冻结余额 -> 可用余额。"""
    amount = _amount(amount)
    account = await get_account_for_update(db, user_id)
    if account.frozen_amount < amount:
        raise InsufficientBalanceError("FROZEN_INSUFFICIENT", "冻结余额不足")
    before = account.available_amount
    account.frozen_amount -= amount
    account.available_amount += amount
    account.version += 1
    tx = AccountTransaction(
        transaction_no=gen_no("TX", 24),
        user_id=account.user_id,
        account_id=account.id,
        business_type=business_type,
        business_id=business_id,
        amount=amount,
        before_balance=before,
        after_balance=account.available_amount,
        direction="IN",
        reason=f"解冻:{reason}",
    )
    db.add(tx)
    await db.flush()
    return tx


async def settle_from_frozen(
    db: AsyncSession,
    buyer_user_id: int,
    seller_user_id: int,
    amount: Decimal,
    business_type: str,
    business_id: int | None = None,
    reason: str = "",
) -> tuple[AccountTransaction, AccountTransaction]:
    """撮合结算：买方冻结 -> 卖方可用。"""
    amount = _amount(amount)
    buyer = await get_account_for_update(db, buyer_user_id)
    if buyer.frozen_amount < amount:
        raise InsufficientBalanceError("FROZEN_INSUFFICIENT", "买方冻结余额不足")
    buyer.frozen_amount -= amount
    buyer.version += 1
    buyer_tx = AccountTransaction(
        transaction_no=gen_no("TX", 24),
        user_id=buyer_user_id,
        account_id=buyer.id,
        business_type=business_type,
        business_id=business_id,
        amount=amount,
        before_balance=buyer.available_amount,
        after_balance=buyer.available_amount,
        direction="OUT",
        reason=f"结算出账:{reason}",
    )
    db.add(buyer_tx)

    seller = await get_account_for_update(db, seller_user_id)
    before = seller.available_amount
    seller.available_amount += amount
    seller.version += 1
    seller_tx = AccountTransaction(
        transaction_no=gen_no("TX", 24),
        user_id=seller_user_id,
        account_id=seller.id,
        business_type=business_type,
        business_id=business_id,
        amount=amount,
        before_balance=before,
        after_balance=seller.available_amount,
        direction="IN",
        reason=f"结算入账:{reason}",
    )
    db.add(seller_tx)
    await db.flush()
    return buyer_tx, seller_tx


async def admin_adjust(
    db: AsyncSession,
    admin_id: int,
    user_id: int,
    amount: Decimal,
    reason: str,
) -> AccountTransaction:
    """人工调整账户余额（必须记录管理员与原因）。"""
    if not reason:
        raise AppError("ADJUSTMENT_REASON_REQUIRED", "人工调整必须填写原因")
    if amount > 0:
        return await credit(
            db, user_id, amount, "ADJUSTMENT", None, reason, "ADMIN", admin_id
        )
    return await debit(
        db, user_id, abs(amount), "ADJUSTMENT", None, reason, "ADMIN", admin_id
    )
