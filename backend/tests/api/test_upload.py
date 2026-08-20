"""文件上传与订单凭证测试。"""

from __future__ import annotations

from tests.conftest import auth_header, register_user

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _admin_token(client) -> str:
    resp = client.post(
        "/api/v1/admin/login", json={"username": "superadmin", "password": "Admin@123456"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _full_match_order(client, token: str) -> int:
    """造一个已完成撮合的买方订单（COMPLETED）。"""
    admin_token = _admin_token(client)
    for i in range(3):
        s = register_user(client, f"1385000001{i}")
        resp = client.post(
            "/api/v1/orders", headers=auth_header(s), json={"order_type": "SELL", "amount": 4000}
        )
        assert resp.status_code == 200, resp.text

    uid = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["data"]["id"]
    client.post(
        f"/api/v1/admin/users/{uid}/adjust",
        headers=auth_header(admin_token),
        json={"amount": 20000, "reason": "测试入金"},
    )
    resp = client.post(
        "/api/v1/orders", headers=auth_header(token), json={"order_type": "BUY", "amount": 10000}
    )
    assert resp.status_code == 200, resp.text
    order_id = resp.json()["data"]["id"]
    resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "WAITING_MATCH"
    # 后台自动撮合
    resp = client.post("/api/v1/admin/matching/auto", headers=auth_header(admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["matched"] >= 1
    return order_id


def test_upload_requires_auth(client):
    resp = client.post(
        "/api/v1/upload", files={"file": ("a.png", PNG, "image/png")}
    )
    assert resp.status_code == 401


def test_upload_rejects_bad_extension(client):
    token = register_user(client, "13860000001")
    resp = client.post(
        "/api/v1/upload",
        headers=auth_header(token),
        files={"file": ("evil.exe", b"MZ...", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "FILE_TYPE_NOT_ALLOWED"


def test_upload_success(client):
    token = register_user(client, "13860000002")
    resp = client.post(
        "/api/v1/upload",
        headers=auth_header(token),
        files={"file": ("proof.png", PNG, "image/png")},
    )
    assert resp.status_code == 200, resp.text
    url = resp.json()["data"]["url"]
    assert url.startswith("/uploads/")


def test_proof_attach_flow(client):
    token = register_user(client, "13860000003")
    order_id = _full_match_order(client, token)

    url = client.post(
        "/api/v1/upload",
        headers=auth_header(token),
        files={"file": ("proof.png", PNG, "image/png")},
    ).json()["data"]["url"]

    resp = client.post(
        f"/api/v1/orders/{order_id}/proof",
        headers=auth_header(token),
        json={"urls": [url]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["proof_urls"] == [url]

    detail = client.get(
        f"/api/v1/orders/{order_id}", headers=auth_header(token)
    ).json()["data"]
    assert url in detail["proof_urls"]
    assert detail["proof_submitted_at"] is not None


def test_proof_rejects_external_url(client):
    token = register_user(client, "13860000004")
    order_id = _full_match_order(client, token)
    resp = client.post(
        f"/api/v1/orders/{order_id}/proof",
        headers=auth_header(token),
        json={"urls": ["https://evil.example.com/x.png"]},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_PROOF_URL"


def test_proof_rejects_non_buyer(client):
    token = register_user(client, "13860000005")
    order_id = _full_match_order(client, token)
    other = register_user(client, "13860000006")
    resp = client.post(
        f"/api/v1/orders/{order_id}/proof",
        headers=auth_header(other),
        json={"urls": ["/uploads/1/abc.png"]},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "ORDER_NOT_FOUND"
