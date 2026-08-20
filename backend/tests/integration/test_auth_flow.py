"""认证流程集成测试：注册 → 登录 → me → 刷新 → 上级切换登录。"""

from __future__ import annotations

from tests.conftest import auth_header, get_system_invite_code, register_user


def test_register_login_me(client):
    token = register_user(client, "user0001")
    resp = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == "user0001"
    assert data["status"] == "ACTIVE"
    assert data["credit_level_name"] == "普通信用"
    assert data["completed_order_count"] == 0


def test_login_wrong_password(client):
    register_user(client, "user0002")
    resp = client.post(
        "/api/v1/auth/login", json={"username": "user0002", "password": "WrongPass1"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_INVALID"


def test_login_success_and_refresh(client):
    register_user(client, "user0003")
    login = client.post(
        "/api/v1/auth/login", json={"username": "user0003", "password": "Passw0rd"}
    )
    assert login.status_code == 200
    tokens = login.json()["data"]
    assert tokens["access_token"]

    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200
    assert refresh.json()["data"]["access_token"]


def test_duplicate_username_rejected(client):
    register_user(client, "user0004")
    invite = get_system_invite_code()
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "user0004",
            "invite_code": invite,
            "password": "Passw0rd",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "USER_EXISTS"


def test_unauthorized_access(client):
    resp = client.get("/api/v1/accounts")
    assert resp.status_code == 401


def test_register_generates_unique_invite_code(client):
    token = register_user(client, "user0005")
    resp = client.get("/api/v1/invites/codes", headers=auth_header(token))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["status"] == "ACTIVE"
    assert items[0]["code"]


def test_parent_switch_login(client):
    """上级可通过邀请码关系切换登录直推账号。"""
    parent_token = register_user(client, "parent001")
    # 取上级专属邀请码
    resp = client.get("/api/v1/invites/codes", headers=auth_header(parent_token))
    assert resp.status_code == 200
    invite = resp.json()["data"]["items"][0]["code"]

    child = client.post(
        "/api/v1/auth/register",
        json={"username": "child001", "invite_code": invite, "password": "Passw0rd"},
    )
    assert child.status_code == 200
    child_id = client.get("/api/v1/auth/me", headers=auth_header(child.json()["data"]["access_token"])).json()["data"]["id"]

    # 上级切换登录子账号
    switch = client.post(
        "/api/v1/auth/switch-user",
        json={"user_id": child_id},
        headers=auth_header(parent_token),
    )
    assert switch.status_code == 200
    switch_token = switch.json()["data"]["access_token"]
    me = client.get("/api/v1/auth/me", headers=auth_header(switch_token))
    assert me.status_code == 200
    assert me.json()["data"]["id"] == child_id

    # 非直推关系不可切换
    stranger = client.post(
        "/api/v1/auth/switch-user",
        json={"user_id": child_id},
        headers=auth_header(child.json()["data"]["access_token"]),
    )
    assert stranger.status_code == 401
    assert stranger.json()["code"] == "SWITCH_FORBIDDEN"


def test_switchable_list(client):
    parent_token = register_user(client, "parent002")
    resp = client.get("/api/v1/invites/codes", headers=auth_header(parent_token))
    invite = resp.json()["data"]["items"][0]["code"]
    client.post(
        "/api/v1/auth/register",
        json={"username": "child002", "invite_code": invite, "password": "Passw0rd"},
    )

    resp = client.get("/api/v1/users/team/switchable", headers=auth_header(parent_token))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["username"] == "child002"
