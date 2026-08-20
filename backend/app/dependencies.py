"""通用依赖：分页、限流、幂等。"""

from __future__ import annotations

from fastapi import Header, Query, Request

from app.core.exceptions import AppError
from app.schemas.common import PageParams
from app.utils.redis_client import redis_client


def get_page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


def get_idempotency_key(idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> str | None:
    return idempotency_key


async def rate_limit(request: Request, limit: int = 60, window: int = 60) -> None:
    """按 IP 限流。"""
    key = f"rl:{request.client.host if request.client else 'unknown'}:{request.url.path}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, window)
    if count > limit:
        raise AppError("RATE_LIMITED", "请求过于频繁，请稍后再试")


class RateLimiter:
    def __init__(self, limit: int = 60, window: int = 60) -> None:
        self.limit = limit
        self.window = window

    async def __call__(self, request: Request) -> None:
        await rate_limit(request, self.limit, self.window)
