"""认证服务：注册/登录/令牌/当前用户与管理员依赖。"""

from __future__ import annotations

from datetime import datetime

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    AppError,
    AuthError,
    NotFoundError,
    UserDisabledError,
    UserFrozenError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.admin import AdminUser
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, SwitchUserRequest, TokenPair
from app.services.account_service import ensure_account

_LOGIN_LIMIT_PREFIX = "login:limit:"


async def register(db: AsyncSession, payload: RegisterRequest, ip: str = "") -> User:
    from app.models.invite import UserRelation
    from app.models.user import UserLoginLog
    from app.services.invite_service import create_user_invite_code, use_invite_code

    exists = await db.scalar(select(User).where(User.username == payload.username))
    if exists:
        raise AppError("USER_EXISTS", "该账号已注册")

    invite = await use_invite_code(db, payload.invite_code)

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname or payload.username,
        register_ip=ip,
    )
    db.add(user)
    await db.flush()

    await ensure_account(db, user.id)
    # 每个账号注册时生成唯一邀请码（终身可复用）
    await create_user_invite_code(db, user.id)

    # 系统邀请码（creator_id 为空）不建立上级关系
    if invite.creator_id is not None:
        db.add(
            UserRelation(
                user_id=user.id,
                parent_id=invite.creator_id,
                level=1,
                path=f"/{invite.creator_id}/{user.id}",
            )
        )
    db.add(UserLoginLog(user_id=user.id, login_type="REGISTER", ip=ip, success=True))
    return user


async def login(db: AsyncSession, payload: LoginRequest, ip: str = "", user_agent: str = "") -> TokenPair:
    from app.models.user import UserLoginLog

    user = await db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise AuthError("AUTH_INVALID", "账号或密码错误")
    if user.status == "DISABLED":
        raise UserDisabledError()
    if user.status == "FROZEN":
        raise UserFrozenError()

    user.last_login_at = datetime.now()
    user.last_login_ip = ip
    db.add(UserLoginLog(user_id=user.id, login_type="PASSWORD", ip=ip, user_agent=user_agent, success=True))
    await db.flush()

    return TokenPair(
        access_token=create_access_token(user.id, role="user"),
        refresh_token=create_refresh_token(user.id, role="user"),
        expires_in=settings.JWT_ACCESS_EXPIRE,
    )


async def switch_user(db: AsyncSession, current_user: User, payload: SwitchUserRequest) -> TokenPair:
    """上级切换登录直推账号（默认开启，受 allow_parent_switch 控制）。"""
    from app.models.invite import UserRelation

    target = await db.get(User, payload.user_id)
    if not target:
        raise NotFoundError("USER_NOT_FOUND", "目标账号不存在")

    relation = await db.scalar(
        select(UserRelation).where(
            UserRelation.user_id == target.id,
            UserRelation.parent_id == current_user.id,
            UserRelation.level == 1,
        )
    )
    if not relation:
        raise AuthError("SWITCH_FORBIDDEN", "仅可切换登录由您直接邀请的账号")
    if not target.allow_parent_switch:
        raise AuthError("SWITCH_DISABLED", "该账号已关闭上级切换登录")
    if target.status == "DISABLED":
        raise UserDisabledError()
    if target.status == "FROZEN":
        raise UserFrozenError()

    return TokenPair(
        access_token=create_access_token(target.id, role="user"),
        refresh_token=create_refresh_token(target.id, role="user"),
        expires_in=settings.JWT_ACCESS_EXPIRE,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenPair:
    payload = decode_token(refresh_token, expected_type="refresh")
    if payload.get("role") != "user":
        raise AuthError("TOKEN_INVALID", "令牌类型错误")
    user_id = int(payload["sub"])
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("USER_NOT_FOUND", "用户不存在")
    return TokenPair(
        access_token=create_access_token(user.id, role="user"),
        refresh_token=create_refresh_token(user.id, role="user"),
        expires_in=settings.JWT_ACCESS_EXPIRE,
    )


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_token(authorization)
    payload = decode_token(token, expected_type="access")
    if payload.get("role") != "user":
        raise AuthError("TOKEN_INVALID", "令牌类型错误")
    user = await db.get(User, int(payload["sub"]))
    if not user:
        raise AuthError("AUTH_INVALID", "用户不存在")
    if user.status == "DISABLED":
        raise UserDisabledError()
    if user.status == "FROZEN":
        raise UserFrozenError()
    return user


async def get_current_admin(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    token = _extract_token(authorization)
    payload = decode_token(token, expected_type="access")
    if payload.get("role") != "admin":
        raise AuthError("TOKEN_INVALID", "令牌类型错误")
    admin = await db.get(AdminUser, int(payload["sub"]))
    if not admin or admin.status != "ACTIVE":
        raise AuthError("AUTH_INVALID", "管理员不存在或已禁用")
    return admin


def _extract_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthError("AUTH_INVALID", "缺少认证信息")
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("AUTH_INVALID", "认证头格式错误")
    return parts[1]
