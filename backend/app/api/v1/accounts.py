"""账户与流水接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success
from app.database import get_db
from app.dependencies import get_page_params
from app.models.account import AccountTransaction
from app.schemas.common import PageParams
from app.services import account_service, auth_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
async def my_account(current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    account = await account_service.ensure_account(db, current_user.id)
    return success(
        {
            "account_no": account.account_no,
            "available_amount": str(account.available_amount),
            "frozen_amount": str(account.frozen_amount),
            "pending_amount": str(account.pending_amount),
        }
    )


@router.get("/transactions")
async def transactions(
    business_type: str | None = None,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    base = select(AccountTransaction).where(AccountTransaction.user_id == current_user.id)
    if business_type:
        base = base.where(AccountTransaction.business_type == business_type)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(AccountTransaction.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return success(
        {
            "items": [
                {
                    "transaction_no": t.transaction_no,
                    "business_type": t.business_type,
                    "amount": str(t.amount),
                    "before_balance": str(t.before_balance),
                    "after_balance": str(t.after_balance),
                    "direction": t.direction,
                    "reason": t.reason,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in items
            ],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )
