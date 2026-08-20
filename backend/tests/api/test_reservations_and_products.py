"""预约（G-10）接口测试（商品功能已移除）。"""

from __future__ import annotations

from tests.conftest import auth_header, register_user


def _admin_token(client) -> str:
    resp = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def test_reservation_flow(client):
    token = register_user(client, "13860000001")
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "SELL", "amount": 1000}
    )
    order_id = resp.json()["data"]["id"]

    # 创建预约
    resp = client.post(
        "/api/v1/reservations", headers=auth_header(token), json={"order_id": order_id}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "WAITING"
    assert data["order_id"] == order_id

    # 重复预约返回同一预约
    resp = client.post(
        "/api/v1/reservations", headers=auth_header(token), json={"order_id": order_id}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == data["id"]

    # 列表
    resp = client.get("/api/v1/reservations", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1
    assert resp.json()["data"]["items"][0]["order_id"] == order_id

    # 撮合状态查询
    resp = client.get(
        f"/api/v1/reservations/matching/status/{order_id}", headers=auth_header(token)
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "WAITING_MATCH"


def test_reservation_rejects_unknown_order(client):
    token = register_user(client, "13860000002")
    resp = client.post(
        "/api/v1/reservations", headers=auth_header(token), json={"order_id": 999999}
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "ORDER_NOT_FOUND"


def test_reservation_status_not_available(client):
    admin = _admin_token(client)
    seller_token = register_user(client, "13860000003")
    client.post(
        "/api/v1/orders", headers=auth_header(seller_token), json={"order_type": "SELL", "amount": 1000}
    )
    buyer_token = register_user(client, "13860000004")
    uid = client.get("/api/v1/auth/me", headers=auth_header(buyer_token)).json()["data"]["id"]
    client.post(f"/api/v1/admin/users/{uid}/adjust", headers=auth_header(admin), json={"amount": 5000, "reason": "入金"})
    resp = client.post(
        "/api/v1/orders", headers=auth_header(buyer_token), json={"order_type": "BUY", "amount": 1000}
    )
    order_id = resp.json()["data"]["id"]
    client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_header(buyer_token))
    sell_id = client.get("/api/v1/orders", headers=auth_header(seller_token)).json()["data"]["items"][0]["id"]

    # 撮合完成后的订单不可预约
    client.post(
        "/api/v1/admin/matching/manual",
        headers=auth_header(admin),
        json={"buy_order_ids": [order_id], "sell_order_ids": [sell_id]},
    )

    resp = client.post(
        "/api/v1/reservations", headers=auth_header(buyer_token), json={"order_id": order_id}
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "ORDER_INVALID_STATUS"


def test_product_endpoints_removed(client):
    """商品接口已移除（取消商品功能）。"""
    resp = client.get("/api/v1/products")
    assert resp.status_code == 404
