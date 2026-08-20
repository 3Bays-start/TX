"""核心撮合引擎：A 订单 → 多 B 订单。

并发安全：
1. Redis 分布式锁 lock:matching:order:{order_id}
2. MySQL SELECT ... FOR UPDATE（父订单 + 卖方订单）
3. 数据库事务（调用方会话统一提交）
4. 幂等：唯一 match_no
5. 乐观锁：version 字段

保证：SUM(match_amount) <= order.total_amount，绝不超额。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.base import OrderStatus, OrderType
from app.models.matching import MatchingJob, MatchLog, MatchOrder
from app.models.order import BuyOrder, Order, SellOrder
from app.services import account_service, fee_service
from app.utils.misc import gen_no
from app.utils.redis_client import LockContext

logger = get_logger("matching")


async def match_order(db: AsyncSession, order_id: int) -> bool:
    """撮合一个买入订单。返回是否发生撮合。"""
    lock_key = f"lock:matching:order:{order_id}"
    async with LockContext(lock_key):
        stmt = select(Order).where(Order.id == order_id).with_for_update()
        order = await db.scalar(stmt)
        if not order:
            logger.warning("撮合：订单 %s 不存在", order_id)
            return False
        if order.status not in (OrderStatus.WAITING_MATCH, OrderStatus.PARTIAL_MATCHED):
            return False

        remaining = Decimal(order.total_amount) - Decimal(order.matched_amount)
        if remaining <= 0:
            return False

        matched_any = await _match_candidates(db, order, remaining)
        if matched_any:
            await db.flush()
            if Decimal(order.total_amount) - Decimal(order.matched_amount) <= 0:
                await _settle_and_complete(db, order)
        return matched_any


async def _match_candidates(db: AsyncSession, order: Order, remaining: Decimal) -> bool:
    """按预约优先级匹配卖方订单。"""
    # 卖方候选：状态等待匹配、尚有可用额度、且非本人
    # 排序规则：预约时间(缺省用创建时间) 升序 → 订单创建时间 升序 → id 升序（最早有效预约优先）
    order_key = func.coalesce(Order.reservation_time, Order.created_at)
    stmt = (
        select(SellOrder)
        .join(Order, Order.id == SellOrder.order_id)
        .where(
            SellOrder.status == "WAITING_MATCH",
            Order.status.in_([OrderStatus.WAITING_MATCH, OrderStatus.PARTIAL_MATCHED]),
            Order.user_id != order.user_id,
        )
        .order_by(
            order_key.asc(),
            Order.created_at.asc(),
            SellOrder.id.asc(),
        )
        .with_for_update()
    )
    candidates = list((await db.execute(stmt)).scalars().all())

    matched_any = False
    for sell in candidates:
        if remaining <= 0:
            break
        available = Decimal(sell.available_amount) - Decimal(sell.matched_amount)
        if available <= 0:
            continue
        match_amount = min(available, remaining)
        if match_amount <= 0:
            continue

        # 幂等防重：同一买卖订单唯一撮合
        dup = await db.scalar(
            select(MatchOrder).where(
                MatchOrder.parent_order_id == order.id,
                MatchOrder.seller_order_id == sell.order_id,
            )
        )
        if dup:
            logger.warning("重复撮合尝试：parent=%s seller=%s", order.id, sell.order_id)
            continue

        match = MatchOrder(
            match_no=gen_no("MCH", 24),
            parent_order_id=order.id,
            parent_user_id=order.user_id,
            buyer_order_id=order.id,
            buyer_user_id=order.user_id,
            seller_order_id=sell.order_id,
            seller_user_id=sell.user_id,
            match_amount=match_amount,
        )
        db.add(match)
        db.add(MatchLog(match_no=match.match_no, parent_order_id=order.id, action="MATCH", detail=f"匹配卖方订单 {sell.order_id} 金额 {match_amount}"))

        sell.matched_amount = Decimal(sell.matched_amount) + match_amount
        sell.status = "FULL_MATCHED" if Decimal(sell.available_amount) - sell.matched_amount <= 0 else "PARTIAL_MATCHED"
        order.matched_amount = Decimal(order.matched_amount) + match_amount
        order.version += 1
        remaining -= match_amount
        matched_any = True

        buy = await db.scalar(select(BuyOrder).where(BuyOrder.order_id == order.id))
        if buy:
            buy.matched_amount = order.matched_amount

    if matched_any:
        from app.services.order_service import transition

        await transition(db, order, OrderStatus.PARTIAL_MATCHED, "SYSTEM", reason="部分撮合")
    return matched_any


async def _settle_and_complete(db: AsyncSession, order: Order) -> None:
    """全部撮合完成：结算资金 + 收取服务费 + 完成订单。"""
    from app.services.order_service import complete_order, transition

    matches = list(
        (
            await db.execute(
                select(MatchOrder).where(
                    MatchOrder.parent_order_id == order.id, MatchOrder.status == "ACTIVE"
                )
            )
        ).scalars().all()
    )
    now = datetime.now()
    for match in matches:
        # 买方冻结 → 卖方可用
        await account_service.settle_from_frozen(
            db,
            order.user_id,
            match.seller_user_id,
            match.match_amount,
            "ORDER_SETTLEMENT",
            match.id,
            f"订单 {order.order_no} 撮合结算",
        )
        match.status = "COMPLETED"
        match.completed_at = now

        # 卖方订单：额度用尽时同步完成（计入信用等级；不调用 complete_order，
        # 避免卖方订单也触发推广奖励导致同一笔交易重复发放）
        sell = await db.scalar(select(SellOrder).where(SellOrder.order_id == match.seller_order_id))
        if sell and sell.status == "FULL_MATCHED":
            seller_order = await db.get(Order, match.seller_order_id)
            if seller_order and seller_order.status in (
                OrderStatus.WAITING_MATCH,
                OrderStatus.PARTIAL_MATCHED,
            ):
                await transition(db, seller_order, OrderStatus.FULL_MATCHED, "SYSTEM", reason="撮合完成")
                await transition(db, seller_order, OrderStatus.PROCESSING, "SYSTEM", reason="撮合结算完成")
                await transition(db, seller_order, OrderStatus.COMPLETED, "SYSTEM", reason="撮合结算完成，订单完成")
                from app.services.notification_service import notify_user

                await notify_user(db, seller_order.user_id, "ORDER", "订单已完成", f"订单 {seller_order.order_no} 已完成")

    # 服务费：买方冻结 → 平台账户，并保存费率快照
    if order.service_fee and order.service_fee > 0:
        await account_service.settle_from_frozen(
            db,
            order.user_id,
            account_service.PLATFORM_USER_ID,
            order.service_fee,
            "SERVICE_FEE",
            order.id,
            f"订单 {order.order_no} 平台服务费",
        )
        await fee_service.create_fee_record(db, order.id, order.total_amount)

    buy = await db.scalar(select(BuyOrder).where(BuyOrder.order_id == order.id))
    if buy:
        buy.status = "FULL_MATCHED"

    await transition(db, order, OrderStatus.FULL_MATCHED, "SYSTEM", reason="撮合完成")
    await complete_order(db, order, reason="撮合结算完成，订单完成")


async def match_selected(
    db: AsyncSession,
    buy_order_ids: list[int],
    sell_order_ids: list[int],
    reason: str = "管理员手动撮合",
) -> dict[str, int]:
    """管理员勾选 BUY + SELL 订单批量撮合：按金额两两配对，支持一对多/多对一。

    返回 {"matched": 撮合笔数, "buy_orders": 完成结算的买入订单数, "sell_orders": 完全撮合并已结算的卖出订单数}
    """
    from app.services.order_service import transition

    result = {"matched": 0, "buy_orders": 0, "sell_orders": 0}
    if not buy_order_ids or not sell_order_ids:
        return result

    order_key = func.coalesce(Order.reservation_time, Order.created_at)
    sells = list(
        (
            await db.execute(
                select(SellOrder)
                .join(Order, Order.id == SellOrder.order_id)
                .where(
                    SellOrder.order_id.in_(sell_order_ids),
                    Order.status.in_([OrderStatus.WAITING_MATCH, OrderStatus.PARTIAL_MATCHED]),
                )
                .order_by(order_key.asc(), Order.created_at.asc(), SellOrder.id.asc())
                .with_for_update()
            )
        ).scalars().all()
    )
    buys = list(
        (
            await db.execute(
                select(Order)
                .where(
                    Order.id.in_(buy_order_ids),
                    Order.status.in_([OrderStatus.WAITING_MATCH, OrderStatus.PARTIAL_MATCHED]),
                )
                .with_for_update()
            )
        ).scalars().all()
    )
    if not sells or not buys:
        return result

    buy_map = {o.id: o for o in buys}
    buy_order = sorted(buys, key=lambda o: (o.reservation_time or o.created_at, o.created_at, o.id))

    for sell in sells:
        sell_avail = Decimal(sell.available_amount) - Decimal(sell.matched_amount)
        if sell_avail <= 0:
            continue
        for o in buy_order:
            if sell_avail <= 0:
                break
            buy = buy_map[o.id]
            if buy.user_id == sell.user_id:
                continue
            remaining = Decimal(buy.total_amount) - Decimal(buy.matched_amount)
            if remaining <= 0:
                continue
            dup = await db.scalar(
                select(MatchOrder).where(
                    MatchOrder.parent_order_id == buy.id,
                    MatchOrder.seller_order_id == sell.order_id,
                )
            )
            if dup:
                continue
            match_amount = min(sell_avail, remaining)
            match = MatchOrder(
                match_no=gen_no("MCH", 24),
                parent_order_id=buy.id,
                parent_user_id=buy.user_id,
                buyer_order_id=buy.id,
                buyer_user_id=buy.user_id,
                seller_order_id=sell.order_id,
                seller_user_id=sell.user_id,
                match_amount=match_amount,
            )
            db.add(match)
            db.add(
                MatchLog(
                    match_no=match.match_no,
                    parent_order_id=buy.id,
                    action="MANUAL_MATCH",
                    detail=f"手动撮合卖方订单 {sell.order_id} 金额 {match_amount}（{reason}）",
                )
            )
            sell.matched_amount = Decimal(sell.matched_amount) + match_amount
            sell.status = "FULL_MATCHED" if Decimal(sell.available_amount) - sell.matched_amount <= 0 else "PARTIAL_MATCHED"
            buy.matched_amount = Decimal(buy.matched_amount) + match_amount
            buy.version += 1
            sell_avail -= match_amount
            result["matched"] += 1

            buy_rec = await db.scalar(select(BuyOrder).where(BuyOrder.order_id == buy.id))
            if buy_rec:
                buy_rec.matched_amount = buy.matched_amount

    # 已产生撮合的卖出订单推进为 PARTIAL_MATCHED（全额时由买入结算完成）
    for sell in sells:
        if sell.matched_amount and Decimal(sell.matched_amount) > 0:
            so = await db.get(Order, sell.order_id)
            if so and so.status == OrderStatus.WAITING_MATCH:
                await transition(db, so, OrderStatus.PARTIAL_MATCHED, "SYSTEM", reason="手动撮合")

    # 已产生撮合但未满额的买入订单推进为 PARTIAL_MATCHED
    for o in buys:
        if (
            o.matched_amount
            and Decimal(o.matched_amount) > 0
            and Decimal(o.total_amount) - Decimal(o.matched_amount) > 0
            and o.status == OrderStatus.WAITING_MATCH
        ):
            await transition(db, o, OrderStatus.PARTIAL_MATCHED, "SYSTEM", reason="手动撮合")

    # 已全额撮合的买入订单结算完成
    for o in buys:
        if Decimal(o.total_amount) - Decimal(o.matched_amount) <= 0 and o.status in (
            OrderStatus.WAITING_MATCH,
            OrderStatus.PARTIAL_MATCHED,
        ):
            await _settle_and_complete(db, o)
            result["buy_orders"] += 1

    # 统计完全撮合且已结算的卖出订单
    for sell in sells:
        if Decimal(sell.available_amount) - sell.matched_amount <= 0:
            so = await db.get(Order, sell.order_id)
            if so and so.status == OrderStatus.COMPLETED:
                result["sell_orders"] += 1

    await db.flush()
    return result


async def scan_pending_orders() -> dict[str, int]:
    """自动撮合：扫描 WAITING_MATCH / PARTIAL_MATCHED 订单重新撮合（管理后台触发）。"""
    from app.database import SessionLocal

    job = None
    result: dict[str, int] = {"processed": 0, "matched": 0, "failed": 0}
    async with SessionLocal() as db:
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        job = MatchingJob(job_id=job_id, status="RUNNING")
        db.add(job)
        await db.flush()

        stmt = select(Order.id).where(
            Order.status.in_([OrderStatus.WAITING_MATCH, OrderStatus.PARTIAL_MATCHED]),
            Order.order_type == OrderType.BUY,
        )
        order_ids = list((await db.execute(stmt)).scalars().all())
        await db.commit()

        for oid in order_ids:
            async with SessionLocal() as sub_db:
                try:
                    matched = await match_order(sub_db, oid)
                    await sub_db.commit()
                    result["processed"] += 1
                    if matched:
                        result["matched"] += 1
                except Exception as exc:  # noqa: BLE001
                    await sub_db.rollback()
                    result["failed"] += 1
                    logger.exception("扫描撮合失败 order=%s: %s", oid, exc)

        if job:
            async with SessionLocal() as end_db:
                j = await end_db.get(MatchingJob, job.id)
                if j:
                    j.end_time = datetime.now()
                    j.processed_count = result["processed"]
                    j.success_count = result["matched"]
                    j.failed_count = result["failed"]
                    j.status = "COMPLETED" if result["failed"] == 0 else "PARTIAL"
                    await end_db.commit()
    return result
