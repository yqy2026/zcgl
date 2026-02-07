import type { RentContractSearchFilters } from '@/types/rentContract';

interface RentStatisticsQueryParams {
  start: string;
  end: string;
  year: number;
}

export const RENTAL_QUERY_KEYS = {
  contractRoot: ['rent-contract'] as const,
  contract: (id: string | undefined) => ['rent-contract', id] as const,

  contractListRoot: ['rent-contract-list'] as const,
  contractList: (currentPage: number, pageSize: number, filters: RentContractSearchFilters) =>
    ['rent-contract-list', currentPage, pageSize, filters] as const,

  contractStatistics: ['rent-contract-statistics'] as const,
  referenceAssets: ['rent-contract-reference-assets'] as const,
  referenceOwnerships: ['rent-contract-reference-ownerships'] as const,

  contractDepositLedger: (id: string | undefined) => ['contract-deposit-ledger', id] as const,
  contractServiceFeeLedger: (id: string | undefined) =>
    ['contract-service-fee-ledger', id] as const,

  ledgerListRoot: ['rent-ledger-list'] as const,
  ledgerList: (currentPage: number, pageSize: number, filters: Record<string, unknown>) =>
    ['rent-ledger-list', currentPage, pageSize, filters] as const,
  ledgerStatistics: ['rent-ledger-statistics'] as const,
  ledgerReferenceAssets: ['rent-ledger-reference-assets'] as const,
  ledgerReferenceOwnerships: ['rent-ledger-reference-ownerships'] as const,

  rentStatisticsRoot: ['rent-statistics'] as const,
  rentStatistics: (params: RentStatisticsQueryParams) => ['rent-statistics', params] as const,
} as const;
