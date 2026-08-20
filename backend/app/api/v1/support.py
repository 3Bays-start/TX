"""客服 / 申诉 / 通知接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.response import success
from app.database import get_db
from app.dependencies import get_page_params
from app.models.support import SupportTicket
from app.schemas.common import PageParams
from app.schemas.support import AppealCreate, TicketCreate, TicketMessageCreate
from app.services import (
    appeal_service,
    auth_service,
    notification_service,
    support_service,
)

router = APIRouter(tags=["support"])


# ===== 客服 =====

@router.post("/support/tickets")
async def create_ticket(
    payload: TicketCreate,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await support_service.create_ticket(
        db, current_user.id, payload.category, payload.title, payload.content, payload.order_id, payload.priority
    )
    return success({"ticket_no": ticket.ticket_no, "id": ticket.id, "status": ticket.status}, "工单已创建")


@router.get("/support/tickets")
async def list_tickets(
    status: str | None = None,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    items, total = await support_service.list_tickets(db, current_user.id, params.page, params.page_size, status)
    return success(
        {
            "items": [
                {
                    "id": t.id,
                    "ticket_no": t.ticket_no,
                    "category": t.category,
                    "title": t.title,
                    "priority": t.priority,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in items
            ],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )


@router.get("/support/tickets/{ticket_id}")
async def ticket_detail(
    ticket_id: int,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await db.get(SupportTicket, ticket_id)
    if not ticket or ticket.user_id != current_user.id:
        raise NotFoundError("TICKET_NOT_FOUND", "工单不存在")
    messages = await support_service.get_ticket_messages(db, ticket_id)
    return success(
        {
            "id": ticket.id,
            "ticket_no": ticket.ticket_no,
            "category": ticket.category,
            "title": ticket.title,
            "content": ticket.content,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "messages": [
                {
                    "sender_type": m.sender_type,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }
    )


@router.post("/support/tickets/{ticket_id}/messages")
async def reply_ticket(
    ticket_id: int,
    payload: TicketMessageCreate,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    msg = await support_service.add_message(
        db, ticket_id, "USER", current_user.id, payload.content, payload.attachments
    )
    return success({"message_id": msg.id}, "回复成功")


# ===== 申诉 =====

@router.post("/appeals")
async def create_appeal(
    payload: AppealCreate,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appeal = await appeal_service.create_appeal(
        db, current_user.id, payload.subject, payload.content, payload.order_id, payload.evidence
    )
    return success({"appeal_no": appeal.appeal_no, "id": appeal.id, "status": appeal.status}, "申诉已提交")


@router.get("/appeals")
async def list_appeals(
    status: str | None = None,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    items, total = await appeal_service.list_appeals(db, current_user.id, params.page, params.page_size, status)
    return success(
        {
            "items": [
                {
                    "id": a.id,
                    "appeal_no": a.appeal_no,
                    "order_id": a.order_id,
                    "subject": a.subject,
                    "status": a.status,
                    "result": a.result,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in items
            ],
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    )


# ===== 通知 =====

@router.get("/notifications")
async def list_notifications(
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PageParams = Depends(get_page_params),
):
    items, total = await notification_service.list_notifications(db, current_user.id, params.page, params.page_size)
    return success(
        {
            "items": [
                {
                    "id": n.id,
                    "type": n.type,
                    "title": n.title,
                    "content": n.content,
                    "status": n.status,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in items
            ],
            "total": total,
            "unread": await notification_service.unread_count(db, current_user.id),
            "page": params.page,
            "page_size": params.page_size,
        }
    )


@router.post("/notifications/{notification_id}/read")
async def read_notification(
    notification_id: int,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await notification_service.mark_read(db, current_user.id, notification_id)
    return success({"ok": ok})


@router.post("/notifications/read-all")
async def read_all(current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    count = await notification_service.mark_all_read(db, current_user.id)
    return success({"count": count}, "已全部标记已读")


@router.get("/announcements")
async def announcements(db: AsyncSession = Depends(get_db)):
    items, total = await notification_service.list_announcements(db)
    return success(
        {
            "items": [
                {
                    "id": a.id,
                    "title": a.title,
                    "content": a.content,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                }
                for a in items
            ],
            "total": total,
        }
    )
