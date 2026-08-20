"""认证与用户 Schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_PATTERN = r"^1[3-9]\d{9}$"
USERNAME_PATTERN = r"^[A-Za-z0-9_]{3,20}$"


class RegisterRequest(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    invite_code: str = Field(min_length=4, max_length=16)
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(default="", max_length=30)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("密码必须同时包含字母和数字")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class SwitchUserRequest(BaseModel):
    user_id: int


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str = ""
    phone: str = ""
    nickname: str
    avatar: str = ""
    status: str
    risk_level: str
    credit_level_name: str = ""
    credit_level_code: str = ""
    completed_order_count: int = 0
    created_at: datetime | None = None


class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gender: str = ""
    birth_date: datetime | None = None
    email: str = ""
    region: str = ""
    bio: str = ""


class ProfileUpdateRequest(BaseModel):
    nickname: str | None = None
    gender: str | None = None
    email: str | None = None
    region: str | None = None
    bio: str | None = None
    avatar: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=64)


class ResetPasswordRequest(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    sms_code: str
    new_password: str = Field(min_length=8, max_length=64)


class TeamUserOut(BaseModel):
    user_id: int
    username: str = ""
    nickname: str
    phone: str = ""
    level: int
    created_at: datetime | None = None


class TeamSummaryOut(BaseModel):
    total_team: int
    direct_count: int
    active_count: int
    team_order_count: int
    team_order_amount: str
