"""邀请码接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success
from app.database import get_db
from app.schemas.invite import InviteCodeCreate
from app.services import auth_service, invite_service

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("/codes")
async def create_codes(
    payload: InviteCodeCreate,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    codes = await invite_service.create_invite_codes(
        db, current_user.id, payload.count, payload.expires_in_days
    )
    return success(
        {
            "items": [
                {"id": c.id, "code": c.code, "status": c.status, "expires_at": c.expires_at.isoformat() if c.expires_at else None}
                for c in codes
            ]
        },
        "邀请码已生成",
    )


@router.get("/codes")
async def my_codes(current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    codes = await invite_service.user_invite_codes(db, current_user.id)
    return success(
        {
            "items": [
                {
                    "id": c.id,
                    "code": c.code,
                    "status": c.status,
                    "used_by": c.used_by,
                    "used_at": c.used_at.isoformat() if c.used_at else None,
                    "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in codes
            ]
        }
    )


@router.post("/codes/{code_id}/disable")
async def disable_code(
    code_id: int,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    invite = await invite_service.disable_invite_code(db, code_id)
    if not invite or invite.creator_id is None or invite.creator_id != current_user.id:
        return success(None, "无操作")
    return success(None, "邀请码已禁用")
