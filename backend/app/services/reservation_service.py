"""预约服务。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.order import Order
from app.models.reservation import ReservationOrder
from app.utils.misc import gen_no


async def create_reservation(db: AsyncSession, user_id: int, order_id: int) -> ReservationOrder:
    order = await db.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise NotFoundError("ORDER_NOT_FOUND", "订单不存在")
    if order.status not in ("WAITING_PAYMENT", "WAITING_MATCH", "PARTIAL_MATCHED", "PAID"):
        raise AppError("ORDER_INVALID_STATUS", "当前订单状态不可预约")

    existing = await db.scalar(
        select(ReservationOrder).where(
            ReservationOrder.order_id == order_id, ReservationOrder.status == "WAITING"
        )
    )
    if existing:
        return existing

    reservation = ReservationOrder(
        reservation_no=gen_no("RSV", 24),
        order_id=order.id,
        user_id=user_id,
        reserved_at=datetime.now(),
    )
    db.add(reservation)
    await db.flush()
    return reservation


async def list_reservations(
    db: AsyncSession, user_id: int, page: int, page_size: int
) -> tuple[list[ReservationOrder], int]:
    base = select(ReservationOrder).where(ReservationOrder.user_id == user_id)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(ReservationOrder.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total
