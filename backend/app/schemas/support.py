"""客服 / 申诉 / 风控 / 通知 Schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    category: str = "OTHER"
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=2)
    order_id: int | None = None
    priority: str = "NORMAL"


class TicketMessageCreate(BaseModel):
    content: str = Field(min_length=1)
    attachments: str = ""


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_no: str
    user_id: int
    category: str
    title: str
    content: str
    order_id: int | None = None
    priority: str
    status: str
    created_at: datetime | None = None


class TicketDetailOut(TicketOut):
    messages: list[object] = []


class AppealCreate(BaseModel):
    order_id: int | None = None
    subject: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=2)
    evidence: str = ""


class AppealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appeal_no: str
    user_id: int
    order_id: int | None = None
    subject: str
    content: str
    evidence: str = ""
    status: str
    result: str = ""
    created_at: datetime | None = None


class RiskEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_no: str
    user_id: int
    rule_code: str
    level: str
    action: str
    detail: str
    status: str
    created_at: datetime | None = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    content: str
    status: str
    business_type: str = ""
    business_id: int | None = None
    created_at: datetime | None = None


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    type: str
    status: str
    published_at: datetime | None = None
