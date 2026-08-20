"""通知服务。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Announcement, Notification


async def notify_user(
    db: AsyncSession,
    user_id: int,
    type_: str,
    title: str,
    content: str = "",
    business_type: str = "",
    business_id: int | None = None,
) -> Notification:
    n = Notification(
        user_id=user_id,
        type=type_,
        title=title,
        content=content,
        business_type=business_type,
        business_id=business_id,
    )
    db.add(n)
    await db.flush()
    return n


async def list_notifications(
    db: AsyncSession, user_id: int, page: int, page_size: int
) -> tuple[list[Notification], int]:
    base = select(Notification).where(Notification.user_id == user_id)
    total = len((await db.execute(base)).scalars().all())
    stmt = (
        base.order_by(Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> bool:
    n = await db.get(Notification, notification_id)
    if not n or n.user_id != user_id:
        return False
    from datetime import datetime

    n.status = "READ"
    n.read_at = datetime.now()
    return True


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    from datetime import datetime

    stmt = select(Notification).where(
        Notification.user_id == user_id, Notification.status == "UNREAD"
    )
    items = list((await db.execute(stmt)).scalars().all())
    for n in items:
        n.status = "READ"
        n.read_at = datetime.now()
    return len(items)


async def unread_count(db: AsyncSession, user_id: int) -> int:
    stmt = select(Notification).where(
        Notification.user_id == user_id, Notification.status == "UNREAD"
    )
    return len((await db.execute(stmt)).scalars().all())


async def list_announcements(db: AsyncSession, page: int = 1, page_size: int = 20) -> tuple[list[Announcement], int]:
    base = select(Announcement).where(Announcement.status == "ACTIVE")
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(Announcement.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total
