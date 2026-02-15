import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { PaginationState } from '@/components/Common/TableWithPagination';
import { logService } from '@/services/systemService';
import type { LogFilters, LogListQueryResult, OperationLogPaginationState } from '../types';
import {
  buildOperationLogRequestParams,
  deriveOperationLogStatistics,
  normalizeOperationLogs,
} from '../utils';

interface UseOperationLogDataParams {
  filters: LogFilters;
  pagination: OperationLogPaginationState;
}

export const useOperationLogData = ({ filters, pagination }: UseOperationLogDataParams) => {
  const currentPage = pagination.current;
  const pageSize = pagination.pageSize;
  const startDateTimestamp = filters.dateRange != null ? filters.dateRange[0].valueOf() : null;
  const endDateTimestamp = filters.dateRange != null ? filters.dateRange[1].valueOf() : null;

  const fetchLogs = useCallback(async (): Promise<LogListQueryResult> => {
    const result = await logService.getLogs(buildOperationLogRequestParams(filters, pagination));
    const items = Array.isArray(result?.items) ? result.items : [];
    const normalizedItems = normalizeOperationLogs(items);

    return {
      items: normalizedItems,
      total: result?.total ?? normalizedItems.length,
      pages: result?.pages,
    };
  }, [filters, pagination]);

  const logsQuery = useQuery<LogListQueryResult>({
    queryKey: [
      'operation-log-list',
      pagination.current,
      pagination.pageSize,
      filters.searchText,
      filters.module,
      filters.action,
      filters.status,
      startDateTimestamp,
      endDateTimestamp,
    ],
    queryFn: fetchLogs,
    retry: 1,
  });

  const logs = useMemo(() => logsQuery.data?.items ?? [], [logsQuery.data?.items]);

  const tablePagination = useMemo<PaginationState>(
    () => ({
      current: currentPage,
      pageSize,
      total: logsQuery.data?.total ?? 0,
    }),
    [currentPage, logsQuery.data?.total, pageSize]
  );

  const statistics = useMemo(() => {
    return deriveOperationLogStatistics(logs, tablePagination.total);
  }, [logs, tablePagination.total]);

  return {
    logs,
    tablePagination,
    statistics,
    loading: logsQuery.isLoading || logsQuery.isFetching,
    logsError: logsQuery.error,
    refetchLogs: logsQuery.refetch,
  };
};
