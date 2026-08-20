"""提现边界测试：日限额（G-01）与并发防双花（G-02）。"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from tests.conftest import auth_header, register_user

ADDR = "TXJabcXYZ1234567890abcdefghijklmnop"


def _admin_token(client) -> str:
    resp = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def test_withdrawal_single_amount_over_limit(client):
    """单笔提现超过日限额上限被拒绝。"""
    admin = _admin_token(client)
    token = register_user(client, "13830000001")
    uid = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]
    client.post(f"/api/v1/admin/users/{uid}/adjust", headers=auth_header(admin), json={"amount": 100000, "reason": "入金"})

    resp = client.post("/api/v1/withdrawals", headers=auth_header(token), json={"amount": 50001, "usdt_address": ADDR})
    assert resp.status_code == 400
    assert resp.json()["code"] == "WITHDRAWAL_INVALID"
    assert "单笔提现不能超过" in resp.json()["message"]


def test_withdrawal_daily_limit_reached(client):
    """当日累计达到 50000 后继续申请被拒绝。"""
    admin = _admin_token(client)
    token = register_user(client, "13830000002")
    uid = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]
    client.post(f"/api/v1/admin/users/{uid}/adjust", headers=auth_header(admin), json={"amount": 100000, "reason": "入金"})

    # 第一笔 50000（等于限额，允许）
    resp = client.post("/api/v1/withdrawals", headers=auth_header(token), json={"amount": 50000, "usdt_address": ADDR})
    assert resp.status_code == 200, resp.text

    # 第二笔 100 → 当日累计 50100 > 50000
    resp = client.post("/api/v1/withdrawals", headers=auth_header(token), json={"amount": 100, "usdt_address": ADDR})
    assert resp.status_code == 400
    assert resp.json()["code"] == "WITHDRAWAL_INVALID"
    assert "限额" in resp.json()["message"]


def test_withdrawal_concurrent_review_no_double_spend(client):
    """同一 PENDING 提现并发审核：不允许出现重复出账/负冻结。"""
    from decimal import Decimal

    from app.database import SessionLocal
    from app.models.account import Account
    from app.models.withdrawal import WithdrawalOrder
    from app.services import withdrawal_service

    admin = _admin_token(client)
    token = register_user(client, "13830000003")
    uid = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]
    client.post(f"/api/v1/admin/users/{uid}/adjust", headers=auth_header(admin), json={"amount": 10000, "reason": "入金"})

    resp = client.post("/api/v1/withdrawals", headers=auth_header(token), json={"amount": 1000, "usdt_address": ADDR})
    assert resp.status_code == 200
    wd_no = resp.json()["data"]["withdrawal_no"]
    wd_id = next(
        w["id"]
        for w in client.get("/api/v1/withdrawals", headers=auth_header(token)).json()["data"]["items"]
        if w["withdrawal_no"] == wd_no
    )

    async def _run():
        async with SessionLocal() as db:
            async def worker(_):
                async with SessionLocal() as s:
                    try:
                        await withdrawal_service.review_withdrawal(s, wd_id, 1, True, "并发审核")
                        await withdrawal_service.complete_withdrawal(s, wd_id, 1)
                        await s.commit()
                    except Exception:
                        await s.rollback()

            await asyncio.gather(*[worker(i) for i in range(6)])

        async with SessionLocal() as db:
            order = await db.get(WithdrawalOrder, wd_id)
            acc = await db.scalar(select(Account).where(Account.user_id == uid))
            return order, acc

    order, acc = asyncio.run(_run())

    # 核心不变式：不产生负冻结、余额变化恰好一次
    assert acc.frozen_amount >= Decimal("0"), f"出现负冻结: {acc.frozen_amount}"
    assert acc.available_amount == Decimal("9000.00"), f"余额错误: {acc.available_amount}"
    assert order.status in ("APPROVED", "COMPLETED")
