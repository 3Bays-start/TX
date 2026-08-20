"""用户接口：资料 / 实名 / 团队 / 安全。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.response import success
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.dependencies import get_page_params
from app.models.user import UserProfile
from app.schemas.auth import (
    ChangePasswordRequest,
    ProfileUpdateRequest,
)
from app.schemas.common import PageParams
from app.services import auth_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.id))
    credit_name, credit_code = await user_service.get_credit_level(db, current_user.completed_order_count or 0)
    return success(
        {
            "id": current_user.id,
            "username": current_user.username or "",
            "phone": current_user.phone or "",
            "nickname": current_user.nickname,
            "avatar": current_user.avatar,
            "status": current_user.status,
            "risk_level": current_user.risk_level,
            "credit_level_name": credit_name,
            "credit_level_code": credit_code,
            "completed_order_count": current_user.completed_order_count or 0,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "profile": {
                "gender": profile.gender if profile else "",
                "email": profile.email if profile else "",
                "region": profile.region if profile else "",
                "bio": profile.bio if profile else "",
            },
        }
    )


@router.put("/me/profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.id))
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    if payload.nickname is not None:
        current_user.nickname = payload.nickname
    if payload.avatar is not None:
        current_user.avatar = payload.avatar
    if payload.gender is not None:
        profile.gender = payload.gender
    if payload.email is not None:
        profile.email = payload.email
    if payload.region is not None:
        profile.region = payload.region
    if payload.bio is not None:
        profile.bio = payload.bio
    await db.flush()
    return success(None, "资料已更新")


@router.post("/me/password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.old_password, current_user.password_hash):
        raise AppError("PASSWORD_INCORRECT", "原密码错误")
    current_user.password_hash = hash_password(payload.new_password)
    await db.flush()
    return success(None, "密码已修改")


@router.get("/team/summary")
async def team_summary(current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    data = await user_service.team_summary(db, current_user.id)
    return success(data)


@router.get("/team/switchable")
async def team_switchable(current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    """可直接切换登录的直推账号列表。"""
    items = await user_service.team_switchable(db, current_user.id)
    data = [
        {
            "user_id": u.id,
            "username": u.username or "",
            "nickname": u.nickname,
            "allow_parent_switch": u.allow_parent_switch,
        }
        for u in items
    ]
    return success({"items": data})


@router.get("/team")
async def team_members(
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    items, total = await user_service.team_members(db, current_user.id, params.page, params.page_size)
    data = [
        {
            "user_id": u.id,
            "username": u.username or "",
            "nickname": u.nickname,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in items
    ]
    return success({"items": data, "total": total, "page": params.page, "page_size": params.page_size})
