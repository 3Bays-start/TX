"""认证接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.response import success
from app.core.security import create_access_token, create_refresh_token
from app.database import get_db
from app.dependencies import RateLimiter
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SwitchUserRequest,
    TokenPair,
    UserInfo,
)
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", dependencies=[Depends(RateLimiter(5, 60))])
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register(db, payload, ip=_client_ip(request))
    tokens = TokenPair(
        access_token=create_access_token(user.id, role="user"),
        refresh_token=create_refresh_token(user.id, role="user"),
        expires_in=settings.JWT_ACCESS_EXPIRE,
    )
    return success(tokens.model_dump(), "注册成功")


@router.post("/login", dependencies=[Depends(RateLimiter(10, 60))])
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    tokens = await auth_service.login(
        db, payload, ip=_client_ip(request), user_agent=request.headers.get("user-agent", "")
    )
    return success(tokens.model_dump(), "登录成功")


@router.post("/switch-user")
async def switch_user(
    payload: SwitchUserRequest,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tokens = await auth_service.switch_user(db, current_user, payload)
    return success(tokens.model_dump(), "切换成功")


@router.post("/refresh")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    tokens = await auth_service.refresh_tokens(db, payload.refresh_token)
    return success(tokens.model_dump(), "刷新成功")


@router.get("/me")
async def me(current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    credit_name, credit_code = await user_service.get_credit_level(db, current_user.completed_order_count or 0)
    data = UserInfo(
        id=current_user.id,
        username=current_user.username or "",
        phone=current_user.phone or "",
        nickname=current_user.nickname,
        avatar=current_user.avatar,
        status=current_user.status,
        risk_level=current_user.risk_level,
        credit_level_name=credit_name,
        credit_level_code=credit_code,
        completed_order_count=current_user.completed_order_count or 0,
        created_at=current_user.created_at,
    )
    return success(data.model_dump())


def _client_ip(request: Request) -> str:
    # 仅当部署在可信反向代理后且代理覆盖 X-Forwarded-For 时才信任该头；
    # 未配置可信代理时优先使用直连 socket 地址，避免客户端伪造 IP 绕过限流。
    fwd = request.headers.get("x-forwarded-for")
    if fwd and settings.TRUSTED_PROXY:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""
