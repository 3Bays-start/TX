"""统一响应结构与错误响应。"""

from __future__ import annotations

import uuid
from typing import Any, cast

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError, AuthError, PermissionDeniedError

_CODE_MESSAGE: dict[str, str] = {
    "AUTH_INVALID": "认证失败",
    "TOKEN_EXPIRED": "登录已过期",
    "PERMISSION_DENIED": "权限不足",
    "NOT_FOUND": "资源不存在",
    "USER_NOT_FOUND": "用户不存在",
    "USER_FROZEN": "用户已被冻结",
    "USER_DISABLED": "用户已被禁用",
    "INVITE_CODE_INVALID": "邀请码无效",
    "INVITE_CODE_USED": "邀请码已被使用",
    "INVITE_CODE_EXPIRED": "邀请码已过期",
    "ORDER_NOT_FOUND": "订单不存在",
    "ORDER_INVALID_STATUS": "当前订单状态不允许执行此操作",
    "ORDER_ALREADY_COMPLETED": "订单已完成",
    "MATCH_NOT_FOUND": "撮合记录不存在",
    "MATCH_AMOUNT_INVALID": "撮合金额无效",
    "MATCH_OVERFLOW": "撮合金额超过订单剩余金额",
    "ACCOUNT_NOT_FOUND": "账户不存在",
    "INSUFFICIENT_BALANCE": "余额不足",
    "WITHDRAWAL_INVALID": "提现申请无效",
    "WITHDRAWAL_LIMIT_EXCEEDED": "超出提现限额",
    "RISK_REVIEW_REQUIRED": "该操作需要风控审核",
    "VALIDATION_ERROR": "参数校验失败",
    "INTERNAL_ERROR": "系统繁忙，请稍后重试",
    "RATE_LIMITED": "请求过于频繁",
}


def _request_id() -> str:
    return f"req_{uuid.uuid4().hex[:20]}"


def success(data: Any = None, message: str = "success") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data, "requestId": _request_id()}


def fail(
    code: str = "INTERNAL_ERROR", message: str | None = None, data: Any = None
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message or _CODE_MESSAGE.get(code, code),
        "data": data,
        "requestId": _request_id(),
    }


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    e = cast(AppError, exc)
    return JSONResponse(
        status_code=e.status_code,
        content=fail(e.code, e.message),
    )


async def auth_error_handler(request: Request, exc: Exception) -> JSONResponse:
    e = cast(AuthError, exc)
    return JSONResponse(
        status_code=e.status_code,
        content=fail(e.code, e.message),
    )


async def permission_error_handler(request: Request, exc: Exception) -> JSONResponse:
    e = cast(PermissionDeniedError, exc)
    return JSONResponse(
        status_code=e.status_code,
        content=fail(e.code, e.message),
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=fail("VALIDATION_ERROR", "参数校验失败", getattr(exc, "errors", lambda: None)()),
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=fail("INTERNAL_ERROR", "系统繁忙，请稍后重试"),
    )
