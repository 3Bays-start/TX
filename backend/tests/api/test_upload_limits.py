"""上传边界测试：超大文件（G-08）与空文件。"""

from __future__ import annotations

import io

from tests.conftest import auth_header, register_user


def test_upload_rejects_oversized_file(client):
    """构造 >10MB 文件 → 400 FILE_TOO_LARGE。"""
    from app.config import settings

    token = register_user(client, "13850000001")
    big = io.BytesIO(b"x" * (settings.UPLOAD_MAX_SIZE + 1024))
    resp = client.post(
        "/api/v1/upload",
        headers=auth_header(token),
        files={"file": ("big.png", big, "image/png")},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "FILE_TOO_LARGE"


def test_upload_rejects_empty_file(client):
    token = register_user(client, "13850000002")
    resp = client.post(
        "/api/v1/upload",
        headers=auth_header(token),
        files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "FILE_EMPTY"
