"""审计日志写入助手。"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import request_id_var
from app.models.audit import OperationLog


async def write_operation_log(
    db: AsyncSession,
    action: str,
    module: str = "",
    operator_type: str = "ADMIN",
    operator_id: int | None = None,
    target_type: str = "",
    target_id: int | None = None,
    before_data: Any = None,
    after_data: Any = None,
    reason: str = "",
    ip: str = "",
    user_agent: str = "",
) -> OperationLog:
    def _dumps(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        try:
            return json.dumps(v, ensure_ascii=False, default=str)
        except TypeError:
            return str(v)

    log = OperationLog(
        operator_type=operator_type,
        operator_id=operator_id,
        action=action,
        module=module,
        target_type=target_type,
        target_id=target_id,
        before_data=_dumps(before_data),
        after_data=_dumps(after_data),
        reason=reason,
        ip=ip,
        user_agent=user_agent,
        request_id=request_id_var.get(),
    )
    db.add(log)
    await db.flush()
    return log
