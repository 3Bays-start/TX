"""安全：JWT、密码哈希（Argon2id）、令牌。"""

from __future__ import annotations

import datetime as dt
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import settings
from app.core.exceptions import AuthError, TokenExpiredError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _encode(subject: str, token_type: str, expire_seconds: int, extra: dict[str, Any] | None = None) -> str:
    now = dt.datetime.now(dt.UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + dt.timedelta(seconds=expire_seconds),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    subject_id: int | str,
    role: str = "user",
    extra: dict[str, Any] | None = None,
) -> str:
    extra = {**(extra or {}), "role": role}
    return _encode(str(subject_id), "access", settings.JWT_ACCESS_EXPIRE, extra)


def create_refresh_token(subject_id: int | str, role: str = "user") -> str:
    return _encode(str(subject_id), "refresh", settings.JWT_REFRESH_EXPIRE, {"role": role})


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("TOKEN_INVALID", "令牌无效") from exc
    if payload.get("type") != expected_type:
        raise AuthError("TOKEN_INVALID", "令牌类型错误")
    return payload


def mask_sensitive(value: str | None, keep_front: int = 1, keep_back: int = 1) -> str:
    """脱敏：手机号 / 姓名 / 身份证号。"""
    if not value:
        return ""
    if len(value) <= keep_front + keep_back:
        return "*" * len(value)
    return value[:keep_front] + "*" * (len(value) - keep_front - keep_back) + value[-keep_back:]
