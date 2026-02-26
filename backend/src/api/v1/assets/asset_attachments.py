import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    InvalidRequestError,
    ResourceNotFoundError,
    internal_error,
)
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....services.asset.asset_service import AsyncAssetService
from ....utils import file_security

router = APIRouter()


class AssetCRUD:
    """资产查询兼容适配器（内部委托服务层）。"""

    async def get_async(self, *, db: AsyncSession, id: str) -> Any:
        asset_service = AsyncAssetService(db)
        return await asset_service.get_asset(id)


# 兼容旧单测 patch 点；实现已不直连 CRUD。
asset_crud: Any = AssetCRUD()


def _get_asset_lookup() -> Any:
    return asset_crud


def _resolve_attachment_path(asset_id: str, filename: str) -> Path:
    """Resolve a safe attachment path under the asset directory."""
    base_dir = Path("uploads") / "attachments" / asset_id
    safe_name = file_security.secure_filename(filename)
    file_path = (base_dir / safe_name).resolve()
    base_dir_resolved = base_dir.resolve()
    try:
        file_path.relative_to(base_dir_resolved)
    except ValueError:
        raise InvalidRequestError("非法文件路径")
    return file_path


@router.post(
    "/{asset_id}/attachments",
    response_model=dict[str, Any],
    summary="上传资产附件",
)
async def upload_asset_attachments(
    asset_id: str,
    files: list[UploadFile] = File(..., description="附件文件列表"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
) -> dict[str, Any]:
    try:
        asset_lookup = _get_asset_lookup()
        asset = await asset_lookup.get_async(db=db, id=asset_id)
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
                content = await file.read()
                file_size = len(content)
                await file.seek(0)
            except Exception:
                content = b""
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
                with open(file_path, "wb") as target:
                    target.write(content)
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
            resource_id="{asset_id}",
            deny_as_not_found=True,
        )
    ),
) -> list[dict[str, Any]]:
    try:
        asset_lookup = _get_asset_lookup()
        asset = await asset_lookup.get_async(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("asset", asset_id)

        base_dir = Path("uploads") / "attachments" / asset_id
        if not base_dir.exists():
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
            resource_id="{asset_id}",
            deny_as_not_found=True,
        )
    ),
) -> FileResponse:
    try:
        asset_lookup = _get_asset_lookup()
        asset = await asset_lookup.get_async(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("asset", asset_id)

        if not filename.lower().endswith(".pdf"):
            raise InvalidRequestError("仅支持PDF文件")

        file_path = _resolve_attachment_path(asset_id, filename)
        if not file_path.exists():
            raise ResourceNotFoundError("attachment", filename)

        return FileResponse(
            str(file_path), filename=file_path.name, media_type="application/pdf"
        )
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
) -> dict[str, str]:
    try:
        asset_lookup = _get_asset_lookup()
        asset = await asset_lookup.get_async(db=db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("asset", asset_id)

        file_path = _resolve_attachment_path(asset_id, attachment_id)
        if not file_path.exists():
            raise ResourceNotFoundError("attachment", attachment_id)

        os.remove(file_path)
        return {"message": "附件删除成功"}
    except BaseBusinessError:
        raise
    except Exception as e:
        raise internal_error(f"删除附件失败: {str(e)}")
