"""邀请码单元测试。"""

from __future__ import annotations

import pytest
from app.core.exceptions import AppError
from app.database import SessionLocal
from app.services.invite_service import create_invite_codes, use_invite_code


def test_create_and_use_invite():
    import asyncio


    async def _main() -> None:
        async with SessionLocal() as db:
            codes = await create_invite_codes(db, 1, 2)
            assert len(codes) == 2
            assert codes[0].status == "ACTIVE"
            used = await use_invite_code(db, codes[0].code)
            assert used.status == "ACTIVE"

            # 账号专属邀请码可复用，重复使用不报错
            again = await use_invite_code(db, codes[0].code)
            assert again.code == codes[0].code
            await db.rollback()

    asyncio.run(_main())


def test_invalid_invite_rejected():
    import asyncio

    async def _main() -> None:
        async with SessionLocal() as db:
            with pytest.raises(AppError):
                await use_invite_code(db, "NO_SUCH_CODE")
            await db.rollback()

    asyncio.run(_main())
