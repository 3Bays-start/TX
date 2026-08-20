"""首页轮播广告接口。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success
from app.database import get_db
from app.models.banner import Banner

router = APIRouter(prefix="/banners", tags=["banners"])


@router.get("")
async def list_banners(db: AsyncSession = Depends(get_db)):
    now = datetime.now()
    stmt = (
        select(Banner)
        .where(Banner.status == "ACTIVE")
        .where((Banner.start_at.is_(None)) | (Banner.start_at <= now))
        .where((Banner.end_at.is_(None)) | (Banner.end_at >= now))
        .order_by(Banner.sort_order.desc(), Banner.id.desc())
    )
    items = list((await db.execute(stmt)).scalars().all())
    return success(
        {
            "items": [
                {
                    "id": b.id,
                    "title": b.title,
                    "subtitle": b.subtitle,
                    "image_url": b.image_url,
                    "link_type": b.link_type,
                    "link_value": b.link_value,
                }
                for b in items
            ]
        }
    )
