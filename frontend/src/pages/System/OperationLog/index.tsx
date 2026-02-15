import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Card } from 'antd';
import PageContainer from '@/components/Common/PageContainer';
import { MessageManager } from '@/utils/messageManager';
import { countActiveLogFilters } from './utils';
import { useOperationLogData } from './hooks/useOperationLogData';
import type { LogFilters, OperationLogPaginationState, Tone } from './types';
import type { OperationLog } from '@/services/systemService';
import OperationLogStatisticsCards from './components/OperationLogStatisticsCards';
import OperationLogFiltersToolbar from './components/OperationLogFiltersToolbar';
import OperationLogTable from './components/OperationLogTable';
import OperationLogDetailDrawer from './components/OperationLogDetailDrawer';
import styles from '../OperationLogPage.module.css';

const toneClassMap: Record<Tone, string> = {
  primary: styles.tonePrimary,
  success: styles.toneSuccess,
  warning: styles.toneWarning,
  error: styles.toneError,
  neutral: styles.toneNeutral,
};

const OperationLogPage: React.FC = () => {
  const [filters, setFilters] = useState<LogFilters>({
    searchText: '',
    module: '',
    action: '',
    status: '',
    dateRange: null,
  });
  const [paginationState, setPaginationState] = useState<OperationLogPaginationState>({
    current: 1,
    pageSize: 20,
  });
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<OperationLog | null>(null);

  const getToneClassName = useCallback((tone: Tone): string => {
    return toneClassMap[tone];
  }, []);

  const { logs, tablePagination, statistics, loading, logsError, refetchLogs } =
    useOperationLogData({
      filters,
      pagination: paginationState,
    });

  useEffect(() => {
    if (logsError != null) {
      MessageManager.error('加载操作日志失败');
    }
  }, [logsError]);

  const activeFilterCount = useMemo(() => countActiveLogFilters(filters), [filters]);

  const refreshLogs = useCallback(() => {
    void refetchLogs();
  }, [refetchLogs]);

  const updateFilters = useCallback((nextFilters: Partial<LogFilters>) => {
    setFilters(prev => ({ ...prev, ...nextFilters }));
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handleSearch = useCallback(
    (value: string) => {
      updateFilters({ searchText: value });
    },
    [updateFilters]
  );

  const handleModuleChange = useCallback(
    (value?: string) => {
      updateFilters({ module: value ?? '' });
    },
    [updateFilters]
  );

  const handleActionChange = useCallback(
    (value?: string) => {
      updateFilters({ action: value ?? '' });
    },
    [updateFilters]
  );

  const handleStatusChange = useCallback(
    (value?: string) => {
      updateFilters({ status: value ?? '' });
    },
    [updateFilters]
  );

  const handleDateRangeChange = useCallback(
    (dates: LogFilters['dateRange']) => {
      updateFilters({ dateRange: dates });
    },
    [updateFilters]
  );

  const handlePageChange = useCallback((next: { current?: number; pageSize?: number }) => {
    setPaginationState(prev => ({
      current: next.current ?? prev.current,
      pageSize: next.pageSize ?? prev.pageSize,
    }));
  }, []);

  const handleViewDetail = useCallback((log: OperationLog) => {
    setSelectedLog(log);
    setDetailDrawerVisible(true);
  }, []);

  return (
    <PageContainer
      className={styles.pageShell}
      title="操作日志"
      subTitle="查看系统操作轨迹与安全审计记录"
    >
      <OperationLogStatisticsCards
        statistics={statistics}
        resolveToneClassName={getToneClassName}
      />

      <Card className={styles.auditCard}>
        <OperationLogFiltersToolbar
          filters={filters}
          total={tablePagination.total}
          activeFilterCount={activeFilterCount}
          loading={loading}
          onSearch={handleSearch}
          onModuleChange={handleModuleChange}
          onActionChange={handleActionChange}
          onStatusChange={handleStatusChange}
          onDateRangeChange={handleDateRangeChange}
          onRefresh={refreshLogs}
        />

        <OperationLogTable
          logs={logs}
          loading={loading}
          paginationState={tablePagination}
          resolveToneClassName={getToneClassName}
          onPageChange={handlePageChange}
          onViewDetail={handleViewDetail}
        />
      </Card>

      <OperationLogDetailDrawer
        open={detailDrawerVisible}
        selectedLog={selectedLog}
        onClose={() => setDetailDrawerVisible(false)}
        resolveToneClassName={getToneClassName}
      />
    </PageContainer>
  );
};

export default OperationLogPage;
