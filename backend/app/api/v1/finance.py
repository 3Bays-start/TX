"""提现 / 推广记录 / 费用公开接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success
from app.database import get_db
from app.dependencies import get_page_params
from app.models.fee import FeeRule
from app.models.promotion import PromotionRecord
from app.schemas.common import PageParams
from app.schemas.finance import WithdrawalCreate
from app.services import auth_service, withdrawal_service

router = APIRouter(tags=["finance"])


@router.post("/withdrawals")
async def create_withdrawal(
    payload: WithdrawalCreate,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await withdrawal_service.create_withdrawal(
        db, current_user, payload.amount, payload.usdt_address
    )
    return success(
        {"withdrawal_no": order.withdrawal_no, "amount": str(order.amount), "status": order.status},
        "提现申请已提交",
    )


@router.get("/withdrawals")
async def list_withdrawals(
    status: str | None = None,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    items, total = await withdrawal_service.list_withdrawals(db, current_user.id, params.page, params.page_size, status)
    return success(
        {
            "items": [
                {
                    "id": w.id,
                    "withdrawal_no": w.withdrawal_no,
                    "amount": str(w.amount),
                    "actual_amount": str(w.actual_amount),
                    "usdt_address": w.usdt_address,
                    "status": w.status,
                    "review_reason": w.review_reason,
                    "created_at": w.created_at.isoformat() if w.created_at else None,
                }
                for w in items
            ],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )


@router.get("/fees")
async def fee_rules(db: AsyncSession = Depends(get_db)):
    rules = list((await db.execute(select(FeeRule).where(FeeRule.status == "ACTIVE"))).scalars().all())
    return success(
        {
            "items": [
                {
                    "fee_type": r.fee_type,
                    "name": r.name,
                    "rate": str(r.rate),
                    "min_fee": str(r.min_fee),
                    "max_fee": str(r.max_fee),
                }
                for r in rules
            ]
        }
    )


@router.get("/promotion/records")
async def my_promotion_records(
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    base = select(PromotionRecord).where(PromotionRecord.beneficiary_user_id == current_user.id)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(PromotionRecord.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return success(
        {
            "items": [
                {
                    "record_no": r.record_no,
                    "source_order_id": r.source_order_id,
                    "reward_amount": str(r.reward_amount),
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in items
            ],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )
