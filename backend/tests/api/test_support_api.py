"""客服 / 申诉 / 通知 / 公告模块测试。"""

from __future__ import annotations

from tests.conftest import auth_header, register_user


def _admin_token(client) -> str:
    resp = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _ticket(client, token: str) -> int:
    resp = client.post(
        "/api/v1/support/tickets",
        headers=auth_header(token),
        json={"category": "QUESTION", "title": "无法支付", "content": "支付时提示余额不足", "priority": "HIGH"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


# ===== 工单 =====


def test_ticket_full_flow(client):
    token = register_user(client, "13870000001")
    admin = _admin_token(client)

    tid = _ticket(client, token)

    # 用户列表
    resp = client.get("/api/v1/support/tickets", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1
    assert resp.json()["data"]["items"][0]["status"] == "OPEN"

    # 用户详情（空消息）
    resp = client.get(f"/api/v1/support/tickets/{tid}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["messages"] == []

    # 用户回复 → 工单转 PROCESSING
    resp = client.post(
        f"/api/v1/support/tickets/{tid}/messages",
        headers=auth_header(token),
        json={"content": "补充：重试也失败"},
    )
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/v1/support/tickets/{tid}", headers=auth_header(token)).json()["data"]
    assert detail["status"] == "PROCESSING"
    assert any(m["sender_type"] == "USER" for m in detail["messages"])

    # 后台工单列表包含该单
    resp = client.get("/api/v1/admin/tickets", headers=auth_header(admin))
    assert resp.status_code == 200
    assert any(t["id"] == tid for t in resp.json()["data"]["items"])

    # 后台回复
    resp = client.post(
        f"/api/v1/admin/tickets/{tid}/reply",
        headers=auth_header(admin),
        json={"content": "已为您核实，请稍候"},
    )
    assert resp.status_code == 200, resp.text

    # 后台关闭
    resp = client.post(f"/api/v1/admin/tickets/{tid}/close", headers=auth_header(admin))
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/v1/support/tickets/{tid}", headers=auth_header(token)).json()["data"]
    assert detail["status"] == "CLOSED"
    assert any(m["sender_type"] == "ADMIN" for m in detail["messages"])

    # 关闭后回复被拒
    resp = client.post(
        f"/api/v1/support/tickets/{tid}/messages",
        headers=auth_header(token),
        json={"content": "还想追问"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "TICKET_CLOSED"


def test_ticket_scoped_to_owner(client):
    token = register_user(client, "13870000002")
    tid = _ticket(client, token)
    other = register_user(client, "13870000003")

    resp = client.get(f"/api/v1/support/tickets/{tid}", headers=auth_header(other))
    assert resp.status_code == 404
    assert resp.json()["code"] == "TICKET_NOT_FOUND"


# ===== 申诉 =====


def test_appeal_full_flow(client):
    token = register_user(client, "13870000004")
    admin = _admin_token(client)

    resp = client.post(
        "/api/v1/appeals",
        headers=auth_header(token),
        json={"subject": "订单纠纷", "content": "未收到服务", "evidence": "截图链接"},
    )
    assert resp.status_code == 200, resp.text
    aid = resp.json()["data"]["id"]
    assert resp.json()["data"]["status"] == "PENDING"

    # 用户申诉列表
    resp = client.get("/api/v1/appeals", headers=auth_header(token))
    assert resp.status_code == 200
    assert any(a["id"] == aid for a in resp.json()["data"]["items"])

    # 后台列表
    resp = client.get("/api/v1/admin/appeals", headers=auth_header(admin))
    assert resp.status_code == 200
    assert any(a["id"] == aid for a in resp.json()["data"]["items"])

    # 后台处理通过
    resp = client.post(
        f"/api/v1/admin/appeals/{aid}/process",
        headers=auth_header(admin),
        json={"approve": True, "result": "双方协商一致"},
    )
    assert resp.status_code == 200, resp.text

    detail = client.get("/api/v1/appeals", headers=auth_header(token)).json()["data"]
    mine = next(a for a in detail["items"] if a["id"] == aid)
    assert mine["status"] == "RESOLVED"
    assert mine["result"] == "双方协商一致"

    # 重复处理被拒
    resp = client.post(
        f"/api/v1/admin/appeals/{aid}/process",
        headers=auth_header(admin),
        json={"approve": False, "result": ""},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "APPEAL_PROCESSED"


# ===== 通知 =====


def test_notification_flow(client):
    token = register_user(client, "13870000005")
    uid = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]
    admin = _admin_token(client)
    client.post(
        f"/api/v1/admin/users/{uid}/adjust",
        headers=auth_header(admin),
        json={"amount": 5000, "reason": "入金"},
    )

    # 买家下单 + 支付（产生 PAYMENT 通知）
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "BUY", "amount": 1000}
    )
    order_id = resp.json()["data"]["id"]
    resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_header(token))
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/v1/notifications", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert data["unread"] >= 1
    assert any(n["type"] == "PAYMENT" for n in data["items"])
    nid = data["items"][0]["id"]

    # 单条已读
    resp = client.post(f"/api/v1/notifications/{nid}/read", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["ok"] is True

    # 全部已读
    resp = client.post("/api/v1/notifications/read-all", headers=auth_header(token))
    assert resp.status_code == 200
    unread = client.get("/api/v1/notifications", headers=auth_header(token)).json()["data"]["unread"]
    assert unread == 0


def test_read_other_users_notification_ignored(client):
    token = register_user(client, "13870000006")
    other = register_user(client, "13870000007")
    resp = client.get("/api/v1/notifications", headers=auth_header(other))
    others = resp.json()["data"]["items"]
    if others:
        resp = client.post(
            f"/api/v1/notifications/{others[0]['id']}/read", headers=auth_header(token)
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["ok"] is False


# ===== 公告 =====


def test_announcement_publish_and_visible(client):
    admin = _admin_token(client)

    # 后台发布
    resp = client.post(
        "/api/v1/admin/announcements",
        headers=auth_header(admin),
        json={"title": "系统维护通知", "content": "本周六凌晨维护", "type": "NOTICE"},
    )
    assert resp.status_code == 200, resp.text
    aid = resp.json()["data"]["id"]

    # 后台列表
    resp = client.get("/api/v1/admin/announcements", headers=auth_header(admin))
    assert resp.status_code == 200
    assert any(a["id"] == aid for a in resp.json()["data"]["items"])

    # 用户端可见
    token = register_user(client, "13870000008")
    resp = client.get("/api/v1/announcements", headers=auth_header(token))
    assert resp.status_code == 200
    assert any(a["title"] == "系统维护通知" for a in resp.json()["data"]["items"])
