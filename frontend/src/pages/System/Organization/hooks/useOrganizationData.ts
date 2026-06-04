import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { PaginationState } from '@/components/Common/TableWithPagination';
import { organizationService } from '@/services/organizationService';
import type {
  OrganizationHistory,
  OrganizationStatistics,
  OrganizationTree,
} from '@/types/organization';
import type {
  OrganizationFilters,
  OrganizationListQueryResult,
  OrganizationPaginationState,
} from '../types';

interface UseOrganizationDataParams {
  filters: OrganizationFilters;
  pagination: OrganizationPaginationState;
  historyOrganizationId?: string;
  historyEnabled?: boolean;
}

export const useOrganizationData = ({
  filters,
  pagination,
  historyOrganizationId,
  historyEnabled = false,
}: UseOrganizationDataParams) => {
  const currentPage = pagination.current;
  const pageSize = pagination.pageSize;
  const keyword = filters.keyword;

  const fetchOrganizationList = useCallback(async (): Promise<OrganizationListQueryResult> => {
    const trimmedKeyword = keyword.trim();
    const data =
      trimmedKeyword !== ''
        ? await organizationService.searchOrganizations(trimmedKeyword, {
            page: currentPage,
            page_size: pageSize,
          })
        : await organizationService.getOrganizations({
            page: currentPage,
            page_size: pageSize,
          });
    return { items: data, total: data.length };
  }, [currentPage, keyword, pageSize]);

  const organizationsQuery = useQuery<OrganizationListQueryResult>({
    queryKey: ['organization-list', currentPage, pageSize, keyword],
    queryFn: fetchOrganizationList,
    retry: 1,
  });

  const organizationTreeQuery = useQuery<OrganizationTree[]>({
    queryKey: ['organization-tree'],
    queryFn: async () => {
      return await organizationService.getOrganizationTree();
    },
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const statisticsQuery = useQuery<OrganizationStatistics>({
    queryKey: ['organization-statistics'],
    queryFn: async () => {
      return await organizationService.getStatistics();
    },
    staleTime: 60 * 1000,
    retry: 1,
  });

  const organizationHistoryQuery = useQuery<OrganizationHistory[]>({
    queryKey: ['organization-history', historyOrganizationId],
    queryFn: async () => {
      if (historyOrganizationId == null) {
        return [];
      }
      return await organizationService.getOrganizationHistory(historyOrganizationId);
    },
    enabled: historyEnabled && historyOrganizationId != null,
    retry: 1,
  });

  const tablePagination = useMemo<PaginationState>(
    () => ({
      current: currentPage,
      pageSize,
      total: organizationsQuery.data?.total ?? 0,
    }),
    [currentPage, organizationsQuery.data?.total, pageSize]
  );

  return {
    organizations: organizationsQuery.data?.items ?? [],
    organizationTree: organizationTreeQuery.data ?? [],
    statistics: statisticsQuery.data ?? null,
    loading: organizationsQuery.isLoading || organizationsQuery.isFetching,
    isOrganizationTreeFetching: organizationTreeQuery.isFetching,
    organizationsError: organizationsQuery.error,
    organizationTreeError: organizationTreeQuery.error,
    statisticsError: statisticsQuery.error,
    organizationHistory: organizationHistoryQuery.data ?? [],
    organizationHistoryError: organizationHistoryQuery.error,
    isOrganizationHistoryFetching: organizationHistoryQuery.isFetching,
    tablePagination,
    refetchOrganizations: organizationsQuery.refetch,
    refetchOrganizationTree: organizationTreeQuery.refetch,
    refetchStatistics: statisticsQuery.refetch,
  };
};
