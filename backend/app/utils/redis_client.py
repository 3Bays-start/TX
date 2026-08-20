"""Redis 客户端，带进程内降级实现（无 Redis 时仍可用锁/缓存/限流）。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.config import settings
from app.core.logging import get_logger

logger = get_logger("redis")


class MemoryRedis:
    """进程内 Redis 兼容层，用于本地无 Redis 环境。"""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._locks: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def clear(self) -> None:
        self._data.clear()
        self._locks.clear()

    async def get(self, key: str) -> str | None:
        val = self._data.get(key)
        return val if val is not None else None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._data[key] = value
        if ex:
            asyncio.get_running_loop().call_later(ex, self._expire, key)

    def _expire(self, key: str) -> None:
        self._data.pop(key, None)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._locks.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._data

    async def incr(self, key: str, amount: int = 1) -> int:
        val = int(self._data.get(key, "0")) + amount
        self._data[key] = str(val)
        return val

    async def expire(self, key: str, seconds: int) -> None:
        if key in self._data:
            asyncio.get_running_loop().call_later(seconds, self._expire, key)

    async def acquire_lock(self, key: str, timeout: int = 10, token: str | None = None) -> bool:  # noqa: ASYNC109  lock TTL, not timeout
        token = token or str(uuid.uuid4())
        async with self._lock:
            if self._locks.get(key) is None:
                self._locks[key] = token
                asyncio.get_running_loop().call_later(timeout, self._release_lock, key, token)
                return True
            return False

    def _release_lock(self, key: str, token: str) -> None:
        if self._locks.get(key) == token:
            self._locks.pop(key, None)

    async def release_lock(self, key: str, token: str) -> None:
        self._release_lock(key, token)


class RedisClient:
    """封装真实 redis 与内存降级，对外统一异步接口。"""

    def __init__(self) -> None:
        self._memory = MemoryRedis()
        self._client: Any = None
        self._ready = False

    async def connect(self) -> None:
        if not settings.REDIS_HOST:
            self._ready = False
            logger.warning("REDIS_HOST 未配置，使用进程内降级实现")
            return
        try:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=2
            )
            await self._client.ping()
            self._ready = True
        except Exception as exc:  # noqa: BLE001
            self._ready = False
            logger.warning("Redis 连接失败，使用进程内降级实现: %s", exc)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def get(self, key: str) -> str | None:
        if self._ready:
            return await self._client.get(key)
        return await self._memory.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if self._ready:
            await self._client.set(key, value, ex=ex)
        else:
            await self._memory.set(key, value, ex=ex)

    async def delete(self, key: str) -> None:
        if self._ready:
            await self._client.delete(key)
        else:
            await self._memory.delete(key)

    async def exists(self, key: str) -> bool:
        if self._ready:
            return bool(await self._client.exists(key))
        return await self._memory.exists(key)

    async def incr(self, key: str, amount: int = 1) -> int:
        if self._ready:
            return int(await self._client.incr(key, amount))
        return await self._memory.incr(key, amount)

    async def expire(self, key: str, seconds: int) -> None:
        if self._ready:
            await self._client.expire(key, seconds)
        else:
            await self._memory.expire(key, seconds)

    async def acquire_lock(self, key: str, timeout: int = 10) -> str | None:  # noqa: ASYNC109  lock TTL, not timeout
        """返回锁 token，获取失败返回 None。"""
        token = str(uuid.uuid4())
        if self._ready:
            ok = await self._client.set(key, token, nx=True, ex=timeout)
            return token if ok else None
        ok = await self._memory.acquire_lock(key, timeout, token)
        return token if ok else None

    async def release_lock(self, key: str, token: str) -> None:
        if self._ready:
            await self._client.delete(key)
        else:
            await self._memory.release_lock(key, token)

    async def flush(self) -> None:
        """清空全部数据（测试用）。"""
        if self._ready:
            await self._client.flushdb()
        else:
            await self._memory.clear()


redis_client = RedisClient()


async def with_lock(key: str, timeout: int = 10, wait: float = 0.1) -> None:  # noqa: ASYNC109  lock TTL, not timeout
    """阻塞式获取分布式锁，配合上下文使用。"""


class LockContext:
    def __init__(self, key: str, timeout: int = 10, retries: int = 30, wait: float = 0.1) -> None:
        self.key = key
        self.timeout = timeout
        self.retries = retries
        self.wait = wait
        self.token: str | None = None

    async def __aenter__(self) -> LockContext:
        for _ in range(self.retries):
            self.token = await redis_client.acquire_lock(self.key, self.timeout)
            if self.token:
                return self
            await asyncio.sleep(self.wait)
        raise TimeoutError(f"获取锁超时: {self.key}")

    async def __aexit__(self, *exc: object) -> None:
        if self.token:
            await redis_client.release_lock(self.key, self.token)
