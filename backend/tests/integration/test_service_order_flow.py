"""BUY 订单支付流程（G-06）与用户端订单列表（G-07）。"""

from __future__ import annotations

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


def test_buy_order_full_flow(client):
    """BUY 订单：下单→支付→后台自动撮合→完成，无 FROZEN_INSUFFICIENT。"""
    admin_token = _admin_token(client)

    # 卖方挂卖单
    seller_token = register_user(client, "13840000001")
    client.post(
        "/api/v1/orders",
        headers=auth_header(seller_token),
        json={"order_type": "SELL", "amount": 1000},
    )

    # 买方
    buyer_token = register_user(client, "13840000002")
    buyer_id = client.get("/api/v1/auth/me", headers=auth_header(buyer_token)).json()["data"]["id"]
    _credit(client, admin_token, buyer_id, 5000)

    resp = client.post(
        "/api/v1/orders",
        headers=auth_header(buyer_token),
        json={"order_type": "BUY", "amount": 1000, "remark": "援助服务"},
    )
    assert resp.status_code == 200, resp.text
    order = resp.json()["data"]
    assert order["order_type"] == "BUY"
    assert order["status"] == "WAITING_PAYMENT"
    assert order["service_fee"] == "50.00"
    assert order["payable_amount"] == "1050.00"
    order_id = order["id"]

    # 支付：冻结→PAID→WAITING_MATCH（不实时撮合）
    resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_header(buyer_token))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "WAITING_MATCH"
    assert data["matched_amount"] == "0.00"

    # 后台自动撮合
    resp = client.post("/api/v1/admin/matching/auto", headers=auth_header(admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["matched"] >= 1

    data = client.get(f"/api/v1/orders/{order_id}", headers=auth_header(buyer_token)).json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["matched_amount"] == "1000.00"

    # 状态日志完整路径
    logs = client.get(f"/api/v1/orders/{order_id}", headers=auth_header(buyer_token)).json()["data"]["status_logs"]
    transitions = [(log["from_status"], log["to_status"]) for log in logs]
    assert ("WAITING_PAYMENT", "PAID") in transitions
    assert ("PAID", "WAITING_MATCH") in transitions
    assert ("FULL_MATCHED", "PROCESSING") in transitions
    assert ("PROCESSING", "COMPLETED") in transitions

    # 余额正确，无负冻结
    acc = client.get("/api/v1/accounts", headers=auth_header(buyer_token)).json()["data"]
    assert acc["available_amount"] == "3950.00"
    assert acc["frozen_amount"] == "0.00"

    # 撮合详情
    match_data = client.get(f"/api/v1/orders/{order_id}/match", headers=auth_header(buyer_token)).json()["data"]
    assert match_data["remaining_amount"] == "0.00"
    assert match_data["status"] == "COMPLETED"


def test_order_list_filter_and_pagination(client):
    """用户端订单列表：状态筛选 + 分页。"""
    admin_token = _admin_token(client)
    token = register_user(client, "13840000003")
    uid = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]
    _credit(client, admin_token, uid, 10000)

    # 2 个 WAITING_PAYMENT + 1 个 WAITING_MATCH
    for _ in range(2):
        client.post("/api/v1/orders", headers=auth_header(token), json={"order_type": "BUY", "amount": 1000})
    client.post("/api/v1/orders", headers=auth_header(token), json={"order_type": "SELL", "amount": 2000})

    resp = client.get("/api/v1/orders?status=WAITING_PAYMENT", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 2
    assert all(o["status"] == "WAITING_PAYMENT" for o in data["items"])

    # 分页 page_size=2 → 第 2 页只剩 1 条
    resp = client.get("/api/v1/orders?page=2&page_size=2", headers=auth_header(token))
    data = resp.json()["data"]
    assert data["total"] == 3
    assert len(data["items"]) == 1

    # 排序：新单在前
    resp = client.get("/api/v1/orders", headers=auth_header(token))
    items = resp.json()["data"]["items"]
    assert items[0]["order_type"] == "SELL"


def test_order_list_scoped_to_owner(client):
    """用户端订单列表只返回本人订单。"""
    admin_token = _admin_token(client)
    a = register_user(client, "13840000004")
    b = register_user(client, "13840000005")
    client.post("/api/v1/orders", headers=auth_header(a), json={"order_type": "SELL", "amount": 1000})
    uid_b = client.get("/api/v1/auth/me", headers=auth_header(b)).json()["data"]["id"]
    _credit(client, admin_token, uid_b, 1000)

    data = client.get("/api/v1/orders", headers=auth_header(b)).json()["data"]
    assert data["total"] == 0
