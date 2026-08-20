"""邀请码相关 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class InviteCodeCreate(BaseModel):
    count: int = Field(default=1, ge=1, le=100)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)
