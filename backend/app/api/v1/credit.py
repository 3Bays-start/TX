"""信用等级接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success
from app.database import get_db
from app.services import auth_service, credit_service

router = APIRouter(prefix="/credit", tags=["credit"])


@router.get("/level")
async def my_credit(current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    data = await credit_service.get_credit_info(db, current_user.completed_order_count or 0)
    return success(data)
