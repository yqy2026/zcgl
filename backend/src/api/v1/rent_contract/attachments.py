"""
合同附件管理模块
"""

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ....core.exception_handler import bad_request, internal_error, not_found
from ....crud.rent_contract import rent_contract
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/{contract_id}/attachments", response_model=dict[str, Any], summary="上传合同附件"
)
async def upload_contract_attachment(
    contract_id: str,
    file: UploadFile = File(..., description="附件文件"),
    file_type: str = Form("other", description="文件类型: contract_scan/id_card/other"),
    description: str | None = Form(None, description="附件描述"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    上传合同附件

    支持的文件类型:
    - PDF (.pdf)
    - 图片 (.jpg, .jpeg, .png)
    - Word文档 (.doc, .docx)
    """
    from ....models.rent_contract import RentContractAttachment

    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)

    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""

    if file_ext not in allowed_extensions:
        raise bad_request(
            f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(allowed_extensions)}"
        )

    upload_dir = Path("uploads/contracts")
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        file_size = len(contents)
    except Exception as e:
        raise internal_error(f"文件保存失败: {str(e)}")

    attachment = RentContractAttachment(
        contract_id=contract_id,
        file_name=file.filename or "unnamed",
        file_path=str(file_path),
        file_size=file_size,
        mime_type=file.content_type,
        file_type=file_type,
        description=description,
        uploader=current_user.full_name or current_user.username,
        uploader_id=current_user.id,
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "file_size": attachment.file_size,
        "file_type": attachment.file_type,
        "description": attachment.description,
        "uploaded_at": attachment.created_at.isoformat(),
    }


@router.get(
    "/{contract_id}/attachments", response_model=list[Any], summary="获取合同附件列表"
)
async def get_contract_attachments(
    contract_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    获取指定合同的所有附件
    """
    from ....models.rent_contract import RentContractAttachment

    contract = rent_contract.get(db, id=contract_id)
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)

    attachments = (
        db.query(RentContractAttachment)
        .filter(RentContractAttachment.contract_id == contract_id)
        .order_by(RentContractAttachment.created_at.desc())
        .all()
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


@router.get(
    "/{contract_id}/attachments/{attachment_id}/download", summary="下载合同附件"
)
async def download_contract_attachment(
    contract_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    下载指定的合同附件
    """
    from ....models.rent_contract import RentContractAttachment

    attachment = (
        db.query(RentContractAttachment)
        .filter(
            RentContractAttachment.id == attachment_id,
            RentContractAttachment.contract_id == contract_id,
        )
        .first()
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


@router.delete(
    "/{contract_id}/attachments/{attachment_id}",
    response_model=dict[str, Any],
    summary="删除合同附件",
)
async def delete_contract_attachment(
    contract_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    删除指定的合同附件
    """
    from ....models.rent_contract import RentContractAttachment

    attachment = (
        db.query(RentContractAttachment)
        .filter(
            RentContractAttachment.id == attachment_id,
            RentContractAttachment.contract_id == contract_id,
        )
        .first()
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

    db.delete(attachment)
    db.commit()

    return {"message": "附件已删除"}
