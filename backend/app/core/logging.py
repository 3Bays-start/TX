"""结构化日志，携带 request_id / user_id 等上下文。"""

from __future__ import annotations

import logging
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")
admin_id_var: ContextVar[str] = ContextVar("admin_id", default="-")


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.admin_id = admin_id_var.get()
        return True


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())
    logging.basicConfig(
        level=level,
        handlers=[handler],
        format=(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "req=%(request_id)s user=%(user_id)s admin=%(admin_id)s | %(message)s"
        ),
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
