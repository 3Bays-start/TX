"""客服服务。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.support import SupportTicket, TicketMessage
from app.utils.misc import gen_no


async def create_ticket(
    db: AsyncSession,
    user_id: int,
    category: str,
    title: str,
    content: str,
    order_id: int | None = None,
    priority: str = "NORMAL",
) -> SupportTicket:
    ticket = SupportTicket(
        ticket_no=gen_no("TK", 24),
        user_id=user_id,
        category=category,
        title=title,
        content=content,
        order_id=order_id,
        priority=priority,
    )
    db.add(ticket)
    await db.flush()
    return ticket


async def add_message(
    db: AsyncSession,
    ticket_id: int,
    sender_type: str,
    sender_id: int,
    content: str,
    attachments: str = "",
) -> TicketMessage:
    ticket = await db.get(SupportTicket, ticket_id)
    if not ticket or ticket.status == "CLOSED":
        raise AppError("TICKET_CLOSED", "工单已关闭")
    message = TicketMessage(
        ticket_id=ticket_id,
        sender_type=sender_type,
        sender_id=sender_id,
        content=content,
        attachments=attachments,
    )
    db.add(message)
    await db.flush()
    if ticket.status == "OPEN":
        ticket.status = "PROCESSING"
    return message


async def list_tickets(
    db: AsyncSession, user_id: int, page: int, page_size: int, status: str | None = None
) -> tuple[list[SupportTicket], int]:
    base = select(SupportTicket).where(SupportTicket.user_id == user_id)
    if status:
        base = base.where(SupportTicket.status == status)
    total = len((await db.execute(base)).scalars().all())
    stmt = base.order_by(SupportTicket.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def get_ticket_messages(db: AsyncSession, ticket_id: int) -> list[TicketMessage]:
    stmt = select(TicketMessage).where(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.id.asc())
    return list((await db.execute(stmt)).scalars().all())


async def close_ticket(db: AsyncSession, ticket_id: int, operator_id: int, operator_type: str = "ADMIN") -> SupportTicket:
    ticket = await db.get(SupportTicket, ticket_id)
    if not ticket:
        raise NotFoundError("TICKET_NOT_FOUND", "工单不存在")
    ticket.status = "CLOSED"
    ticket.closed_at = datetime.now()
    return ticket
