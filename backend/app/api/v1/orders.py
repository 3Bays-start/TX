"""订单接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.response import success
from app.database import get_db
from app.dependencies import get_page_params
from app.models.matching import MatchOrder
from app.models.order import Order, OrderStatusLog
from app.schemas.common import PageParams
from app.schemas.order import OrderCreate, ProofSubmit
from app.services import auth_service, order_service
from app.utils.misc import check_idempotency, save_idempotency

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("")
async def create_order(
    payload: OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await check_idempotency(db, idempotency_key, current_user.id, "CREATE_ORDER")
    if existing and existing.business_id:
        return success({"order_id": existing.business_id, "duplicated": True})
    order = await order_service.create_order(db, current_user, payload)
    await save_idempotency(db, idempotency_key, current_user.id, "CREATE_ORDER", order.id, str(order.id))
    return success(_order_out(order), "订单创建成功")


@router.get("")
async def list_orders(
    status: str | None = None,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    base = select(Order).where(Order.user_id == current_user.id)
    if status:
        base = base.where(Order.status == status)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(Order.id.desc()).offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return success(
        {
            "items": [_order_out(o) for o in items],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )


@router.get("/{order_id}")
async def order_detail(
    order_id: int,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.get_order(db, order_id, current_user.id)
    if not order:
        raise NotFoundError("ORDER_NOT_FOUND", "订单不存在")
    logs = list((await db.execute(select(OrderStatusLog).where(OrderStatusLog.order_id == order_id))).scalars().all())
    matches = list((await db.execute(select(MatchOrder).where(MatchOrder.parent_order_id == order_id))).scalars().all())
    data = _order_out(order)
    data["status_logs"] = [
        {"from_status": log.from_status, "to_status": log.to_status, "reason": log.reason, "created_at": log.created_at.isoformat() if log.created_at else None}
        for log in logs
    ]
    data["matches"] = [
        {
            "id": m.id,
            "match_no": m.match_no,
            "seller_order_id": m.seller_order_id,
            "seller_user_id": m.seller_user_id,
            "match_amount": str(m.match_amount),
            "status": m.status,
            "completed_at": m.completed_at.isoformat() if m.completed_at else None,
        }
        for m in matches
    ]
    return success(data)


@router.post("/{order_id}/pay")
async def pay_order(
    order_id: int,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.pay_order(db, current_user, order_id)
    return success(_order_out(order), "支付成功，已进入撮合")


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.cancel_order(db, current_user, order_id)
    return success(_order_out(order), "订单已取消")


@router.post("/{order_id}/proof")
async def submit_proof(
    order_id: int,
    payload: ProofSubmit,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.submit_proof(db, order_id, current_user.id, payload.urls)
    return success(_order_out(order), "凭证上传成功")


@router.get("/{order_id}/match")
async def order_match(
    order_id: int,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.get_order(db, order_id, current_user.id)
    if not order:
        raise NotFoundError("ORDER_NOT_FOUND", "订单不存在")
    matches = list((await db.execute(select(MatchOrder).where(MatchOrder.parent_order_id == order_id))).scalars().all())
    return success(
        {
            "order_id": order.id,
            "target_amount": str(order.total_amount),
            "matched_amount": str(order.matched_amount),
            "remaining_amount": str(order.total_amount - order.matched_amount),
            "status": order.status,
            "matches": [
                {
                    "match_no": m.match_no,
                    "seller_order_id": m.seller_order_id,
                    "match_amount": str(m.match_amount),
                    "status": m.status,
                }
                for m in matches
            ],
        }
    )


def _order_out(order: Order) -> dict:
    return {
        "id": order.id,
        "order_no": order.order_no,
        "user_id": order.user_id,
        "order_type": order.order_type,
        "product_name": order.product_name,
        "total_amount": str(order.total_amount),
        "service_fee": str(order.service_fee),
        "payable_amount": str(order.payable_amount),
        "matched_amount": str(order.matched_amount),
        "status": order.status,
        "reservation_time": order.reservation_time.isoformat() if order.reservation_time else None,
        "remark": order.remark,
        "proof_urls": [u for u in (order.proof_urls or "").split(",") if u],
        "proof_submitted_at": order.proof_submitted_at.isoformat() if order.proof_submitted_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }
