import os
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ....core.exception_handler import (
    BaseBusinessError,
    InvalidRequestError,
    ResourceNotFoundError,
    internal_error,
)
from ....crud.asset import asset_crud
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....utils import file_security

router = APIRouter()


@router.post(
    "/{asset_id}/attachments",
    response_model=dict[str, Any],
    summary="上传资产附件",
)
async def upload_asset_attachments(
    asset_id: str,
    files: list[UploadFile] = File(..., description="附件文件列表"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    try:
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("asset", asset_id)

        upload_dir = file_security.create_safe_upload_directory(
            "uploads/attachments", asset_id
        )
        success: list[str] = []
        failed: list[str] = []

        for file in files:
            if not file.filename:
                failed.append("文件名不能为空")
                continue

            try:
                file.file.seek(0, 2)
                file_size = file.file.tell()
                file.file.seek(0)
            except Exception:
                file_size = 0

            validation = file_security.validate_upload_file(
                file.filename,
                file.content_type,
                file_size,
                allowed_extensions=[".pdf"],
                max_size=10 * 1024 * 1024,
            )

            if not validation["valid"]:
                errors = validation.get("errors") or []
                failed.append("; ".join(errors) if errors else "文件验证失败")
                continue

            safe_filename = validation.get("safe_filename") or file.filename
            file_path = upload_dir / safe_filename

            try:
                file.file.seek(0)
                with open(file_path, "wb") as target:
                    target.write(file.file.read())
                success.append(safe_filename)
            except Exception as e:
                failed.append(str(e))

        if success and failed:
            message = f"成功上传 {len(success)} 个文件，失败 {len(failed)} 个文件"
        elif success:
            message = f"成功上传 {len(success)} 个文件"
        else:
            message = "上传失败"

        return {"success": success, "failed": failed, "message": message}
    except BaseBusinessError:
        raise
    except Exception as e:
        raise internal_error(f"上传附件失败: {str(e)}")


@router.get(
    "/{asset_id}/attachments",
    response_model=list[dict[str, Any]],
    summary="获取资产附件列表",
)
async def get_asset_attachments(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict[str, Any]]:
    try:
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("asset", asset_id)

        base_dir = os.path.join("uploads", "attachments", asset_id)
        if not os.path.exists(base_dir):
            return []

        attachments: list[dict[str, Any]] = []
        for filename in os.listdir(base_dir):
            if not filename.lower().endswith(".pdf"):
                continue
            file_path = os.path.join(base_dir, filename)
            stat = os.stat(file_path)
            attachments.append(
                {
                    "id": filename,
                    "name": filename,
                    "size": stat.st_size,
                    "url": f"/api/v1/assets/{asset_id}/attachments/{filename}",
                    "upload_time": stat.st_mtime,
                }
            )
        return attachments
    except BaseBusinessError:
        raise
    except Exception as e:
        raise internal_error(f"获取附件列表失败: {str(e)}")


@router.get(
    "/{asset_id}/attachments/{filename}",
    summary="下载资产附件",
)
async def download_asset_attachment(
    asset_id: str,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    try:
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("asset", asset_id)

        if not filename.lower().endswith(".pdf"):
            raise InvalidRequestError("仅支持PDF文件")

        file_path = f"uploads/attachments/{asset_id}/{filename}"
        if not os.path.exists(file_path):
            raise ResourceNotFoundError("attachment", filename)

        return FileResponse(file_path, filename=filename, media_type="application/pdf")
    except BaseBusinessError:
        raise
    except Exception as e:
        raise internal_error(f"下载附件失败: {str(e)}")


@router.delete(
    "/{asset_id}/attachments/{attachment_id}",
    response_model=dict[str, str],
    summary="删除资产附件",
)
async def delete_asset_attachment(
    asset_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    try:
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("asset", asset_id)

        file_path = f"uploads/attachments/{asset_id}/{attachment_id}"
        if not os.path.exists(file_path):
            raise ResourceNotFoundError("attachment", attachment_id)

        os.remove(file_path)
        return {"message": "附件删除成功"}
    except BaseBusinessError:
        raise
    except Exception as e:
        raise internal_error(f"删除附件失败: {str(e)}")
