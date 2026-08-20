"""pytest 配置与共享 Fixture：使用独立 SQLite + 内存 Redis。"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

_TEST_DIR = tempfile.mkdtemp(prefix="lx_test_")
os.environ["SQLITE_PATH"] = os.path.join(_TEST_DIR, "test.db")
os.environ["MYSQL_HOST"] = ""
os.environ["REDIS_HOST"] = ""
os.environ["DEBUG"] = "false"
os.environ["APP_ENV"] = "test"
os.environ["MATCH_SCAN_INTERVAL"] = "60"

from app import models  # noqa: E402, F401
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db(client):
    """每个测试前清空业务表、重置内存 Redis 并重新种子。"""
    async def _reset() -> None:
        async with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
        from app.seed import run_seed
        from app.utils.redis_client import redis_client

        await redis_client.flush()
        async with SessionLocal() as db:
            await run_seed(db)

    _run(_reset())
    yield


def get_system_invite_code() -> str:
    """从种子数据取一个系统邀请码（creator_id 为空表示系统发放）。"""
    from app.models.invite import InviteCode

    async def _get() -> str:
        from sqlalchemy import select

        async with SessionLocal() as db:
            code = await db.scalar(
                select(InviteCode)
                .where(InviteCode.creator_id.is_(None), InviteCode.status == "ACTIVE")
                .limit(1)
            )
            return code.code if code else ""

    return _run(_get())


def register_user(client: TestClient, username: str, password: str = "Passw0rd") -> str:
    """按账号注册并返回 access_token。"""
    invite = get_system_invite_code()
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "invite_code": invite,
            "password": password,
            "nickname": f"user_{username}",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def invite_code():
    return get_system_invite_code()
