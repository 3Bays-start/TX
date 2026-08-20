"""提现集成测试：申请 → 审核 → 完成。"""

from __future__ import annotations

from tests.conftest import auth_header, register_user


def test_withdrawal_below_min_rejected(client):
    token = register_user(client, "13800000205")
    resp = client.post(
        "/api/v1/withdrawals",
        headers=auth_header(token),
        json={"amount": 10, "usdt_address": "TXJabcXYZ1234567890abcdefghijklmnop"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "WITHDRAWAL_INVALID"


def test_withdrawal_full_flow(client):
    token = register_user(client, "13800000202")
    uid = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]
    admin_token = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    ).json()["data"]["access_token"]

    client.post(f"/api/v1/admin/users/{uid}/adjust", headers=auth_header(admin_token), json={"amount": 5000, "reason": "入金"})

    # 申请提现
    resp = client.post(
        "/api/v1/withdrawals",
        headers=auth_header(token),
        json={"amount": 1000, "usdt_address": "TXJabcXYZ1234567890abcdefghijklmnop"},
    )
    assert resp.status_code == 200, resp.text
    wd_no = resp.json()["data"]["withdrawal_no"]

    # 余额已冻结
    acc = client.get("/api/v1/accounts", headers=auth_header(token)).json()["data"]
    assert acc["frozen_amount"] == "1000.00"

    # 审核通过 + 完成
    resp = client.get("/api/v1/withdrawals", headers=auth_header(token)).json()["data"]
    wd = next(w for w in resp["items"] if w["withdrawal_no"] == wd_no)
    assert wd["status"] == "PENDING"

    resp = client.post(
        f"/api/v1/admin/withdrawals/{wd['id']}/review",
        headers=auth_header(admin_token),
        json={"approve": True, "reason": "风控通过"},
    )
    assert resp.status_code == 200

    resp = client.post(
        f"/api/v1/admin/withdrawals/{wd['id']}/complete",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200

    # 完成：冻结清零，可用 = 5000 - 1000
    acc = client.get("/api/v1/accounts", headers=auth_header(token)).json()["data"]
    assert acc["frozen_amount"] == "0.00"
    assert acc["available_amount"] == "4000.00"

    # 流水含 WITHDRAWAL
    txs = client.get("/api/v1/accounts/transactions", headers=auth_header(token)).json()["data"]
    assert any(t["business_type"] == "WITHDRAWAL" for t in txs["items"])
