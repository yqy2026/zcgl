"""合同台账聚合查询与重算 API。"""

from datetime import date
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    BusinessValidationError,
    internal_error,
)
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    DataScopeContext,
    get_current_active_user,
    require_authz,
    require_data_scope_context,
)
from ....models.auth import User
from ....schemas.contract_group import (
    ContractLedgerEntryResponse,
    ContractLedgerListResponse,
    LedgerAggregateQueryParams,
    LedgerCompensationResponse,
    LedgerExportQueryParams,
    LedgerFollowUpUpdateRequest,
    LedgerRecalculateResponse,
    OperationalPaymentFlowCreate,
    OperationalPaymentFlowDetailResponse,
    OperationalPaymentFlowResponse,
    PaymentAllocationResponse,
    PaymentAllocationSaveRequest,
    PaymentFlowCorrectionRequest,
    PaymentFlowLifecycleActionRequest,
    PaymentVoucherAttachmentResponse,
    PaymentVoucherDownloadAuditResponse,
    ServiceFeeGenerateRequest,
    ServiceFeeGenerateResponse,
    ServiceFeeLedgerResponse,
    ServiceFeeSourceReconcileRequest,
)
from ....security.file_validation import validate_upload_file
from ....services.contract.ledger_compensation_service import (
    ledger_compensation_service,
)
from ....services.contract.ledger_export_service import ledger_export_service
from ....services.contract.ledger_service_v2 import ledger_service_v2
from ....services.contract.payment_flow_service import payment_flow_service
from ....services.contract.payment_voucher_service import payment_voucher_service
from ....services.contract.service_fee_ledger_service import service_fee_ledger_service
from ....services.party_scope import build_party_filter_from_scope_context

router = APIRouter()

PAYMENT_VOUCHER_MAX_SIZE = 20 * 1024 * 1024
PAYMENT_VOUCHER_ALLOWED_MIME_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
]

LedgerPaymentStatus = Literal["unpaid", "paid", "partial", "voided"]
LedgerViewFilter = Literal["terminal_collection", "operator_income", "operator_cost"]


def resolve_ledger_query_params(
    ledger_view: LedgerViewFilter | None = Query(None, description="经营台账视图"),
    project_id: str | None = Query(None, description="项目 ID"),
    asset_id: str | None = Query(None, description="资产 ID"),
    party_id: str | None = Query(None, description="主体 ID"),
    contract_id: str | None = Query(None, description="合同 ID"),
    year_month_start: str | None = Query(None, description="开始账期，格式 YYYY-MM"),
    year_month_end: str | None = Query(None, description="结束账期，格式 YYYY-MM"),
    flow_occurred_on_start: date | None = Query(
        None,
        description="收付流水发生日期开始",
    ),
    flow_occurred_on_end: date | None = Query(
        None,
        description="收付流水发生日期结束",
    ),
    payment_status: str | None = Query(None, description="支付状态"),
    include_voided: bool = Query(False, description="是否包含作废条目"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    limit: int = Query(20, ge=1, le=200, description="每页条数"),
) -> LedgerAggregateQueryParams:
    try:
        normalized_payment_status: LedgerPaymentStatus | None = None
        if payment_status is not None:
            allowed_payment_statuses: set[LedgerPaymentStatus] = {
                "unpaid",
                "paid",
                "partial",
                "voided",
            }
            if payment_status not in allowed_payment_statuses:
                raise ValidationError.from_exception_data(
                    "LedgerAggregateQueryParams",
                    [
                        {
                            "type": "literal_error",
                            "loc": ("payment_status",),
                            "input": payment_status,
                            "ctx": {
                                "expected": ", ".join(sorted(allowed_payment_statuses)),
                            },
                        }
                    ],
                )
            normalized_payment_status = cast(LedgerPaymentStatus, payment_status)

        return LedgerAggregateQueryParams(
            ledger_view=ledger_view,
            project_id=project_id,
            asset_id=asset_id,
            party_id=party_id,
            contract_id=contract_id,
            year_month_start=year_month_start,
            year_month_end=year_month_end,
            flow_occurred_on_start=flow_occurred_on_start,
            flow_occurred_on_end=flow_occurred_on_end,
            payment_status=normalized_payment_status,
            include_voided=include_voided,
            offset=offset,
            limit=limit,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


def resolve_ledger_export_query_params(
    export_format: Literal["csv", "excel"] = Query(
        "excel",
        description="导出格式",
    ),
    params: LedgerAggregateQueryParams = Depends(resolve_ledger_query_params),
) -> LedgerExportQueryParams:
    return LedgerExportQueryParams(
        export_format=export_format,
        ledger_view=params.ledger_view,
        project_id=params.project_id,
        asset_id=params.asset_id,
        party_id=params.party_id,
        contract_id=params.contract_id,
        year_month_start=params.year_month_start,
        year_month_end=params.year_month_end,
        flow_occurred_on_start=params.flow_occurred_on_start,
        flow_occurred_on_end=params.flow_occurred_on_end,
        payment_status=params.payment_status,
        include_voided=params.include_voided,
        offset=params.offset,
        limit=params.limit,
    )


async def resolve_service_fee_group_resource_id(request: Request) -> str | None:
    return request.query_params.get("contract_group_id")


@router.get(
    "/ledger/entries",
    response_model=ContractLedgerListResponse,
    summary="跨合同查询台账条目",
)
async def get_ledger_entries(
    params: LedgerAggregateQueryParams = Depends(resolve_ledger_query_params),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="contract",
            )
        ),
    ] = None,
) -> ContractLedgerListResponse:
    _ = _authz
    try:
        result = await ledger_service_v2.query_ledger_entries(
            db,
            ledger_view=params.ledger_view,
            project_id=params.project_id,
            asset_id=params.asset_id,
            party_id=params.party_id,
            contract_id=params.contract_id,
            year_month_start=params.year_month_start,
            year_month_end=params.year_month_end,
            flow_occurred_on_start=params.flow_occurred_on_start,
            flow_occurred_on_end=params.flow_occurred_on_end,
            payment_status=params.payment_status,
            include_voided=params.include_voided,
            offset=params.offset,
            limit=params.limit,
            current_user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return ContractLedgerListResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询台账条目失败", original_error=exc) from exc


@router.get(
    "/ledger/entries/export",
    summary="导出台账条目",
)
async def export_ledger_entries(
    params: LedgerExportQueryParams = Depends(resolve_ledger_export_query_params),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="contract",
            )
        ),
    ] = None,
) -> Response:
    _ = _authz
    try:
        result = await ledger_export_service.export_ledger_entries(
            db,
            params=params,
            current_user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return Response(
            content=result.content,
            media_type=result.media_type,
            headers={"Content-Disposition": f"attachment; filename={result.filename}"},
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("导出台账条目失败", original_error=exc) from exc


@router.post(
    "/ledger/payment-flows",
    response_model=OperationalPaymentFlowResponse,
    summary="创建经营收付流水",
)
async def create_payment_flow(
    payload: OperationalPaymentFlowCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="create",
                resource_type="ledger",
            )
        ),
    ] = None,
) -> OperationalPaymentFlowResponse:
    _ = _authz
    try:
        result = await payment_flow_service.create_flow(
            db,
            data=payload.model_dump(mode="json"),
            registered_by=str(current_user.id),
        )
        return OperationalPaymentFlowResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("创建经营收付流水失败", original_error=exc) from exc


@router.get(
    "/ledger/payment-flows",
    response_model=list[OperationalPaymentFlowDetailResponse],
    summary="按台账目标查询经营收付流水",
)
async def list_payment_flows(
    target_type: Literal["contract_ledger_entry", "service_fee_ledger"] = Query(...),
    target_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(require_authz(action="read", resource_type="ledger")),
    ] = None,
) -> list[OperationalPaymentFlowDetailResponse]:
    _ = _authz
    try:
        result = await payment_flow_service.list_flows_by_target(
            db,
            target_type=target_type,
            target_id=target_id,
            current_user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return [
            OperationalPaymentFlowDetailResponse.model_validate(item)
            for item in result
        ]
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询经营收付流水失败", original_error=exc) from exc


@router.post(
    "/ledger/payment-flows/{flow_id}/vouchers",
    response_model=PaymentVoucherAttachmentResponse,
    summary="上传经营收付流水凭证",
)
async def upload_payment_flow_voucher(
    flow_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(require_authz(action="update", resource_type="ledger")),
    ] = None,
) -> PaymentVoucherAttachmentResponse:
    _ = _authz
    try:
        await validate_upload_file(
            file,
            allowed_types=PAYMENT_VOUCHER_ALLOWED_MIME_TYPES,
            max_size=PAYMENT_VOUCHER_MAX_SIZE,
        )
        content = await file.read(PAYMENT_VOUCHER_MAX_SIZE + 1)
        if len(content) > PAYMENT_VOUCHER_MAX_SIZE:
            raise BusinessValidationError(
                "payment flow voucher exceeds the 20MB size limit"
            )
        result = await payment_voucher_service.upload_voucher(
            db,
            flow_id=flow_id,
            file_name=file.filename or "",
            content_type=file.content_type,
            content=content,
            user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return PaymentVoucherAttachmentResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("上传经营收付流水凭证失败", original_error=exc) from exc


@router.get(
    "/ledger/payment-flows/{flow_id}/vouchers/{attachment_id}/download",
    summary="下载经营收付流水凭证",
)
async def download_payment_flow_voucher(
    flow_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="ledger_voucher",
                resource_id="{flow_id}",
            )
        ),
    ] = None,
) -> FileResponse:
    _ = _authz
    try:
        result = await payment_voucher_service.prepare_download(
            db,
            flow_id=flow_id,
            attachment_id=attachment_id,
            user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        media_types = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
        }
        return FileResponse(
            str(result.path),
            filename=result.attachment.file_name,
            media_type=media_types[result.attachment.file_type],
        )
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("下载经营收付流水凭证失败", original_error=exc) from exc


@router.get(
    "/ledger/payment-flows/{flow_id}/voucher-download-audits",
    response_model=list[PaymentVoucherDownloadAuditResponse],
    summary="查询经营收付流水凭证下载审计",
)
async def list_payment_flow_voucher_download_audits(
    flow_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="ledger",
                resource_id="{flow_id}",
            )
        ),
    ] = None,
) -> list[PaymentVoucherDownloadAuditResponse]:
    _ = _authz
    try:
        result = await payment_voucher_service.list_download_audits(
            db,
            flow_id=flow_id,
            current_user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return [
            PaymentVoucherDownloadAuditResponse.model_validate(item)
            for item in result
        ]
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询经营收付流水凭证审计失败", original_error=exc) from exc


@router.post(
    "/ledger/payment-flows/{flow_id}/allocations",
    response_model=list[PaymentAllocationResponse],
    summary="保存经营收付流水分摊",
)
async def save_payment_flow_allocations(
    flow_id: str,
    payload: PaymentAllocationSaveRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="ledger",
                resource_id="{flow_id}",
            )
        ),
    ] = None,
) -> list[PaymentAllocationResponse]:
    _ = _authz
    try:
        result = await payment_flow_service.save_allocations(
            db,
            flow_id=flow_id,
            allocations=[
                allocation.model_dump(mode="json") for allocation in payload.allocations
            ],
            current_user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return [PaymentAllocationResponse.model_validate(item) for item in result]
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("保存经营收付流水分摊失败", original_error=exc) from exc


@router.post(
    "/ledger/payment-flows/{flow_id}/void",
    response_model=OperationalPaymentFlowResponse,
    summary="作废经营收付流水",
)
async def void_payment_flow(
    flow_id: str,
    payload: PaymentFlowLifecycleActionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="ledger",
                resource_id="{flow_id}",
            )
        ),
    ] = None,
) -> OperationalPaymentFlowResponse:
    _ = _authz
    try:
        user_id = str(current_user.id)
        result = await payment_flow_service.void_flow(
            db,
            flow_id=flow_id,
            reason=payload.reason,
            actor_id=user_id,
            current_user_id=user_id,
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return OperationalPaymentFlowResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("作废经营收付流水失败", original_error=exc) from exc


@router.post(
    "/ledger/payment-flows/{flow_id}/correct",
    response_model=OperationalPaymentFlowResponse,
    summary="更正经营收付流水",
)
async def correct_payment_flow(
    flow_id: str,
    payload: PaymentFlowCorrectionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="ledger",
                resource_id="{flow_id}",
            )
        ),
    ] = None,
) -> OperationalPaymentFlowResponse:
    _ = _authz
    try:
        user_id = str(current_user.id)
        result = await payment_flow_service.correct_flow(
            db,
            flow_id=flow_id,
            reason=payload.reason,
            actor_id=user_id,
            replacement_data=payload.replacement.model_dump(mode="json"),
            allocations=[
                allocation.model_dump(mode="json")
                for allocation in payload.allocations
            ],
            current_user_id=user_id,
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return OperationalPaymentFlowResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("更正经营收付流水失败", original_error=exc) from exc


@router.patch(
    "/ledger/entries/{entry_id}/follow-up",
    response_model=ContractLedgerEntryResponse,
    summary="维护终端收缴台账跟进状态",
)
async def update_ledger_entry_follow_up(
    entry_id: str,
    payload: LedgerFollowUpUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="ledger",
                resource_id="{entry_id}",
            )
        ),
    ] = None,
) -> ContractLedgerEntryResponse:
    _ = _authz
    try:
        result = await ledger_service_v2.update_follow_up(
            db,
            entry_id=entry_id,
            follow_up_status=(
                payload.follow_up_status.value
                if payload.follow_up_status is not None
                else None
            ),
            next_follow_up_date=payload.next_follow_up_date,
            follow_up_note=payload.follow_up_note,
            current_user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return ContractLedgerEntryResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("维护台账跟进状态失败", original_error=exc) from exc


@router.post(
    "/ledger/service-fees/generate",
    response_model=ServiceFeeGenerateResponse,
    summary="生成月度服务费台账",
)
async def generate_service_fees(
    payload: ServiceFeeGenerateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="ledger",
            )
        ),
    ] = None,
) -> ServiceFeeGenerateResponse:
    _ = _authz
    try:
        result = await service_fee_ledger_service.sync_contract_group(
            db,
            group_id=payload.contract_group_id,
            current_user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return ServiceFeeGenerateResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("生成月度服务费台账失败", original_error=exc) from exc


@router.get(
    "/ledger/service-fees",
    response_model=list[ServiceFeeLedgerResponse],
    summary="查询月度服务费台账",
)
async def list_service_fees(
    contract_group_id: str | None = Query(None, min_length=1, description="合同组 ID"),
    project_id: str | None = Query(None, min_length=1, description="项目 ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="contract_group",
                resource_id=resolve_service_fee_group_resource_id,
                deny_as_not_found=True,
            )
        ),
    ] = None,
) -> list[ServiceFeeLedgerResponse]:
    _ = _authz
    try:
        result = await service_fee_ledger_service.list_entries(
            db,
            group_id=contract_group_id,
            project_id=project_id,
            current_user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return [ServiceFeeLedgerResponse.model_validate(item) for item in result]
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("查询月度服务费台账失败", original_error=exc) from exc


@router.post(
    "/ledger/service-fees/{entry_id}/reconcile",
    response_model=ServiceFeeLedgerResponse,
    summary="人工校准服务费台账来源",
)
async def reconcile_service_fee_source(
    entry_id: str,
    payload: ServiceFeeSourceReconcileRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="contract_group")
    ),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="ledger",
            )
        ),
    ] = None,
) -> ServiceFeeLedgerResponse:
    _ = _authz
    try:
        result = await service_fee_ledger_service.reconcile_source(
            db,
            entry_id=entry_id,
            reason=payload.reason,
            current_user_id=str(current_user.id),
            party_filter=build_party_filter_from_scope_context(_scope_ctx),
        )
        return ServiceFeeLedgerResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("校准服务费台账来源失败", original_error=exc) from exc


@router.post(
    "/ledger/compensation/run",
    response_model=LedgerCompensationResponse,
    summary="运行台账补偿任务",
)
async def run_ledger_compensation(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="contract",
            )
        ),
    ] = None,
) -> LedgerCompensationResponse:
    _ = current_user
    _ = _authz
    try:
        result = await ledger_compensation_service.run(db)
        return LedgerCompensationResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("运行台账补偿任务失败", original_error=exc) from exc


@router.post(
    "/contracts/{contract_id}/ledger/recalculate",
    response_model=LedgerRecalculateResponse,
    summary="重算合同台账",
)
async def recalculate_contract_ledger(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="contract",
                resource_id="{contract_id}",
            )
        ),
    ] = None,
) -> LedgerRecalculateResponse:
    _ = current_user
    _ = _authz
    try:
        result = await ledger_service_v2.recalculate_ledger(db, contract_id=contract_id)
        return LedgerRecalculateResponse.model_validate(result)
    except BaseBusinessError:
        raise
    except Exception as exc:
        raise internal_error("重算合同台账失败", original_error=exc) from exc
