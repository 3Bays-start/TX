"""文件上传服务：校验扩展名/大小，按用户目录隔离存储。"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import BASE_DIR, settings
from app.core.exceptions import AppError

_CHUNK = 1024 * 1024
_ALLOWED = {ext.strip().lower() for ext in settings.UPLOAD_ALLOWED_EXT.split(",") if ext.strip()}


def _upload_root() -> Path:
    path = Path(settings.UPLOAD_DIR)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def _ext_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def save_upload(file: UploadFile, user_id: int) -> str:
    """保存上传文件，返回可访问的相对 URL（如 /uploads/12/ab12...png）。"""
    ext = _ext_of(file.filename or "")
    if ext not in _ALLOWED:
        raise AppError("FILE_TYPE_NOT_ALLOWED", f"仅支持上传 {settings.UPLOAD_ALLOWED_EXT} 格式")

    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        size += len(chunk)
        if size > settings.UPLOAD_MAX_SIZE:
            raise AppError(
                "FILE_TOO_LARGE",
                f"文件大小不能超过 {settings.UPLOAD_MAX_SIZE // 1024 // 1024}MB",
            )
        chunks.append(chunk)
    if size == 0:
        raise AppError("FILE_EMPTY", "不能上传空文件")

    stored = f"{uuid.uuid4().hex}.{ext}"
    target_dir = _upload_root() / str(user_id)
    target = target_dir / stored

    def _write() -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as fh:
            for chunk in chunks:
                fh.write(chunk)

    await asyncio.to_thread(_write)
    return f"{settings.UPLOAD_URL_PREFIX}/{user_id}/{stored}"
