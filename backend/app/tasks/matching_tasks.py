"""撮合与订单相关 Celery 任务。"""

from __future__ import annotations

import asyncio


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def scan_pending_orders_task() -> dict[str, int]:
    from app.services.matching_service import scan_pending_orders

    return _run(scan_pending_orders())
