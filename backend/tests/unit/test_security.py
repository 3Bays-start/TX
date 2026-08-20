"""安全模块单元测试：密码哈希 / JWT。"""

from __future__ import annotations

import pytest
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    mask_sensitive,
    verify_password,
)


def test_password_hash_and_verify():
    hashed = hash_password("StrongPass1")
    assert hashed != "StrongPass1"
    assert verify_password("StrongPass1", hashed) is True
    assert verify_password("WrongPass1", hashed) is False


def test_access_token_roundtrip():
    token = create_access_token(42)
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_refresh_token_type():
    token = create_refresh_token(42)
    payload = decode_token(token, expected_type="refresh")
    assert payload["type"] == "refresh"


def test_decode_wrong_type_rejected():
    token = create_refresh_token(42)
    from app.core.exceptions import AuthError

    with pytest.raises(AuthError):
        decode_token(token, expected_type="access")


def test_mask_sensitive():
    assert mask_sensitive("13812345678") == "1*********8"
    assert mask_sensitive("张") == "*"
