"""通用 Schema：分页等。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=1000)


class IdempotencyHeader(BaseModel):
    idempotency_key: str | None = Field(None, alias="Idempotency-Key")


class ApiResponse[T](BaseModel):
    code: int | str
    message: str
    data: T | None = None
    requestId: str

    model_config = {"from_attributes": True}
