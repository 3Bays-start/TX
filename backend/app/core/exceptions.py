"""业务异常与全局异常处理。"""

from __future__ import annotations


class AppError(Exception):
    """业务异常基类，携带错误码与消息。"""

    code: str = "INTERNAL_ERROR"
    status_code: int = 400

    def __init__(self, code: str = "", message: str = "") -> None:
        resolved = message or getattr(self, "message", "") or code or self.code
        super().__init__(resolved)
        self.code = code or self.code
        self.message = resolved


class AuthError(AppError):
    code = "AUTH_INVALID"
    status_code = 401


class TokenExpiredError(AuthError):
    code = "TOKEN_EXPIRED"


class PermissionDeniedError(AppError):
    code = "PERMISSION_DENIED"
    status_code = 403


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class InvalidStatusError(AppError):
    code = "ORDER_INVALID_STATUS"
    message = "订单当前状态不允许此操作"


class InsufficientBalanceError(AppError):
    code = "INSUFFICIENT_BALANCE"
    message = "余额不足，请先充值"


class RiskReviewRequiredError(AppError):
    code = "RISK_REVIEW_REQUIRED"
    status_code = 403


class UserDisabledError(AppError):
    code = "USER_DISABLED"
    status_code = 403


class UserFrozenError(AppError):
    code = "USER_FROZEN"
    status_code = 403
