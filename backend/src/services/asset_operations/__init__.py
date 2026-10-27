"""Business services for the asset-operations v5 vertical slice."""

from .asset_unit_command_service import (
    AssetUnitCommandService,
    asset_unit_command_service,
)
from .boundary_command_service import (
    AssetUnitBoundaryCommandService,
    AssetUnitBoundaryPreviewStore,
    asset_unit_boundary_command_service,
)
from .boundary_rules import AreaCheck, AreaTotals, validate_merge, validate_split
from .contract_command_service import (
    AssetContractCommandService,
    asset_contract_command_service,
)
from .contract_lifecycle_command_service import (
    ContractLifecycleCommandService,
    ContractLifecyclePreviewStore,
    contract_lifecycle_command_service,
)
from .contract_projections import (
    derive_terminal_contract_status,
    derive_terminal_contract_warnings,
    derive_upstream_contract_status,
    rented_asset_unit_ids,
)
from .errors import (
    ActiveTerminalContractsBlockExitError,
    AssetContractCoverageInvalidError,
    AssetOperationsIdempotencyConflictError,
    AssetOperationsPermissionDeniedError,
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
    AssetUnitAreaMismatchError,
    AssetUnitBoundaryInvalidError,
    AssetUnitPeriodOverlapError,
    AssetUnitUpstreamScopeMismatchError,
    ScanDocumentAlreadyBoundError,
    ScanDocumentRequiredError,
    TerminalContractAlreadyTerminatedError,
)
from .lifecycle_rules import validate_upstream_exit
from .query_service import (
    AssetOperationsQueryService,
    asset_operations_query_service,
)

__all__ = [
    "derive_upstream_contract_status",
    "derive_terminal_contract_status",
    "derive_terminal_contract_warnings",
    "rented_asset_unit_ids",
    "AssetUnitCommandService",
    "asset_unit_command_service",
    "AssetUnitBoundaryCommandService",
    "AssetUnitBoundaryPreviewStore",
    "asset_unit_boundary_command_service",
    "AssetContractCommandService",
    "asset_contract_command_service",
    "ContractLifecycleCommandService",
    "ContractLifecyclePreviewStore",
    "contract_lifecycle_command_service",
    "AssetOperationsQueryService",
    "asset_operations_query_service",
    "ActiveTerminalContractsBlockExitError",
    "AssetContractCoverageInvalidError",
    "AssetOperationsIdempotencyConflictError",
    "AssetOperationsPermissionDeniedError",
    "AssetOperationsPreviewStaleError",
    "AssetOperationsVersionConflictError",
    "AreaCheck",
    "AreaTotals",
    "AssetUnitAreaMismatchError",
    "AssetUnitBoundaryInvalidError",
    "AssetUnitPeriodOverlapError",
    "AssetUnitUpstreamScopeMismatchError",
    "ScanDocumentAlreadyBoundError",
    "ScanDocumentRequiredError",
    "TerminalContractAlreadyTerminatedError",
    "validate_merge",
    "validate_split",
    "validate_upstream_exit",
]
