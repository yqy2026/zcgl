"""Stable business errors for asset-operations v5."""

from __future__ import annotations

from fastapi import status

from ...core.exception_handler import BaseBusinessError


class ActiveTerminalContractsBlockExitError(BaseBusinessError):
    """An upstream contract cannot exit while terminal contracts remain active."""

    def __init__(self, *, terminal_contract_ids: list[str]) -> None:
        super().__init__(
            message="上游合同仍有关联的有效终端合同，请先处理终端合同",
            code="ACTIVE_TERMINAL_CONTRACTS_BLOCK_EXIT",
            details={"terminal_contract_ids": terminal_contract_ids},
            status_code=status.HTTP_409_CONFLICT,
        )


class AssetUnitAreaMismatchError(BaseBusinessError):
    """A split or merge does not conserve source area totals."""

    def __init__(
        self,
        *,
        source: dict[str, str],
        result: dict[str, str],
    ) -> None:
        super().__init__(
            message="资产单元拆分或合并前后面积不守恒",
            code="ASSET_UNIT_AREA_MISMATCH",
            details={"source": source, "result": result},
            status_code=status.HTTP_409_CONFLICT,
        )


class AssetUnitBoundaryInvalidError(BaseBusinessError):
    """A split or merge does not form the declared effective-date boundary."""

    def __init__(
        self,
        *,
        reason: str,
        unit_ids: list[str],
    ) -> None:
        super().__init__(
            message="资产单元拆分或合并边界无效",
            code="ASSET_UNIT_BOUNDARY_INVALID",
            details={"reason": reason, "unit_ids": unit_ids},
            status_code=status.HTTP_409_CONFLICT,
        )


class AssetUnitUpstreamScopeMismatchError(BaseBusinessError):
    """Merged units do not share one non-empty upstream contract scope."""

    def __init__(
        self,
        *,
        effective_date: str,
        source_scopes: dict[str, list[str]],
    ) -> None:
        super().__init__(
            message="待合并资产单元不属于同一有效上游合同范围",
            code="ASSET_UNIT_UPSTREAM_SCOPE_MISMATCH",
            details={
                "effective_date": effective_date,
                "source_scopes": source_scopes,
            },
            status_code=status.HTTP_409_CONFLICT,
        )


class AssetUnitPeriodOverlapError(BaseBusinessError):
    """A boundary change would cross terminal-contract coverage."""

    def __init__(
        self,
        *,
        asset_unit_ids: list[str],
        terminal_contract_ids: list[str],
    ) -> None:
        super().__init__(
            message="资产单元在调整生效日仍有关联的终端合同",
            code="ASSET_UNIT_PERIOD_OVERLAP",
            details={
                "asset_unit_ids": asset_unit_ids,
                "terminal_contract_ids": terminal_contract_ids,
            },
            status_code=status.HTTP_409_CONFLICT,
        )


class AssetOperationsPreviewStaleError(BaseBusinessError):
    """A boundary preview no longer describes the current facts."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            message="预览已失效，请重新预览",
            code="PREVIEW_STALE",
            details={"reason": reason},
            status_code=status.HTTP_409_CONFLICT,
        )


class AssetOperationsVersionConflictError(BaseBusinessError):
    """An expected source-unit version no longer matches."""

    def __init__(
        self,
        *,
        unit_id: str,
        expected_version: int,
        actual_version: int | None,
    ) -> None:
        super().__init__(
            message="期望版本已变化，请刷新后重试",
            code="VERSION_CONFLICT",
            details={
                "unit_id": unit_id,
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
            status_code=status.HTTP_409_CONFLICT,
        )


class AssetOperationsIdempotencyConflictError(BaseBusinessError):
    """One idempotency key was reused for a different write request."""

    def __init__(self) -> None:
        super().__init__(
            message="请求标识已用于其他操作，请重新发起请求",
            code="IDEMPOTENCY_CONFLICT",
            details={},
            status_code=status.HTTP_409_CONFLICT,
        )


class AssetOperationsPermissionDeniedError(BaseBusinessError):
    """The caller lacks the asset-operations business capability."""

    def __init__(self) -> None:
        super().__init__(
            message="缺少资产运营写入权限",
            code="ASSET_OPS_PERMISSION_DENIED",
            details={"required_permission": "asset_ops:write"},
            status_code=status.HTTP_403_FORBIDDEN,
        )


class AssetContractCoverageInvalidError(BaseBusinessError):
    """A signed contract cannot be attached to the requested unit period."""

    def __init__(self, *, reason: str, asset_unit_ids: list[str]) -> None:
        super().__init__(
            message="合同与资产单元覆盖关系无效",
            code="ASSET_CONTRACT_COVERAGE_INVALID",
            details={"reason": reason, "asset_unit_ids": asset_unit_ids},
            status_code=status.HTTP_409_CONFLICT,
        )


class AssetUnitFieldNotEditableError(BaseBusinessError):
    """Ownership fields cannot be changed on a signed unit."""

    def __init__(self, *, field_names: list[str]) -> None:
        super().__init__(
            message="归属字段不可修改，如需调整请走资产单元拆合",
            code="ASSET_UNIT_FIELD_NOT_EDITABLE",
            details={"field_names": field_names},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


class ContractFieldNotApplicableError(BaseBusinessError):
    """Submitted terms do not apply to this upstream contract type."""

    def __init__(self, *, contract_type: str, field_names: list[str]) -> None:
        super().__init__(
            message="这些字段不适用于当前合同类型，请调整后重试",
            code="CONTRACT_FIELD_NOT_APPLICABLE",
            details={"contract_type": contract_type, "field_names": field_names},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


class RentScheduleInvalidError(BaseBusinessError):
    """A rent stage falls outside the contract term or overlaps another."""

    def __init__(self, *, reason: str) -> None:
        super().__init__(
            message="租金阶段无效：必须位于合同期限内且互不重叠",
            code="RENT_SCHEDULE_INVALID",
            details={"reason": reason},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


class AssetUnitAreaInvalidError(BaseBusinessError):
    """Rentable area cannot exceed the building area."""

    def __init__(self, *, unit_id: str) -> None:
        super().__init__(
            message="可出租面积不得超过建筑面积",
            code="ASSET_UNIT_AREA_INVALID",
            details={"unit_id": unit_id},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


class ScanDocumentRequiredError(BaseBusinessError):
    """Confirmation requires one persisted signed scan document."""

    def __init__(self, *, attachment_id: str | None = None) -> None:
        super().__init__(
            message="确认合同前必须上传已签扫描件",
            code="SCAN_DOCUMENT_REQUIRED",
            details={"attachment_id": attachment_id},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


class ScanDocumentAlreadyBoundError(BaseBusinessError):
    """A signed scan can be consumed by exactly one intake session."""

    def __init__(self, *, attachment_id: str) -> None:
        super().__init__(
            message="已签扫描件已绑定其他合同",
            code="SCAN_DOCUMENT_ALREADY_BOUND",
            details={"attachment_id": attachment_id},
            status_code=status.HTTP_409_CONFLICT,
        )


class TerminalContractAlreadyTerminatedError(BaseBusinessError):
    """A terminal contract allows at most one unreversed termination."""

    def __init__(self, *, event_id: str) -> None:
        super().__init__(
            message="终端合同已存在未撤销的终止事件",
            code="TERMINAL_CONTRACT_ALREADY_TERMINATED",
            details={"event_id": event_id},
            status_code=status.HTTP_409_CONFLICT,
        )


class TerminationReversalTargetInvalidError(BaseBusinessError):
    """A reversal must point at this contract's unreversed termination."""

    def __init__(self, *, reason: str) -> None:
        super().__init__(
            message="撤销目标不是该合同未撤销的终止事件",
            code="TERMINATION_REVERSAL_TARGET_INVALID",
            details={"reason": reason},
            status_code=status.HTTP_409_CONFLICT,
        )


class TerminationReversalBlockedError(BaseBusinessError):
    """Successor facts stop a termination from being reversed."""

    def __init__(
        self,
        *,
        renewed_event_ids: list[str],
        blocking_contract_ids: list[str],
    ) -> None:
        super().__init__(
            message="已存在后继事实，终止事件不可撤销",
            code="TERMINATION_REVERSAL_BLOCKED",
            details={
                "renewed_event_ids": renewed_event_ids,
                "blocking_contract_ids": blocking_contract_ids,
            },
            status_code=status.HTTP_409_CONFLICT,
        )


class ContractAlreadyRenewedError(BaseBusinessError):
    """A contract allows at most one unreversed renewal successor."""

    def __init__(self, *, event_id: str) -> None:
        super().__init__(
            message="合同已存在未撤销的续签后继",
            code="CONTRACT_ALREADY_RENEWED",
            details={"event_id": event_id},
            status_code=status.HTTP_409_CONFLICT,
        )


class UpstreamContractAlreadyExitedError(BaseBusinessError):
    """An upstream contract allows at most one unreversed exit."""

    def __init__(self, *, event_id: str) -> None:
        super().__init__(
            message="上游合同已存在未撤销的退出事件",
            code="UPSTREAM_CONTRACT_ALREADY_EXITED",
            details={"event_id": event_id},
            status_code=status.HTTP_409_CONFLICT,
        )


class UpstreamExitReversalTargetInvalidError(BaseBusinessError):
    """An exit reversal must point at this contract's unreversed exit."""

    def __init__(self, *, reason: str) -> None:
        super().__init__(
            message="撤销目标不是该合同未撤销的退出事件",
            code="EXIT_REVERSAL_TARGET_INVALID",
            details={"reason": reason},
            status_code=status.HTTP_409_CONFLICT,
        )


class UpstreamExitReversalBlockedError(BaseBusinessError):
    """Successor facts stop an upstream exit from being reversed."""

    def __init__(
        self,
        *,
        renewed_event_ids: list[str],
        blocking_contract_ids: list[str],
    ) -> None:
        super().__init__(
            message="已存在后继事实，退出事件不可撤销",
            code="EXIT_REVERSAL_BLOCKED",
            details={
                "renewed_event_ids": renewed_event_ids,
                "blocking_contract_ids": blocking_contract_ids,
            },
            status_code=status.HTTP_409_CONFLICT,
        )


__all__ = [
    "ActiveTerminalContractsBlockExitError",
    "AssetContractCoverageInvalidError",
    "AssetOperationsIdempotencyConflictError",
    "AssetOperationsPermissionDeniedError",
    "AssetOperationsPreviewStaleError",
    "AssetOperationsVersionConflictError",
    "AssetUnitAreaInvalidError",
    "RentScheduleInvalidError",
    "AssetUnitFieldNotEditableError",
    "AssetUnitAreaMismatchError",
    "AssetUnitBoundaryInvalidError",
    "AssetUnitPeriodOverlapError",
    "AssetUnitUpstreamScopeMismatchError",
    "ContractAlreadyRenewedError",
    "ContractFieldNotApplicableError",
    "ScanDocumentAlreadyBoundError",
    "ScanDocumentRequiredError",
    "TerminalContractAlreadyTerminatedError",
    "TerminationReversalBlockedError",
    "TerminationReversalTargetInvalidError",
    "UpstreamContractAlreadyExitedError",
    "UpstreamExitReversalBlockedError",
    "UpstreamExitReversalTargetInvalidError",
    "AssessmentScopeOperatorForbiddenError",
    "AssessmentScopeDraftExistsError",
    "AssessmentScopeDraftStateError",
    "AssessmentScopePeriodInvalidError",
    "OccupancyReportAlreadySubmittedError",
    "OccupancyReportPeriodInvalidError",
    "OccupancyReportScopeMissingError",
    "OccupancyReportNotSubmittedError",
    "OccupancyReportAlreadyWithdrawnError",
]


class AssessmentScopeOperatorForbiddenError(BaseBusinessError):
    """The caller may not act on this operator party's reporting scope."""

    def __init__(self, *, operator_party_id: str) -> None:
        super().__init__(
            message="无权管理该运营主体的考核范围",
            code="ASSESSMENT_SCOPE_OPERATOR_FORBIDDEN",
            details={"operator_party_id": operator_party_id},
            status_code=status.HTTP_403_FORBIDDEN,
        )


class AssessmentScopeDraftExistsError(BaseBusinessError):
    """One draft per operator and year already exists; continue editing it."""

    def __init__(self, *, draft_id: str) -> None:
        super().__init__(
            message="该年度已存在未保存的考核范围草稿",
            code="ASSESSMENT_SCOPE_DRAFT_EXISTS",
            details={"draft_id": draft_id},
            status_code=status.HTTP_409_CONFLICT,
        )


class AssessmentScopeDraftStateError(BaseBusinessError):
    """The draft is no longer editable, for example after being committed."""

    def __init__(self, *, draft_status: str) -> None:
        super().__init__(
            message="考核范围草稿当前状态不允许该操作",
            code="ASSESSMENT_SCOPE_DRAFT_STATE_INVALID",
            details={"status": draft_status},
            status_code=status.HTTP_409_CONFLICT,
        )


class AssessmentScopePeriodInvalidError(BaseBusinessError):
    """The commit effective period does not belong to the draft's year."""

    def __init__(self, *, effective_from_period: str, year: int) -> None:
        super().__init__(
            message="生效统计月必须属于考核年度",
            code="ASSESSMENT_SCOPE_PERIOD_INVALID",
            details={
                "effective_from_period": effective_from_period,
                "year": year,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class OccupancyReportScopeMissingError(BaseBusinessError):
    """The period's year has no active assessment scope; reporting is closed."""

    def __init__(self, *, operator_party_id: str, year: int) -> None:
        super().__init__(
            message="该年度尚无生效的考核范围，无法生成报送草稿",
            code="OCCUPANCY_REPORT_SCOPE_MISSING",
            details={"operator_party_id": operator_party_id, "year": year},
            status_code=status.HTTP_409_CONFLICT,
        )


class OccupancyReportAlreadySubmittedError(BaseBusinessError):
    """The month already has a submitted snapshot until it is withdrawn."""

    def __init__(self, *, report_id: str, period: str) -> None:
        super().__init__(
            message="该统计月已提交快照，撤回后方可重新编辑",
            code="OCCUPANCY_REPORT_ALREADY_SUBMITTED",
            details={"report_id": report_id, "period": period},
            status_code=status.HTTP_409_CONFLICT,
        )


class OccupancyReportPeriodInvalidError(BaseBusinessError):
    """The requested reporting period is not a closed business month."""

    def __init__(self, *, period: str, reason: str) -> None:
        super().__init__(
            message="报送统计月无效",
            code="OCCUPANCY_REPORT_PERIOD_INVALID",
            details={"period": period, "reason": reason},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class OccupancyReportNotSubmittedError(BaseBusinessError):
    """The report chain row has not been submitted, so no snapshot exists."""

    def __init__(self, *, report_id: str) -> None:
        super().__init__(
            message="该报送尚未提交，无可读取快照",
            code="OCCUPANCY_REPORT_NOT_SUBMITTED",
            details={"report_id": report_id},
            status_code=status.HTTP_409_CONFLICT,
        )


class OccupancyReportAlreadyWithdrawnError(BaseBusinessError):
    """The report was already withdrawn; the original snapshot stays intact."""

    def __init__(self, *, report_id: str) -> None:
        super().__init__(
            message="该报送已撤回，不能重复撤回",
            code="OCCUPANCY_REPORT_ALREADY_WITHDRAWN",
            details={"report_id": report_id},
            status_code=status.HTTP_409_CONFLICT,
        )
