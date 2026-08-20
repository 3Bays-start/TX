"""进程内后台调度（无 RabbitMQ 时兜底）。撮合仅由管理后台触发，不做自动扫描。"""

from __future__ import annotations

import asyncio

from app.config import settings
from app.core.logging import get_logger

logger = get_logger("scheduler")

_running = False


async def scheduler_loop() -> None:
    """降级调度器：占位循环（撮合仅后台触发，无自动任务）。"""
    global _running
    if _running:
        return
    _running = True
    interval = settings.match_scan_interval
    logger.info("进程内调度器启动，间隔 %s 秒（撮合仅后台触发）", interval)
    while _running:
        try:
            await asyncio.sleep(interval)
            logger.info("调度器心跳，无自动撮合任务")
        except asyncio.CancelledError:
            break
        except Exception as exc:  # noqa: BLE001
            logger.exception("调度器执行失败: %s", exc)


async def stop_scheduler() -> None:
    global _running
    _running = False


def start_scheduler() -> None:
    from app.utils.redis_client import redis_client

    if settings.CELERY_ENABLED:
        logger.info("CELERY_ENABLED=true，跳过进程内调度器")
        return
    if redis_client._ready:  # noqa: SLF001
        logger.info("使用外部 Redis，仍启用进程内调度器兜底")
    asyncio.create_task(scheduler_loop())
