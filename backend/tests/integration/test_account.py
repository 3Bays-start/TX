"""账户账务集成测试：入金/出账/冻结/流水。"""

from __future__ import annotations

from tests.conftest import auth_header, register_user


def test_credit_debit_transaction_ledger(client):
    token = register_user(client, "13800000101")
    uid = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]

    # 管理员入金
    admin = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    ).json()["data"]["access_token"]
    resp = client.post(
        f"/api/v1/admin/users/{uid}/adjust",
        headers=auth_header(admin),
        json={"amount": 1000, "reason": "测试入金"},
    )
    assert resp.status_code == 200

    acc = client.get("/api/v1/accounts", headers=auth_header(token)).json()["data"]
    assert acc["available_amount"] == "1000.00"

    # 流水应包含 ADJUSTMENT
    txs = client.get("/api/v1/accounts/transactions", headers=auth_header(token)).json()["data"]
    assert txs["total"] >= 1
    assert any(t["business_type"] == "ADJUSTMENT" for t in txs["items"])


def test_insufficient_balance(client):
    token = register_user(client, "13800000102")

    # 余额不足时支付应失败
    resp = client.post(
        "/api/v1/orders",
        headers=auth_header(token),
        json={"order_type": "BUY", "amount": 50000},
    )
    order_id = resp.json()["data"]["id"]
    resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_header(token))
    assert resp.status_code == 400
    assert resp.json()["code"] == "INSUFFICIENT_BALANCE"
