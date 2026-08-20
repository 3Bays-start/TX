"""账户 / 流水 / 费用 / 提现 / 推广 Schema。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_no: str
    user_id: int
    available_amount: Decimal
    frozen_amount: Decimal
    pending_amount: Decimal


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_no: str
    business_type: str
    business_id: int | None = None
    amount: Decimal
    before_balance: Decimal
    after_balance: Decimal
    direction: str
    status: str
    reason: str = ""
    created_at: datetime | None = None


class WithdrawalCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    usdt_address: str = Field(min_length=8, max_length=100)


class WithdrawalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    withdrawal_no: str
    user_id: int
    amount: Decimal
    fee: Decimal
    actual_amount: Decimal
    status: str
    review_reason: str = ""
    created_at: datetime | None = None
    processed_at: datetime | None = None


class FeeRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fee_type: str
    name: str
    rate: Decimal
    min_fee: Decimal
    max_fee: Decimal
    status: str
    effective_at: datetime | None = None


class FeeRuleUpdate(BaseModel):
    rate: Decimal = Field(ge=0, le=1)
    min_fee: Decimal = Field(default=Decimal("0"), ge=0)
    max_fee: Decimal = Field(default=Decimal("0"), ge=0)
    name: str | None = None
    status: str | None = None


class PromotionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_no: str
    source_user_id: int
    source_order_id: int
    beneficiary_user_id: int
    rule_type: str
    reward_amount: Decimal
    status: str
    created_at: datetime | None = None
