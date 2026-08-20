"""订单撮合集成测试：手动批量撮合 + 后台自动撮合（1 买对多卖 / 1 卖对多买）。"""

from __future__ import annotations

from decimal import Decimal

from tests.conftest import auth_header, register_user


def _admin_token(client) -> str:
    resp = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _credit(client, admin_token: str, user_id: int, amount: float) -> None:
    resp = client.post(
        f"/api/v1/admin/users/{user_id}/adjust",
        headers=auth_header(admin_token),
        json={"amount": amount, "reason": "测试入金"},
    )
    assert resp.status_code == 200, resp.text


def _my_id(client, token: str) -> int:
    resp = client.get("/api/v1/auth/me", headers=auth_header(token))
    return resp.json()["data"]["id"]


def _create_sell(client, token: str, amount: int) -> int:
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "SELL", "amount": amount}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "WAITING_MATCH"
    return resp.json()["data"]["id"]


def _create_buy_paid(client, admin_token: str, amount: int, phone: str) -> tuple[str, int]:
    token = register_user(client, phone)
    uid = _my_id(client, token)
    _credit(client, admin_token, uid, amount * 10)
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "BUY", "amount": amount}
    )
    assert resp.status_code == 200, resp.text
    order_id = resp.json()["data"]["id"]
    resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return token, order_id


def test_auto_match_one_buy_multi_sell(client):
    """后台自动撮合：1 个买入订单由多个卖出订单共同撮合（BUY 10000 = 2000+3000+5000）。"""
    admin_token = _admin_token(client)

    seller_tokens = []
    for i, amount in enumerate([2000, 3000, 5000]):
        token = register_user(client, f"1381000001{i}")
        _create_sell(client, token, amount)
        seller_tokens.append(token)

    buyer_token, buy_id = _create_buy_paid(client, admin_token, 10000, "13810000199")

    # 关闭实时撮合：支付后停留在 WAITING_MATCH，未产生撮合
    detail = client.get(f"/api/v1/orders/{buy_id}", headers=auth_header(buyer_token)).json()["data"]
    assert detail["status"] == "WAITING_MATCH"
    assert detail["matched_amount"] == "0.00"

    # 管理后台触发自动撮合
    resp = client.post("/api/v1/admin/matching/auto", headers=auth_header(admin_token))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["processed"] >= 1
    assert data["matched"] >= 1

    # 买单已完成且满额撮合
    detail = client.get(f"/api/v1/orders/{buy_id}", headers=auth_header(buyer_token)).json()["data"]
    assert detail["status"] == "COMPLETED"
    assert detail["matched_amount"] == "10000.00"

    # 撮合明细 3 条
    match_data = client.get(f"/api/v1/orders/{buy_id}/match", headers=auth_header(buyer_token)).json()["data"]
    assert match_data["remaining_amount"] == "0.00"
    assert len(match_data["matches"]) == 3
    total_matched = sum(int(Decimal(m["match_amount"])) for m in match_data["matches"])
    assert total_matched == 10000

    # 买方账户：扣掉 10500，剩余 89500，无冻结
    acc = client.get("/api/v1/accounts", headers=auth_header(buyer_token)).json()["data"]
    assert acc["available_amount"] == "89500.00"
    assert acc["frozen_amount"] == "0.00"

    # 卖方各自收到结算款
    for i, token in enumerate(seller_tokens):
        acc = client.get("/api/v1/accounts", headers=auth_header(token)).json()["data"]
        assert acc["available_amount"] == f"{[2000, 3000, 5000][i]}.00"


def test_manual_batch_match_partial(client):
    """手动批量撮合：BUY 10000 只勾选 4000 卖单 → 部分撮合。"""
    admin_token = _admin_token(client)
    seller_token = register_user(client, "13800000021")
    sell_id = _create_sell(client, seller_token, 4000)

    buyer_token, buy_id = _create_buy_paid(client, admin_token, 10000, "13800000022")

    resp = client.post(
        "/api/v1/admin/matching/manual",
        headers=auth_header(admin_token),
        json={"buy_order_ids": [buy_id], "sell_order_ids": [sell_id]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["matched"] == 1
    assert data["buy_orders"] == 0  # 未满额不结算

    # 买方停留在 PARTIAL_MATCHED
    detail = client.get(f"/api/v1/orders/{buy_id}", headers=auth_header(buyer_token)).json()["data"]
    assert detail["status"] == "PARTIAL_MATCHED"
    assert detail["matched_amount"] == "4000.00"

    match_data = client.get(f"/api/v1/orders/{buy_id}/match", headers=auth_header(buyer_token)).json()["data"]
    assert match_data["remaining_amount"] == "6000.00"

    # 卖方订单推进为 PARTIAL_MATCHED
    sell_detail = client.get(f"/api/v1/orders/{sell_id}", headers=auth_header(seller_token)).json()["data"]
    assert sell_detail["status"] == "PARTIAL_MATCHED"


def test_manual_batch_one_sell_multi_buy(client):
    """手动批量撮合：1 个卖出订单被多个买入订单共同撮合（SELL 10000 = 3000+7000）。"""
    admin_token = _admin_token(client)
    seller_token = register_user(client, "13800000030")
    sell_id = _create_sell(client, seller_token, 10000)

    buyer1, buy1 = _create_buy_paid(client, admin_token, 3000, "13800000031")
    buyer2, buy2 = _create_buy_paid(client, admin_token, 7000, "13800000032")

    resp = client.post(
        "/api/v1/admin/matching/manual",
        headers=auth_header(admin_token),
        json={"buy_order_ids": [buy1, buy2], "sell_order_ids": [sell_id]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["matched"] == 2
    assert data["buy_orders"] == 2
    assert data["sell_orders"] == 1

    # 两个买单均完成
    for token, buy_id in [(buyer1, buy1), (buyer2, buy2)]:
        detail = client.get(f"/api/v1/orders/{buy_id}", headers=auth_header(token)).json()["data"]
        assert detail["status"] == "COMPLETED"

    # 卖方订单完成并收到全额结算款
    sell_detail = client.get(f"/api/v1/orders/{sell_id}", headers=auth_header(seller_token)).json()["data"]
    assert sell_detail["status"] == "COMPLETED"
    acc = client.get("/api/v1/accounts", headers=auth_header(seller_token)).json()["data"]
    assert acc["available_amount"] == "10000.00"


def test_manual_batch_requires_both_sides(client):
    """手动批量撮合：必须同时勾选买入与卖出。"""
    admin = _admin_token(client)
    resp = client.post(
        "/api/v1/admin/matching/manual",
        headers=auth_header(admin),
        json={"buy_order_ids": [1], "sell_order_ids": []},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "MATCH_PARAM_INVALID"


def test_manual_batch_skips_self_match(client):
    """手动批量撮合：同一用户不参与自撮合。"""
    admin = _admin_token(client)
    token = register_user(client, "13800000040")
    uid = _my_id(client, token)
    _credit(client, admin, uid, 10000)

    sell_id = _create_sell(client, token, 1000)
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "BUY", "amount": 1000}
    )
    buy_id = resp.json()["data"]["id"]
    client.post(f"/api/v1/orders/{buy_id}/pay", headers=auth_header(token))

    resp = client.post(
        "/api/v1/admin/matching/manual",
        headers=auth_header(admin),
        json={"buy_order_ids": [buy_id], "sell_order_ids": [sell_id]},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["matched"] == 0


def test_manual_batch_no_auto_after_pay(client):
    """支付后不会实时撮合（撮合仅后台触发）。"""
    admin_token = _admin_token(client)
    seller_token = register_user(client, "13800000050")
    _create_sell(client, seller_token, 1000)

    buyer_token, buy_id = _create_buy_paid(client, admin_token, 1000, "13800000051")
    detail = client.get(f"/api/v1/orders/{buy_id}", headers=auth_header(buyer_token)).json()["data"]
    assert detail["status"] == "WAITING_MATCH"
    assert detail["matched_amount"] == "0.00"

    acc = client.get("/api/v1/accounts", headers=auth_header(buyer_token)).json()["data"]
    assert acc["frozen_amount"] == "1050.00"


def test_aid_order_cannot_cancel(client):
    """援助订单（BUY/SELL）禁止取消。"""
    admin_token = _admin_token(client)
    buyer_token = register_user(client, "13800000032")
    buyer_id = _my_id(client, buyer_token)
    _credit(client, admin_token, buyer_id, 5000)

    # BUY
    resp = client.post(
        "/api/v1/orders",
        headers=auth_header(buyer_token),
        json={"order_type": "BUY", "amount": 1000},
    )
    buy_id = resp.json()["data"]["id"]
    resp = client.post(f"/api/v1/orders/{buy_id}/cancel", headers=auth_header(buyer_token))
    assert resp.status_code == 400
    assert resp.json()["code"] == "ORDER_CANNOT_CANCEL"

    # SELL
    resp = client.post(
        "/api/v1/orders",
        headers=auth_header(buyer_token),
        json={"order_type": "SELL", "amount": 1000},
    )
    sell_id = resp.json()["data"]["id"]
    resp = client.post(f"/api/v1/orders/{sell_id}/cancel", headers=auth_header(buyer_token))
    assert resp.status_code == 400
    assert resp.json()["code"] == "ORDER_CANNOT_CANCEL"


def test_duplicate_pay_rejected(client):
    """已支付订单不允许重复支付。"""
    admin_token = _admin_token(client)
    buyer_token = register_user(client, "13800000041")
    buyer_id = _my_id(client, buyer_token)
    _credit(client, admin_token, buyer_id, 5000)

    resp = client.post(
        "/api/v1/orders",
        headers=auth_header(buyer_token),
        json={"order_type": "BUY", "amount": 1000},
    )
    order_id = resp.json()["data"]["id"]
    first = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_header(buyer_token))
    assert first.status_code == 200
    second = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_header(buyer_token))
    assert second.status_code == 400
    assert second.json()["code"] == "ORDER_INVALID_STATUS"
