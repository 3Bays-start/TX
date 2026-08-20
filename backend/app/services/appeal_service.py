"""申诉服务。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.appeal import Appeal, AppealLog
from app.utils.misc import gen_no


async def create_appeal(
    db: AsyncSession,
    user_id: int,
    subject: str,
    content: str,
    order_id: int | None = None,
    evidence: str = "",
) -> Appeal:
    appeal = Appeal(
        appeal_no=gen_no("AP", 24),
        user_id=user_id,
        order_id=order_id,
        subject=subject,
        content=content,
        evidence=evidence,
    )
    db.add(appeal)
    await db.flush()
    db.add(AppealLog(appeal_id=appeal.id, action="CREATE", detail="用户提交申诉"))
    return appeal


async def process_appeal(
    db: AsyncSession,
    appeal_id: int,
    admin_id: int,
    approve: bool,
    result: str,
) -> Appeal:
    appeal = await db.get(Appeal, appeal_id)
    if not appeal:
        raise NotFoundError("APPEAL_NOT_FOUND", "申诉不存在")
    if appeal.status not in ("PENDING", "PROCESSING"):
        raise AppError("APPEAL_PROCESSED", "申诉已处理")
    appeal.status = "RESOLVED" if approve else "REJECTED"
    appeal.result = result
    appeal.processed_by = admin_id
    appeal.processed_at = datetime.now()
    db.add(
        AppealLog(
            appeal_id=appeal.id,
            action="RESOLVE" if approve else "REJECT",
            operator_type="ADMIN",
            operator_id=admin_id,
            detail=result,
        )
    )
    return appeal


async def list_appeals(
    db: AsyncSession, user_id: int, page: int, page_size: int, status: str | None = None
) -> tuple[list[Appeal], int]:
    base = select(Appeal).where(Appeal.user_id == user_id)
    if status:
        base = base.where(Appeal.status == status)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(Appeal.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total
