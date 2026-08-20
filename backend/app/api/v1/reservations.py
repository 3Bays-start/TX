"""预约与撮合查询接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success
from app.database import get_db
from app.dependencies import get_page_params
from app.models.matching import MatchOrder
from app.schemas.common import PageParams
from app.schemas.order import ReservationCreate
from app.services import auth_service, reservation_service

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("")
async def create_reservation(
    payload: ReservationCreate,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reservation = await reservation_service.create_reservation(db, current_user.id, payload.order_id)
    return success(
        {
            "id": reservation.id,
            "reservation_no": reservation.reservation_no,
            "order_id": reservation.order_id,
            "status": reservation.status,
        },
        "预约成功",
    )


@router.get("")
async def list_reservations(
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    items, total = await reservation_service.list_reservations(db, current_user.id, params.page, params.page_size)
    return success(
        {
            "items": [
                {
                    "id": r.id,
                    "reservation_no": r.reservation_no,
                    "order_id": r.order_id,
                    "reserved_at": r.reserved_at.isoformat() if r.reserved_at else None,
                    "status": r.status,
                }
                for r in items
            ],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )


@router.get("/matching/status/{order_id}")
async def matching_status(
    order_id: int,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.order import Order

    order = await db.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        return success({"order_id": order_id, "status": "NOT_FOUND"})
    matches = list((await db.execute(select(MatchOrder).where(MatchOrder.parent_order_id == order_id))).scalars().all())
    return success(
        {
            "order_id": order.id,
            "target_amount": str(order.total_amount),
            "matched_amount": str(order.matched_amount),
            "remaining_amount": str(order.total_amount - order.matched_amount),
            "status": order.status,
            "match_count": len(matches),
        }
    )
