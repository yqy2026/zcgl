from .ledger_service import RentContractLedgerService
from .lifecycle_service import RentContractLifecycleService
from .statistics_service import RentContractStatisticsService


class RentContractService(
    RentContractLifecycleService,
    RentContractLedgerService,
    RentContractStatisticsService,
):
    """租金合同业务服务"""


rent_contract_service = RentContractService()

__all__ = ["RentContractService", "rent_contract_service"]
