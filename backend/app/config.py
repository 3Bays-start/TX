"""LX Platform 后端配置。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_NAME: str = "lx-platform"
    DEBUG: bool = True
    SECRET_KEY: str = "CHANGE_ME_STRONG_SECRET"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    MYSQL_HOST: str = ""
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "lx_platform"
    MYSQL_USER: str = "lx_app"
    MYSQL_PASSWORD: str = "CHANGE_ME"

    # Redis
    REDIS_HOST: str = ""
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # RabbitMQ / Celery
    CELERY_ENABLED: bool = False
    RABBITMQ_HOST: str = ""
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "lx"
    RABBITMQ_PASSWORD: str = "CHANGE_ME"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # JWT
    JWT_SECRET: str = "CHANGE_ME_CHANGE_ME_CHANGE_ME_CHANGE_ME_1234567890"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE: int = 7200
    JWT_REFRESH_EXPIRE: int = 2592000

    # Upload
    UPLOAD_MAX_SIZE: int = 10485760
    UPLOAD_ALLOWED_EXT: str = "jpg,jpeg,png,pdf,webp"
    UPLOAD_DIR: str = "uploads"
    # 上传文件对外可访问的 URL 前缀（后端静态托管 /uploads/*）
    UPLOAD_URL_PREFIX: str = "/uploads"

    # 初始超级管理员
    ADMIN_INIT_USERNAME: str = "superadmin"
    ADMIN_INIT_PASSWORD: str = "Admin@123456"

    # SQLite 文件路径覆盖（测试用）
    SQLITE_PATH: str = ""

    # 平台配置默认值
    DEFAULT_SERVICE_FEE_RATE: float = 0.05
    WITHDRAW_MIN_AMOUNT: float = 100
    WITHDRAW_DAILY_LIMIT: float = 50000

    # 安全
    # 生产必须配置为具体的前端域名白名单（逗号分隔）；dev 默认放行本地三端
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:5174,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174"
    )
    # 是否位于可信反向代理（nginx）之后，决定是否信任 X-Forwarded-For 提取客户端 IP
    TRUSTED_PROXY: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def cors_allow_all(self) -> bool:
        return "*" in self.cors_origins

    # 撮合扫描间隔（秒），开发环境缩短便于观察，生产为 24h=86400
    MATCH_SCAN_INTERVAL: int = 60
    MATCH_SCAN_INTERVAL_PROD: int = 86400

    @property
    def sqlite_url(self) -> str:
        path = self.SQLITE_PATH or str(BASE_DIR / "lx_platform.db")
        return f"sqlite+aiosqlite:///{path}"

    @property
    def mysql_url(self) -> str:
        return (
            "mysql+asyncmy://"
            f"{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    @property
    def database_url(self) -> str:
        if self.MYSQL_HOST:
            return self.mysql_url
        return self.sqlite_url

    @property
    def is_sqlite(self) -> bool:
        return not bool(self.MYSQL_HOST)

    @property
    def redis_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def broker_url(self) -> str:
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        auth = f"{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@"
        return f"amqp://{auth}{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"

    @property
    def match_scan_interval(self) -> int:
        if self.APP_ENV == "production":
            return self.MATCH_SCAN_INTERVAL_PROD
        return self.MATCH_SCAN_INTERVAL


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
