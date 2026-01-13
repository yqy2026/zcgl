"""
资产附件管理API路由模块

从 assets.py 中提取的附件管理相关端点
"""

import os
import shutil
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.exception_handler import ResourceNotFoundError
from ...crud.asset import asset_crud
from ...database import get_db
from ...middleware.auth import get_current_active_user, require_permission
from ...models.auth import User

# 创建附件路由器
router = APIRouter()


@router.post("/{asset_id}/attachments", summary="上传资产附件")
async def upload_asset_attachments(
    asset_id: str = Path(..., description="资产ID"),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
) -> dict[str, Any]:
    """
    上传资产附件（PDF格式）

    - **asset_id**: 资产ID
    - **files**: 要上传的文件列表
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 创建附件目录 - 安全处理
        from ...utils.file_security import (
            create_safe_upload_directory,
            validate_upload_file,
        )

        upload_dir = create_safe_upload_directory("uploads/attachments", asset_id)

        success_files = []
        failed_files = []

        for file in files:
            try:
                # 综合验证文件安全性
                file.file.seek(0, 2)  # 移动到文件末尾
                file_size = file.file.tell()
                file.file.seek(0)  # 重置到文件开头

                validation_result = validate_upload_file(
                    filename=file.filename,
                    content_type=file.content_type,
                    file_size=file_size,
                    allowed_extensions=["pdf"],
                    max_size=10 * 1024 * 1024,  # 10MB
                )

                if not validation_result["valid"]:
                    failed_files.append(
                        f"{file.filename}: {', '.join(validation_result['errors'])}"
                    )
                    continue

                # 生成安全的唯一文件名
                unique_filename = validation_result["safe_filename"]
                file_path = upload_dir / unique_filename

                # 保存文件
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                success_files.append(file.filename)

            except Exception as e:
                failed_files.append(f"{file.filename}: {str(e)}")

        return {
            "success": success_files,
            "failed": failed_files,
            "message": f"成功上传 {len(success_files)} 个文件，失败 {len(failed_files)} 个文件",
        }

    except ResourceNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传附件失败: {str(e)}")


@router.get("/{asset_id}/attachments", summary="获取资产附件列表")
async def get_asset_attachments(
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取资产附件列表

    - **asset_id**: 资产ID
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 获取附件目录
        upload_dir = f"uploads/attachments/{asset_id}"

        if not os.path.exists(upload_dir):
            return []

        attachments = []
        for filename in os.listdir(upload_dir):
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(upload_dir, filename)
                file_stat = os.stat(file_path)

                attachments.append(
                    {
                        "id": filename,
                        "name": filename,
                        "size": file_stat.st_size,
                        "url": f"/api/v1/assets/{asset_id}/attachments/{filename}",
                        "upload_time": file_stat.st_mtime,
                    }
                )

        return attachments

    except ResourceNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取附件列表失败: {str(e)}")


@router.get("/{asset_id}/attachments/{filename}", summary="下载资产附件")
async def download_asset_attachment(
    asset_id: str = Path(..., description="资产ID"),
    filename: str = Path(..., description="文件名"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    下载资产附件

    - **asset_id**: 资产ID
    - **filename**: 文件名
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 验证文件路径
        file_path = f"uploads/attachments/{asset_id}/{filename}"

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 验证文件类型
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="仅支持PDF文件")

        return FileResponse(file_path, filename=filename, media_type="application/pdf")

    except ResourceNotFoundError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载附件失败: {str(e)}")


@router.delete("/{asset_id}/attachments/{attachment_id}", summary="删除资产附件")
async def delete_asset_attachment(
    asset_id: str = Path(..., description="资产ID"),
    attachment_id: str = Path(..., description="附件ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "delete")),
) -> dict[str, Any]:
    """
    删除资产附件

    - **asset_id**: 资产ID
    - **attachment_id**: 附件ID（文件名）
    """
    try:
        # 检查资产是否存在
        asset = asset_crud.get(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)

        # 验证文件路径
        file_path = f"uploads/attachments/{asset_id}/{attachment_id}"

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 删除文件
        os.remove(file_path)

        return {"message": "附件删除成功"}

    except ResourceNotFoundError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除附件失败: {str(e)}")
