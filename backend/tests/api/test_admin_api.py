"""管理后台 API 测试：登录 / Dashboard / RBAC。"""

from __future__ import annotations

from tests.conftest import auth_header, register_user


def test_admin_login_and_me(client):
    resp = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    assert resp.json()["data"]["admin"]["is_super"] is True

    resp = client.get("/api/v1/admin/me", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["role_code"] == "SUPER_ADMIN"
    assert "user:freeze" in resp.json()["data"]["permissions"]


def test_dashboard(client):
    token = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    ).json()["data"]["access_token"]
    register_user(client, "13800000301")
    resp = client.get("/api/v1/admin/dashboard", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["user_total"] >= 1
    assert "user_growth" in data["charts"]


def test_freeze_user_requires_super(client):
    admin_token = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    ).json()["data"]["access_token"]
    token = register_user(client, "13800000302")
    uid = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]

    resp = client.post(
        f"/api/v1/admin/users/{uid}/freeze",
        headers=auth_header(admin_token),
        json={"reason": "风控冻结"},
    )
    assert resp.status_code == 200

    # 冻结后用户无法访问
    resp = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert resp.status_code == 403

    resp = client.post(
        f"/api/v1/admin/users/{uid}/unfreeze",
        headers=auth_header(admin_token),
        json={"reason": "复核通过"},
    )
    assert resp.status_code == 200
    resp = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert resp.status_code == 200


def test_admin_manage_invites(client):
    admin_token = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    ).json()["data"]["access_token"]
    resp = client.post(
        "/api/v1/admin/invites", headers=auth_header(admin_token), json={"count": 3}
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 3


def test_create_role_and_permissions(client):
    admin_token = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    ).json()["data"]["access_token"]
    perms = client.get("/api/v1/admin/permissions", headers=auth_header(admin_token)).json()["data"]["items"]
    assert any(p["code"] == "order:view" for p in perms)

    resp = client.post(
        "/api/v1/admin/roles",
        headers=auth_header(admin_token),
        json={"code": "TEST_ROLE", "name": "测试角色", "permission_codes": ["order:view", "user:view"]},
    )
    assert resp.status_code == 200
    roles = client.get("/api/v1/admin/roles", headers=auth_header(admin_token)).json()["data"]["items"]
    assert any(r["code"] == "TEST_ROLE" for r in roles)


def test_admin_endpoints_require_auth(client):
    """所有后台数据接口必须校验管理员身份，匿名访问一律 401。"""
    protected = [
        "/api/v1/admin/dashboard",
        "/api/v1/admin/users",
        "/api/v1/admin/orders",
        "/api/v1/admin/matching",
        "/api/v1/admin/matching/jobs",
        "/api/v1/admin/transactions",
        "/api/v1/admin/withdrawals",
        "/api/v1/admin/fees",
        "/api/v1/admin/fees/records",
        "/api/v1/admin/promotions",
        "/api/v1/admin/risk/events",
        "/api/v1/admin/tickets",
        "/api/v1/admin/appeals",
        "/api/v1/admin/admins",
        "/api/v1/admin/roles",
        "/api/v1/admin/permissions",
        "/api/v1/admin/logs",
        "/api/v1/admin/announcements",
    ]
    for path in protected:
        resp = client.get(path)
        assert resp.status_code in (401, 403), f"{path} 应拒绝匿名访问，实际 {resp.status_code}"

    resp = client.post("/api/v1/admin/invites", json={"count": 1})
    assert resp.status_code in (401, 403)


def test_user_token_cannot_access_admin(client):
    """普通用户令牌即使 id 与管理员撞号，也必须被拒绝（越权回归测试）。"""
    user_token = register_user(client, "13800000999")
    resp = client.get("/api/v1/admin/me", headers=auth_header(user_token))
    assert resp.status_code in (401, 403), resp.text
    resp = client.get("/api/v1/admin/users", headers=auth_header(user_token))
    assert resp.status_code in (401, 403), resp.text
    resp = client.get("/api/v1/admin/dashboard", headers=auth_header(user_token))
    assert resp.status_code in (401, 403), resp.text
