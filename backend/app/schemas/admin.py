"""管理后台 Schema。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    role_code: str
    status: str
    is_super: bool = False
    last_login_at: datetime | None = None


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=64)
    nickname: str = ""
    role_code: str = "ADMIN"
    role_ids: list[int] = []


class AdminUserUpdate(BaseModel):
    nickname: str | None = None
    password: str | None = None
    status: str | None = None
    role_ids: list[int] | None = None


class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=50)
    description: str = ""
    permission_codes: list[str] = []


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str = ""
    is_system: bool = False
    permission_codes: list[str] = []


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    group: str = ""
    description: str = ""


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    nickname: str
    status: str
    risk_level: str
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class UserDetailAdminOut(UserAdminOut):
    account: AccountAdminBrief | None = None
    credit_level_name: str = ""
    credit_level_code: str = ""
    completed_order_count: int = 0


class AccountAdminBrief(BaseModel):
    available_amount: Decimal
    frozen_amount: Decimal
    pending_amount: Decimal


class WithdrawalReviewRequest(BaseModel):
    approve: bool
    reason: str = ""


class RiskEventReviewRequest(BaseModel):
    approve: bool
    action: str | None = None
    reason: str = ""


class DashboardOut(BaseModel):
    user_total: int
    user_today: int
    active_users: int
    order_total: int
    order_today: int
    waiting_match: int
    matching: int
    abnormal_orders: int
    appeal_pending: int
    withdrawal_pending: int
    service_fee_total: Decimal
    charts: dict = {}


class OrderAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    user_id: int
    order_type: str
    product_name: str
    total_amount: Decimal
    service_fee: Decimal
    payable_amount: Decimal
    matched_amount: Decimal
    status: str
    created_at: datetime | None = None
