"""LX Platform FastAPI 应用入口。"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.config import settings
from app.core import response as resp
from app.core.exceptions import AppError, AuthError, PermissionDeniedError
from app.core.logging import admin_id_var, request_id_var, setup_logging, user_id_var
from app.database import SessionLocal, init_db
from app.seed import run_seed
from app.tasks.scheduler import start_scheduler, stop_scheduler
from app.utils.redis_client import redis_client

setup_logging(debug=settings.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_runtime_settings()
    await redis_client.connect()
    await init_db()
    async with SessionLocal() as db:
        await run_seed(db)
    start_scheduler()
    yield
    await stop_scheduler()
    await redis_client.close()


def _validate_runtime_settings() -> None:
    """生产环境禁止使用默认占位密钥与已知初始口令。"""
    if settings.APP_ENV != "production":
        return
    placeholders = [
        ("JWT_SECRET", settings.JWT_SECRET, "CHANGE_ME"),
        ("SECRET_KEY", settings.SECRET_KEY, "CHANGE_ME"),
        ("MYSQL_PASSWORD", settings.MYSQL_PASSWORD, "CHANGE_ME"),
        ("RABBITMQ_PASSWORD", settings.RABBITMQ_PASSWORD, "CHANGE_ME"),
        ("ADMIN_INIT_PASSWORD", settings.ADMIN_INIT_PASSWORD, "Admin@123456"),
    ]
    offenders = [name for name, value, marker in placeholders if marker in value]
    if offenders:
        raise RuntimeError(
            "生产环境禁止使用默认/占位密钥，请通过环境变量或 .env 设置："
            + ", ".join(offenders)
        )


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version="1.0.0",
    description="LX Platform — 订单撮合与会员服务平台 API",
    lifespan=lifespan,
)

# 上传目录静态托管 /uploads/*
_upload_dir = Path(settings.UPLOAD_DIR)
if not _upload_dir.is_absolute():
    _upload_dir = Path(__file__).resolve().parent.parent / _upload_dir
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_upload_dir), name="uploads")

# CORS：仅放行配置白名单；通配符 * 时禁止携带凭据，避免任意站点携带用户会话跨域请求
if settings.cors_allow_all:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id_var.set(f"req_{uuid.uuid4().hex[:20]}")
    user_id_var.set("-")
    admin_id_var.set("-")
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id_var.get()
    return response


# ===== 全局异常处理 =====
app.add_exception_handler(AppError, resp.app_error_handler)
app.add_exception_handler(AuthError, resp.auth_error_handler)
app.add_exception_handler(PermissionDeniedError, resp.permission_error_handler)
app.add_exception_handler(RequestValidationError, resp.validation_error_handler)
app.add_exception_handler(Exception, resp.http_error_handler)


@app.get("/health")
async def health():
    return resp.success({"status": "ok", "app": settings.APP_NAME})


app.include_router(api_router)
