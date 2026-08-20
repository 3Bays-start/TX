"""并发撮合测试：多个 Worker 同时处理一个订单，不超额、不重复、不产生负余额。"""

from __future__ import annotations

import asyncio

from sqlalchemy import select


def test_concurrent_matching_no_overflow(client):
    """直接构造数据 + 并发调用 match_order，验证撮合不超额不重复。"""
    from decimal import Decimal

    from app.core.security import hash_password
    from app.database import SessionLocal
    from app.models.account import Account
    from app.models.matching import MatchOrder
    from app.models.order import BuyOrder, Order, SellOrder
    from app.models.user import User
    from app.services import account_service, matching_service

    async def _run():
        async with SessionLocal() as db:
            # 买方
            buyer = User(phone="13900000000", password_hash=hash_password("Passw0rd"), nickname="buyer")
            db.add(buyer)
            await db.flush()
            await account_service.ensure_account(db, buyer.id)
            # 买方入金
            await account_service.credit(db, buyer.id, Decimal("20000"), "ADJUSTMENT", None, "并发测试入金")
            await db.commit()

            # 20 个卖方，每个 1000 → 共 20000
            seller_ids = []
            for i in range(20):
                seller = User(phone=f"1390000001{i}", password_hash=hash_password("Passw0rd"), nickname=f"s{i}")
                db.add(seller)
                await db.flush()
                await account_service.ensure_account(db, seller.id)
                sell = Order(
                    order_no=f"SEL{i}",
                    user_id=seller.id,
                    order_type="SELL",
                    product_name="服务",
                    total_amount=Decimal("1000"),
                    payable_amount=Decimal("1000"),
                    status="WAITING_MATCH",
                )
                db.add(sell)
                await db.flush()
                db.add(SellOrder(order_id=sell.id, user_id=seller.id, available_amount=Decimal("1000")))
                seller_ids.append(sell.id)
            await db.commit()

            # 买方订单 10000，已支付冻结 10500
            buy = Order(
                order_no="BUY1",
                user_id=buyer.id,
                order_type="BUY",
                product_name="服务",
                total_amount=Decimal("10000"),
                service_fee=Decimal("500"),
                payable_amount=Decimal("10500"),
                status="WAITING_MATCH",
            )
            db.add(buy)
            await db.flush()
            db.add(BuyOrder(order_id=buy.id, user_id=buyer.id, target_amount=Decimal("10000")))
            await account_service.freeze(db, buyer.id, Decimal("10500"), "ORDER_PAYMENT", buy.id, "并发测试支付")
            await db.commit()
            buy_id = buy.id

        # 并发撮合：20 个 worker 同时处理同一订单
        async def worker(_):
            async with SessionLocal() as db:
                try:
                    await matching_service.match_order(db, buy_id)
                    await db.commit()
                except Exception:
                    await db.rollback()

        await asyncio.gather(*[worker(i) for i in range(20)])

        # 校验
        async with SessionLocal() as db:
            order = await db.get(Order, buy_id)
            matches = list((await db.execute(select(MatchOrder).where(MatchOrder.parent_order_id == buy_id))).scalars().all())
            total_match = sum(m.match_amount for m in matches)
            buyer_acc = await db.scalar(select(Account).where(Account.user_id == order.user_id))
            sell_matches = list((await db.execute(select(MatchOrder).where(MatchOrder.parent_order_id == buy_id))).scalars().all())
            pairs = [(m.seller_order_id, m.match_amount) for m in sell_matches]
            assert len(pairs) == len(set(m[0] for m in pairs)), "同一卖方订单被重复撮合"

            # 核心约束
            assert total_match == Decimal("10000.00"), f"撮合总额 {total_match} != 10000"
            assert total_match <= order.total_amount, "撮合超额"
            assert order.matched_amount == Decimal("10000.00")
            assert order.status == "COMPLETED"
            assert buyer_acc.frozen_amount == Decimal("0"), "买方冻结未清"
            assert buyer_acc.available_amount == Decimal("9500.00"), "买方余额错误"

            # 卖方收款总额 = 10000
            seller_sum = 0
            for m in sell_matches:
                sa = await db.scalar(select(Account).where(Account.user_id == m.seller_user_id))
                seller_sum += sa.available_amount
            assert seller_sum == Decimal("10000.00"), f"卖方合计 {seller_sum} != 10000"

    asyncio.run(_run())
