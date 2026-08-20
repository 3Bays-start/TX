"""订单服务：创建/支付/取消/状态机。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError, InvalidStatusError, NotFoundError
from app.models.base import OrderStatus, OrderType
from app.models.order import BuyOrder, Order, OrderStatusLog, SellOrder
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services import account_service, fee_service
from app.services.notification_service import notify_user
from app.utils.misc import gen_no

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.CREATED: {OrderStatus.WAITING_PAYMENT, OrderStatus.CANCELLED, OrderStatus.EXPIRED},
    OrderStatus.WAITING_PAYMENT: {OrderStatus.PAID, OrderStatus.CANCELLED, OrderStatus.EXPIRED},
    OrderStatus.PAID: {OrderStatus.WAITING_MATCH, OrderStatus.CANCELLED, OrderStatus.RISK_REVIEW},
    OrderStatus.WAITING_MATCH: {OrderStatus.PARTIAL_MATCHED, OrderStatus.FULL_MATCHED, OrderStatus.CANCELLED, OrderStatus.RISK_REVIEW},
    OrderStatus.PARTIAL_MATCHED: {OrderStatus.FULL_MATCHED, OrderStatus.CANCELLED, OrderStatus.RISK_REVIEW},
    OrderStatus.FULL_MATCHED: {OrderStatus.PROCESSING, OrderStatus.DISPUTED, OrderStatus.RISK_REVIEW},
    OrderStatus.PROCESSING: {OrderStatus.COMPLETED, OrderStatus.DISPUTED, OrderStatus.RISK_REVIEW},
    OrderStatus.RISK_REVIEW: {OrderStatus.WAITING_MATCH, OrderStatus.FULL_MATCHED, OrderStatus.CANCELLED},
    OrderStatus.DISPUTED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
}


async def transition(
    db: AsyncSession,
    order: Order,
    to_status: str,
    operator_type: str = "SYSTEM",
    operator_id: int | None = None,
    reason: str = "",
) -> None:
    if order.status == to_status:
        return
    allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
    if to_status not in allowed:
        raise InvalidStatusError(message=f"当前订单状态({order.status})不允许变更为({to_status})")
    db.add(
        OrderStatusLog(
            order_id=order.id,
            from_status=order.status,
            to_status=to_status,
            operator_type=operator_type,
            operator_id=operator_id,
            reason=reason,
        )
    )
    order.status = to_status
    order.version += 1
    if to_status == OrderStatus.COMPLETED:
        user = await db.get(User, order.user_id)
        if user:
            user.completed_order_count = (user.completed_order_count or 0) + 1
    await db.flush()


async def create_order(db: AsyncSession, user: User, payload: OrderCreate) -> Order:
    if payload.order_type not in (OrderType.BUY, OrderType.SELL):
        raise AppError("ORDER_PARAM_INVALID", "仅支持援助订单（BUY/SELL）")
    if payload.amount is None or payload.amount <= 0:
        raise AppError("ORDER_PARAM_INVALID", "请填写正确的援助金额")
    total = Decimal(payload.amount)
    product_name = payload.remark or "援助订单"
    order_type = payload.order_type

    if order_type == OrderType.BUY:
        fee = await fee_service.calc_fee_for_amount(db, total)
        payable = (total + fee).quantize(Decimal("0.01"))
        order = Order(
            order_no=gen_no("ORD", 24),
            user_id=user.id,
            order_type=order_type,
            product_name=product_name,
            unit_price=total.quantize(Decimal("0.01")),
            total_amount=total.quantize(Decimal("0.01")),
            service_fee=fee,
            payable_amount=payable,
            reservation_time=payload.reservation_time,
            remark=payload.remark,
            status=OrderStatus.WAITING_PAYMENT,
        )
        db.add(order)
        await db.flush()
        db.add(OrderStatusLog(order_id=order.id, from_status="", to_status=order.status, reason="创建订单"))
        db.add(BuyOrder(order_id=order.id, user_id=user.id, target_amount=total))
    else:  # SELL
        order = Order(
            order_no=gen_no("ORD", 24),
            user_id=user.id,
            order_type=order_type,
            product_name=product_name,
            unit_price=total.quantize(Decimal("0.01")),
            total_amount=total.quantize(Decimal("0.01")),
            service_fee=Decimal("0"),
            payable_amount=total.quantize(Decimal("0.01")),
            reservation_time=payload.reservation_time,
            remark=payload.remark,
            status=OrderStatus.WAITING_MATCH,
        )
        db.add(order)
        await db.flush()
        db.add(OrderStatusLog(order_id=order.id, from_status="", to_status=order.status, reason="创建订单"))
        db.add(SellOrder(order_id=order.id, user_id=user.id, available_amount=total))
    await db.flush()
    return order


async def pay_order(db: AsyncSession, user: User, order_id: int) -> Order:
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise NotFoundError("ORDER_NOT_FOUND", "订单不存在")
    if order.status != OrderStatus.WAITING_PAYMENT:
        raise InvalidStatusError()
    if user.status != "ACTIVE":
        raise AppError("USER_FROZEN", "用户状态异常，无法支付")

    # 可用余额 -> 冻结（模拟支付成功，资金托管至撮合结算）
    await account_service.freeze(
        db, user.id, order.payable_amount, "ORDER_PAYMENT", order.id, "订单支付"
    )
    await transition(db, order, OrderStatus.PAID, "USER", user.id, "支付成功")
    await transition(db, order, OrderStatus.WAITING_MATCH, "SYSTEM", reason="进入撮合队列")

    buy = await db.scalar(select(BuyOrder).where(BuyOrder.order_id == order.id))
    if buy:
        buy.status = "WAITING_MATCH"

    await notify_user(db, user.id, "PAYMENT", "支付成功", f"订单 {order.order_no} 已支付，进入撮合队列")
    return order


async def cancel_order(db: AsyncSession, user: User, order_id: int, reason: str = "用户取消") -> Order:
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise NotFoundError("ORDER_NOT_FOUND", "订单不存在")
    if order.order_type in (OrderType.BUY, OrderType.SELL):
        raise AppError("ORDER_CANNOT_CANCEL", "援助订单不可取消")
    if order.status not in (OrderStatus.CREATED, OrderStatus.WAITING_PAYMENT, OrderStatus.WAITING_MATCH, OrderStatus.PARTIAL_MATCHED):
        raise InvalidStatusError()
    was_paid = order.status in (OrderStatus.WAITING_MATCH, OrderStatus.PARTIAL_MATCHED)

    await transition(db, order, OrderStatus.CANCELLED, "USER", user.id, reason)
    # 已支付则解冻退款
    if was_paid and order.payable_amount:
        await account_service.unfreeze(db, user.id, order.payable_amount, "REFUND", order.id, "取消订单退款")
    await notify_user(db, user.id, "ORDER", "订单已取消", f"订单 {order.order_no} 已取消")
    return order


async def complete_order(db: AsyncSession, order: Order, reason: str = "服务完成") -> Order:
    await transition(db, order, OrderStatus.PROCESSING, "SYSTEM", reason=reason)
    await transition(db, order, OrderStatus.COMPLETED, "SYSTEM", reason=reason)
    await notify_user(db, order.user_id, "ORDER", "订单已完成", f"订单 {order.order_no} 已完成")
    from app.services.promotion_service import settle_order_reward

    await settle_order_reward(db, order)
    return order


async def get_order(db: AsyncSession, order_id: int, user_id: int | None = None) -> Order | None:
    order = await db.get(Order, order_id)
    if not order:
        return None
    if user_id is not None and order.user_id != user_id:
        return None
    return order


async def submit_proof(db: AsyncSession, order_id: int, user_id: int, urls: list[str]) -> Order:
    """撮合完成后买方上传服务凭证并绑定到订单。"""
    order = await get_order(db, order_id, user_id)
    if not order:
        raise NotFoundError("ORDER_NOT_FOUND", "订单不存在")
    if order.order_type != OrderType.BUY:
        raise AppError("ORDER_INVALID_STATUS", "仅买入订单可上传凭证")
    if order.status not in (OrderStatus.FULL_MATCHED, OrderStatus.PROCESSING, OrderStatus.COMPLETED):
        raise AppError("ORDER_INVALID_STATUS", "当前订单状态不允许上传凭证")
    prefix = settings.UPLOAD_URL_PREFIX
    if not urls or any(not u.startswith(prefix) for u in urls):
        raise AppError("INVALID_PROOF_URL", "凭证地址无效，请先通过上传接口获取")

    existing = [u for u in (order.proof_urls or "").split(",") if u]
    for u in urls:
        if u not in existing:
            existing.append(u)
    order.proof_urls = ",".join(existing)
    order.proof_submitted_at = datetime.now()
    await db.flush()
    return order
