"""订单 / 预约 / 撮合 Schema。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    order_type: str = Field(default="BUY", pattern="^(BUY|SELL)$")
    amount: Decimal | None = Field(default=None, gt=0)
    reservation_time: datetime | None = None
    remark: str = ""


class ProofSubmit(BaseModel):
    """撮合完成后绑定服务凭证（/uploads/ 相对 URL 列表）。"""

    urls: list[str] = Field(default_factory=list, max_length=9)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    user_id: int
    order_type: str
    product_name: str = ""
    total_amount: Decimal
    service_fee: Decimal
    payable_amount: Decimal
    matched_amount: Decimal
    status: str
    reservation_time: datetime | None = None
    remark: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrderDetailOut(OrderOut):
    status_logs: list[object] = []
    matches: list[object] = []


class ReservationCreate(BaseModel):
    order_id: int


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reservation_no: str
    order_id: int
    user_id: int
    reserved_at: datetime | None = None
    priority: int = 0
    status: str
    created_at: datetime | None = None


class MatchOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_no: str
    parent_order_id: int
    parent_user_id: int
    buyer_order_id: int
    seller_order_id: int
    match_amount: Decimal
    status: str
    completed_at: datetime | None = None
    created_at: datetime | None = None


class MatchingStatusOut(BaseModel):
    order_id: int
    target_amount: Decimal
    matched_amount: Decimal
    remaining_amount: Decimal
    status: str
    matches: list[MatchOrderOut] = []
