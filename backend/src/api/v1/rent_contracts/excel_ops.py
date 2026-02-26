"""
合同Excel导入导出模块
"""

import logging
import os
import tempfile
import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....constants.message_constants import ErrorIDs
from ....core.exception_handler import (
    BaseBusinessError,
    BusinessValidationError,
    bad_request,
    forbidden,
    internal_error,
    service_unavailable,
)
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....services.authz import authz_service
from ....utils.file_security import generate_safe_filename

logger = logging.getLogger(__name__)

router = APIRouter()
_CONTRACT_BULK_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:rent_contract:bulk_create"

if TYPE_CHECKING:
    from ....services.document.rent_contract_excel import RentContractExcelService

# 尝试导入Excel服务
rent_contract_excel_service: "RentContractExcelService | None"
try:
    from ....services.document.rent_contract_excel import (
        rent_contract_excel_service as _rent_contract_excel_service,
    )

    rent_contract_excel_service = _rent_contract_excel_service
    EXCEL_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.error(
        "无法导入rent_contract_excel_service，可能缺少依赖",
        extra={
            "error_id": ErrorIDs.System.RESOURCE_EXHAUSTED,
            "import_error": str(e),
        },
    )
    rent_contract_excel_service = None
    EXCEL_SERVICE_AVAILABLE = False
except SyntaxError as e:
    logger.critical(
        "rent_contract_excel_service存在语法错误",
        extra={
            "error_id": ErrorIDs.System.RESOURCE_EXHAUSTED,
            "syntax_error": str(e),
        },
    )
    rent_contract_excel_service = None
    EXCEL_SERVICE_AVAILABLE = False


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def _normalize_identifier_sequence(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized_values: list[str] = []
    for value in values:
        normalized = _normalize_optional_str(value)
        if normalized is None:
            continue
        normalized_values.append(normalized)
    return normalized_values


def _resolve_authz_scope_party_ids(
    *,
    authz_ctx: Any,
    field: str,
    list_field: str,
) -> list[str]:
    if not isinstance(authz_ctx, AuthzContext):
        return []
    scope_ids = _normalize_identifier_sequence(
        authz_ctx.resource_context.get(list_field),
    )
    if scope_ids:
        return scope_ids
    scoped_party_id = _normalize_optional_str(authz_ctx.resource_context.get(field))
    if scoped_party_id is None:
        return []
    return [scoped_party_id]


def _resolve_current_user_organization_id(current_user: User) -> str | None:
    return _normalize_optional_str(getattr(current_user, "default_organization_id", None))


async def _resolve_organization_party_id(
    *,
    db: AsyncSession,
    organization_id: str | None,
) -> str | None:
    normalized_organization_id = _normalize_optional_str(organization_id)
    if normalized_organization_id is None:
        return None

    from ....models.party import Party, PartyType

    stmt = (
        select(Party.id.label("party_id"))
        .where(
            Party.party_type == PartyType.ORGANIZATION.value,
            or_(
                Party.id == normalized_organization_id,
                Party.external_ref == normalized_organization_id,
            ),
        )
        .order_by(Party.id)
        .limit(1)
    )
    row = (await db.execute(stmt)).mappings().one_or_none()
    return _normalize_optional_str(row.get("party_id") if row is not None else None)


async def _require_contract_bulk_create_authz(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resource_context: dict[str, Any] = {}
    organization_id = _resolve_current_user_organization_id(current_user)
    if organization_id is not None:
        resource_context["organization_id"] = organization_id
        scoped_party_id = await _resolve_organization_party_id(
            db=db,
            organization_id=organization_id,
        )
        resolved_party_id = (
            scoped_party_id if scoped_party_id is not None else organization_id
        )
        resource_context["party_id"] = resolved_party_id
        resource_context["owner_party_id"] = resolved_party_id
        resource_context["manager_party_id"] = resolved_party_id
    else:
        resource_context["party_id"] = _CONTRACT_BULK_CREATE_UNSCOPED_PARTY_ID
        resource_context["owner_party_id"] = _CONTRACT_BULK_CREATE_UNSCOPED_PARTY_ID
        resource_context["manager_party_id"] = _CONTRACT_BULK_CREATE_UNSCOPED_PARTY_ID

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="rent_contract",
            action="create",
            resource_id=None,
            resource=resource_context,
        )
    except Exception:
        raise forbidden("权限校验失败")

    if not decision.allowed:
        raise forbidden("权限不足")

    return AuthzContext(
        current_user=current_user,
        action="create",
        resource_type="rent_contract",
        resource_id=None,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


@router.get("/excel/template", summary="下载Excel导入模板")
async def download_excel_template(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
) -> FileResponse:
    """
    下载租金合同Excel导入模板
    """
    if not EXCEL_SERVICE_AVAILABLE or rent_contract_excel_service is None:
        raise service_unavailable("Excel服务不可用")
    assert rent_contract_excel_service is not None

    try:
        result = rent_contract_excel_service.download_contract_template()
        if not result["success"]:
            raise internal_error(result["message"])

        return FileResponse(
            result["file_path"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=result["file_name"],
        )
    except BaseBusinessError:
        raise
    except Exception as e:
        logger.error(
            "下载模板时发生未预期错误",
            exc_info=True,
            extra={
                "error_id": ErrorIDs.Excel.TEMPLATE_DOWNLOAD_ERROR,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise internal_error(f"下载模板失败: {str(e)}")


@router.post("/excel/import", summary="Excel导入合同数据")
async def import_contracts_from_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_contract_bulk_create_authz),
    db: AsyncSession = Depends(get_async_db),
    should_import_terms: bool = Form(True, description="是否导入租金条款"),
    should_import_ledger: bool = Form(False, description="是否导入台账数据"),
    should_overwrite_existing: bool = Form(False, description="是否覆盖已存在的数据"),
) -> dict[str, Any]:
    """
    从Excel文件导入租金合同数据
    """
    if not EXCEL_SERVICE_AVAILABLE or rent_contract_excel_service is None:
        raise service_unavailable("Excel服务不可用")
    assert rent_contract_excel_service is not None

    try:
        temp_dir = tempfile.gettempdir()
        try:
            safe_filename = generate_safe_filename(
                file.filename or "upload.xlsx",
                prefix=str(uuid.uuid4()),
                allowed_extensions=["xlsx", "xls"],
            )
        except BusinessValidationError as e:
            raise bad_request(str(e))

        file_path = os.path.join(temp_dir, safe_filename)

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        result = await rent_contract_excel_service.import_contracts_from_excel(
            db=db,
            file_path=file_path,
            import_terms=should_import_terms,
            import_ledger=should_import_ledger,
            overwrite_existing=should_overwrite_existing,
        )

        rent_contract_excel_service.cleanup_file(file_path)

        return result

    except BaseBusinessError:
        raise
    except Exception as e:
        logger.error(
            "导入合同时发生未预期错误",
            exc_info=True,
            extra={
                "error_id": ErrorIDs.Excel.IMPORT_FAILED,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise internal_error(f"导入失败: {str(e)}")


@router.get("/excel/export", summary="Excel导出合同数据")
async def export_contracts_to_excel(
    contract_ids: list[str] | None = Query(None, description="要导出的合同ID列表"),
    current_user: User = Depends(get_current_active_user),
    authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
    db: AsyncSession = Depends(get_async_db),
    should_include_terms: bool = Query(True, description="是否包含租金条款"),
    should_include_ledger: bool = Query(True, description="是否包含台账数据"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
) -> FileResponse:
    """
    导出租金合同数据到Excel文件
    """
    if not EXCEL_SERVICE_AVAILABLE or rent_contract_excel_service is None:
        raise service_unavailable("Excel服务不可用")
    assert rent_contract_excel_service is not None

    scoped_owner_party_ids = _resolve_authz_scope_party_ids(
        authz_ctx=authz_ctx,
        field="owner_party_id",
        list_field="owner_party_ids",
    )
    scoped_manager_party_ids = _resolve_authz_scope_party_ids(
        authz_ctx=authz_ctx,
        field="manager_party_id",
        list_field="manager_party_ids",
    )
    scoped_owner_party_id = scoped_owner_party_ids[0] if scoped_owner_party_ids else None
    scoped_manager_party_id = (
        scoped_manager_party_ids[0] if scoped_manager_party_ids else None
    )

    try:
        result = await rent_contract_excel_service.export_contracts_to_excel(
            db=db,
            contract_ids=contract_ids,
            include_terms=should_include_terms,
            include_ledger=should_include_ledger,
            start_date=start_date,
            end_date=end_date,
            owner_party_id=scoped_owner_party_id,
            manager_party_id=scoped_manager_party_id,
            owner_party_ids=scoped_owner_party_ids or None,
            manager_party_ids=scoped_manager_party_ids or None,
        )

        if not result["success"]:
            raise internal_error(result["message"])

        return FileResponse(
            result["file_path"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=result["file_name"],
        )

    except BaseBusinessError:
        raise
    except Exception as e:
        logger.error(
            "导出合同时发生未预期错误",
            exc_info=True,
            extra={
                "error_id": ErrorIDs.Excel.EXPORT_FAILED,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise internal_error(f"导出失败: {str(e)}")
