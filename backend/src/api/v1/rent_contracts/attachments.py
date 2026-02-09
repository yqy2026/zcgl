"""
合同附件管理模块
"""

import logging
from pathlib import Path
from typing import Any
from typing import Any as AnyType

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import BaseBusinessError, internal_error, not_found
from ....database import get_async_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....services.rent_contract import rent_contract_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/{contract_id}/attachments",
    response_model=dict[str, AnyType],
    summary="上传合同附件",
)
async def upload_contract_attachment(
    contract_id: str,
    file: UploadFile = File(..., description="附件文件"),
    file_type: str = Form("other", description="文件类型: contract_scan/id_card/other"),
    description: str | None = Form(None, description="附件描述"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, AnyType]:
    """
    上传合同附件

    支持的文件类型:
    - PDF (.pdf)
    - 图片 (.jpg, .jpeg, .png)
    - Word文档 (.doc, .docx)
    """

    try:
        result = await rent_contract_service.upload_contract_attachment_async(
            db,
            contract_id=contract_id,
            file=file,
            file_type=file_type,
            description=description,
            uploader_id=current_user.id,
            uploader_name=current_user.full_name or current_user.username,
        )
        return result
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"上传合同附件失败: {str(e)}")


@router.get(
    "/{contract_id}/attachments",
    response_model=list[Any],
    summary="获取合同附件列表",
)
async def get_contract_attachments(
    contract_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[dict[str, Any]]:
    """
    获取指定合同的所有附件
    """

    try:
        contract = await rent_contract_service.get_contract_by_id_async(
            db=db,
            contract_id=contract_id,
        )
        if not contract:
            raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)
        attachments = await rent_contract_service.get_contract_attachments_async(
            db=db,
            contract_id=contract_id,
        )

        return [
            {
                "id": a.id,
                "file_name": a.file_name,
                "file_size": a.file_size,
                "file_type": a.file_type,
                "mime_type": a.mime_type,
                "description": a.description,
                "uploader": a.uploader,
                "uploaded_at": a.created_at.isoformat(),
            }
            for a in attachments
        ]
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取合同附件列表失败: {str(e)}")


@router.get(
    "/{contract_id}/attachments/{attachment_id}/download",
    summary="下载合同附件",
)
async def download_contract_attachment(
    contract_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> FileResponse:
    """
    下载指定的合同附件
    """
    try:
        attachment = await rent_contract_service.get_contract_attachment_async(
            db=db,
            attachment_id=attachment_id,
            contract_id=contract_id,
        )
        if not attachment:
            raise not_found(
                "附件不存在", resource_type="attachment", resource_id=attachment_id
            )

        file_path = Path(attachment.file_path)
        if not file_path.exists():
            raise not_found("文件不存在", resource_type="file", resource_id=str(file_path))

        return FileResponse(
            path=str(file_path),
            filename=attachment.file_name,
            media_type=attachment.mime_type or "application/octet-stream",
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"下载合同附件失败: {str(e)}")


@router.delete(
    "/{contract_id}/attachments/{attachment_id}",
    response_model=dict[str, Any],
    summary="删除合同附件",
)
async def delete_contract_attachment(
    contract_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """
    删除指定的合同附件
    """
    try:
        attachment = await rent_contract_service.get_contract_attachment_async(
            db=db,
            attachment_id=attachment_id,
            contract_id=contract_id,
        )
        if not attachment:
            raise not_found(
                "附件不存在", resource_type="attachment", resource_id=attachment_id
            )

        file_path = Path(attachment.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete file {file_path}: {e}")

        await rent_contract_service.delete_contract_attachment_async(
            db=db,
            attachment=attachment,
        )
        return {"message": "附件已删除"}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"删除合同附件失败: {str(e)}")
