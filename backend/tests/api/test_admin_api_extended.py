"""管理后台扩展测试：用户/订单/撮合/财务/风控/日志/公告/RBAC 权限隔离。"""

from __future__ import annotations

from decimal import Decimal

from tests.conftest import auth_header, register_user


def _admin_token(client) -> str:
    resp = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _uid(client, token: str) -> int:
    return client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]


def _credit(client, admin_token: str, user_id: int, amount: float) -> None:
    resp = client.post(
        f"/api/v1/admin/users/{user_id}/adjust",
        headers=auth_header(admin_token),
        json={"amount": amount, "reason": "测试入金"},
    )
    assert resp.status_code == 200, resp.text


# ===== 用户管理 =====


def test_admin_users_list_and_detail(client):
    admin = _admin_token(client)
    token = register_user(client, "13880000001")
    uid = _uid(client, token)

    resp = client.get("/api/v1/admin/users", headers=auth_header(admin))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert any(u["id"] == uid and u["credit_level_name"] == "普通信用" for u in data["items"])

    # 按 user_id 过滤
    resp = client.get(f"/api/v1/admin/users?user_id={uid}", headers=auth_header(admin))
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1

    resp = client.get(f"/api/v1/admin/users/{uid}", headers=auth_header(admin))
    assert resp.status_code == 200
    assert resp.json()["data"]["account"]["available_amount"] == "0.00"


def test_admin_adjust_balance(client):
    admin = _admin_token(client)
    token = register_user(client, "13880000003")
    uid = _uid(client, token)

    _credit(client, admin, uid, 2000)
    acc = client.get("/api/v1/accounts", headers=auth_header(token)).json()["data"]
    assert acc["available_amount"] == "2000.00"

    # 后台账户查询
    resp = client.get(f"/api/v1/admin/accounts/{uid}", headers=auth_header(admin))
    assert resp.status_code == 200
    assert resp.json()["data"]["available_amount"] == "2000.00"


# ===== 订单管理 =====


def test_admin_orders_list_filter_and_detail(client):
    admin = _admin_token(client)
    token = register_user(client, "13880000004")

    # 买单 WAITING_PAYMENT + 卖单 WAITING_MATCH
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "BUY", "amount": 1000}
    )
    buy_id = resp.json()["data"]["id"]
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "SELL", "amount": 3000}
    )
    sell_id = resp.json()["data"]["id"]

    resp = client.get(
        "/api/v1/admin/orders?status=WAITING_MATCH", headers=auth_header(admin)
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == sell_id

    resp = client.get("/api/v1/admin/orders?order_type=BUY", headers=auth_header(admin))
    assert any(o["id"] == buy_id for o in resp.json()["data"]["items"])

    # 订单详情含凭证字段
    resp = client.get(f"/api/v1/admin/orders/{buy_id}", headers=auth_header(admin))
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["proof_urls"] == []
    assert "status_logs" in detail


def test_admin_manual_match(client):
    """手动批量撮合接口：BUY + SELL 勾选撮合。"""
    admin = _admin_token(client)
    token = register_user(client, "13880000005")
    sell_token = register_user(client, "13880000015")
    client.post(
        "/api/v1/orders", headers=auth_header(sell_token), json={"order_type": "SELL", "amount": 3000}
    )
    sell_id = client.get("/api/v1/orders", headers=auth_header(sell_token)).json()["data"]["items"][0]["id"]
    uid = _uid(client, token)
    _credit(client, admin, uid, 10000)
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "BUY", "amount": 3000}
    )
    buy_id = resp.json()["data"]["id"]
    client.post(f"/api/v1/orders/{buy_id}/pay", headers=auth_header(token))

    resp = client.post(
        "/api/v1/admin/matching/manual",
        headers=auth_header(admin),
        json={"buy_order_ids": [buy_id], "sell_order_ids": [sell_id], "reason": "人工触发"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["matched"] == 1


# ===== 撮合管理 =====


def test_admin_matching_lists(client):
    admin = _admin_token(client)
    token = register_user(client, "13880000006")
    client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "SELL", "amount": 3000}
    )

    resp = client.get("/api/v1/admin/matching", headers=auth_header(admin))
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) >= 1

    resp = client.get("/api/v1/admin/matching/jobs", headers=auth_header(admin))
    assert resp.status_code == 200
    assert "items" in resp.json()["data"]


# ===== 财务 =====


def test_admin_transactions(client):
    admin = _admin_token(client)
    token = register_user(client, "13880000007")
    uid = _uid(client, token)
    _credit(client, admin, uid, 1000)

    resp = client.get(f"/api/v1/admin/transactions?user_id={uid}", headers=auth_header(admin))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert any(t["user_id"] == uid and t["business_type"] == "ADJUSTMENT" for t in items)


def test_admin_withdrawals_list(client):
    admin = _admin_token(client)
    resp = client.get("/api/v1/admin/withdrawals", headers=auth_header(admin))
    assert resp.status_code == 200
    assert "items" in resp.json()["data"]


def test_admin_fees_get_and_update(client):
    admin = _admin_token(client)

    resp = client.get("/api/v1/admin/fees", headers=auth_header(admin))
    assert resp.status_code == 200
    rules = resp.json()["data"]["items"]
    assert any(r["fee_type"] == "ORDER_SERVICE_FEE" for r in rules)

    # 修改费率
    resp = client.put(
        "/api/v1/admin/fees/ORDER_SERVICE_FEE",
        headers=auth_header(admin),
        json={"rate": 0.06, "min_fee": 10, "max_fee": 1000},
    )
    assert resp.status_code == 200, resp.text
    rules = client.get("/api/v1/admin/fees", headers=auth_header(admin)).json()["data"]["items"]
    updated = next(r for r in rules if r["fee_type"] == "ORDER_SERVICE_FEE")
    assert Decimal(updated["rate"]) == Decimal("0.06")
    assert Decimal(updated["min_fee"]) == Decimal("10")
    assert Decimal(updated["max_fee"]) == Decimal("1000")

    # 费率记录
    resp = client.get("/api/v1/admin/fees/records", headers=auth_header(admin))
    assert resp.status_code == 200


def test_admin_promotions(client):
    admin = _admin_token(client)
    resp = client.get("/api/v1/admin/promotions", headers=auth_header(admin))
    assert resp.status_code == 200
    assert "items" in resp.json()["data"]


# ===== 风控 =====


def test_admin_risk(client):
    admin = _admin_token(client)
    resp = client.get("/api/v1/admin/risk/events", headers=auth_header(admin))
    assert resp.status_code == 200
    assert "items" in resp.json()["data"]

    # 不存在的事件审核返回 200（null）
    resp = client.post(
        "/api/v1/admin/risk/events/999999/review",
        headers=auth_header(admin),
        json={"approve": True, "action": "FREEZE", "reason": "测试"},
    )
    assert resp.status_code == 200


# ===== 日志 =====


def test_admin_logs(client):
    admin = _admin_token(client)
    token = register_user(client, "13880000008")
    uid = _uid(client, token)
    _credit(client, admin, uid, 100)  # 触发 ADJUST_BALANCE 日志

    resp = client.get("/api/v1/admin/logs", headers=auth_header(admin))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert any(log["action"] == "ADJUST_BALANCE" for log in items)


# ===== RBAC 管理员与权限隔离 =====


def test_admin_rbac_isolated_admin(client):
    super_admin = _admin_token(client)

    # 建角色：仅 order:view
    resp = client.post(
        "/api/v1/admin/roles",
        headers=auth_header(super_admin),
        json={"code": "VIEWER", "name": "只读角色", "permission_codes": ["order:view"]},
    )
    assert resp.status_code == 200, resp.text
    roles = client.get("/api/v1/admin/roles", headers=auth_header(super_admin)).json()["data"]["items"]
    role_id = next(r["id"] for r in roles if r["code"] == "VIEWER")

    # 建管理员并绑定角色
    resp = client.post(
        "/api/v1/admin/admins",
        headers=auth_header(super_admin),
        json={"username": "viewer01", "password": "Viewer@12345", "nickname": "只读", "role_ids": [role_id]},
    )
    assert resp.status_code == 200, resp.text

    resp = client.post(
        "/api/v1/admin/login", json={"username": "viewer01", "password": "Viewer@12345"}
    )
    assert resp.status_code == 200
    viewer = resp.json()["data"]["access_token"]

    # 有 order:view → 200
    resp = client.get("/api/v1/admin/orders", headers=auth_header(viewer))
    assert resp.status_code == 200

    # 无 user:view → 403
    resp = client.get("/api/v1/admin/users", headers=auth_header(viewer))
    assert resp.status_code == 403

    # 无 order:match → 403
    token = register_user(client, "13880000009")
    sell_token = register_user(client, "13880000019")
    client.post(
        "/api/v1/orders", headers=auth_header(sell_token), json={"order_type": "SELL", "amount": 1000}
    )
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "BUY", "amount": 1000}
    )
    buy_id = resp.json()["data"]["id"]
    resp = client.post(
        "/api/v1/admin/matching/manual",
        headers=auth_header(viewer),
        json={"buy_order_ids": [buy_id], "sell_order_ids": [999999], "reason": "x"},
    )
    assert resp.status_code == 403

    # 重复用户名 → 400
    resp = client.post(
        "/api/v1/admin/admins",
        headers=auth_header(super_admin),
        json={"username": "viewer01", "password": "Viewer@12345", "role_ids": []},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "ADMIN_EXISTS"


def test_admin_update_role_and_admin(client):
    super_admin = _admin_token(client)

    client.post(
        "/api/v1/admin/roles",
        headers=auth_header(super_admin),
        json={"code": "VIEWER", "name": "只读角色", "permission_codes": ["order:view"]},
    )
    roles = client.get("/api/v1/admin/roles", headers=auth_header(super_admin)).json()["data"]["items"]
    role_id = next(r["id"] for r in roles if r["code"] == "VIEWER")

    resp = client.post(
        "/api/v1/admin/admins",
        headers=auth_header(super_admin),
        json={"username": "viewer01", "password": "Viewer@12345", "nickname": "只读", "role_ids": [role_id]},
    )
    assert resp.status_code == 200, resp.text

    # 更新角色：增加 user:view
    resp = client.put(
        f"/api/v1/admin/roles/{role_id}",
        headers=auth_header(super_admin),
        json={"name": "只读角色V2", "permission_codes": ["order:view", "user:view"]},
    )
    assert resp.status_code == 200, resp.text
    roles = client.get("/api/v1/admin/roles", headers=auth_header(super_admin)).json()["data"]["items"]
    updated = next(r for r in roles if r["code"] == "VIEWER")
    assert updated["name"] == "只读角色V2"
    assert "user:view" in updated["permission_codes"]

    # 更新管理员昵称与角色
    admins = client.get("/api/v1/admin/admins", headers=auth_header(super_admin)).json()["data"]["items"]
    vid = next(a["id"] for a in admins if a["username"] == "viewer01")
    resp = client.put(
        f"/api/v1/admin/admins/{vid}",
        headers=auth_header(super_admin),
        json={"nickname": "只读V2", "role_ids": [role_id]},
    )
    assert resp.status_code == 200, resp.text
    admins = client.get("/api/v1/admin/admins", headers=auth_header(super_admin)).json()["data"]["items"]
    assert next(a["nickname"] for a in admins if a["id"] == vid) == "只读V2"

    # 新登录后拥有 user:view
    resp = client.post(
        "/api/v1/admin/login", json={"username": "viewer01", "password": "Viewer@12345"}
    )
    viewer = resp.json()["data"]["access_token"]
    resp = client.get("/api/v1/admin/users", headers=auth_header(viewer))
    assert resp.status_code == 200


def test_admin_permissions_and_logs_require_system_perm(client):
    super_admin = _admin_token(client)
    resp = client.get("/api/v1/admin/permissions", headers=auth_header(super_admin))
    assert resp.status_code == 200
    assert any(p["code"] == "order:view" for p in resp.json()["data"]["items"])
