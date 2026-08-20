"""文件上传接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.response import success
from app.services import auth_service, upload_service

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(auth_service.get_current_user),
):
    url = await upload_service.save_upload(file, current_user.id)
    return success({"url": url, "filename": file.filename}, "上传成功")
