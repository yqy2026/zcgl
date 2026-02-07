import { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Modal } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import { rentContractService } from '@/services/rentContractService';
import { assetService } from '@/services/assetService';
import { ownershipService } from '@/services/ownershipService';
import { RENTAL_QUERY_KEYS } from '@/constants/queryKeys';
import type {
  RentContract,
  RentContractListResponse,
  RentContractPageState,
  RentContractSearchFilters,
  RentStatisticsOverview,
} from '@/types/rentContract';
import type { Asset, AssetListResponse } from '@/types/asset';
import type { Ownership } from '@/types/ownership';

const logger = createLogger('useContractList');

export const useContractList = () => {
  const [filters, setFilters] = useState<RentContractSearchFilters>({});
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 10,
  });

  const {
    data: contractsResponse,
    error: contractsError,
    isLoading: isContractsLoading,
    isFetching: isContractsFetching,
    refetch: refetchContracts,
  } = useQuery<RentContractListResponse>({
    queryKey: RENTAL_QUERY_KEYS.contractList(
      paginationState.current,
      paginationState.pageSize,
      filters
    ),
    queryFn: () =>
      rentContractService.getContracts({
        page: paginationState.current,
        pageSize: paginationState.pageSize,
        ...filters,
      }),
    retry: 1,
  });

  const {
    data: statistics,
    error: statisticsError,
    refetch: refetchStatistics,
  } = useQuery<RentStatisticsOverview>({
    queryKey: RENTAL_QUERY_KEYS.contractStatistics,
    queryFn: () => rentContractService.getRentStatistics(),
    staleTime: 60 * 1000,
    retry: 1,
  });

  const { data: assetsResponse, error: assetsError } = useQuery<AssetListResponse>({
    queryKey: RENTAL_QUERY_KEYS.referenceAssets,
    queryFn: () => assetService.getAssets({ page_size: 100 }),
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const { data: ownershipsData, error: ownershipsError } = useQuery<Ownership[]>({
    queryKey: RENTAL_QUERY_KEYS.referenceOwnerships,
    queryFn: () => ownershipService.getOwnershipOptions(true),
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  useEffect(() => {
    if (contractsError != null) {
      logger.error('加载合同列表失败:', contractsError);
      MessageManager.error(
        `加载合同列表失败: ${contractsError instanceof Error ? contractsError.message : '未知错误'}`
      );
    }
  }, [contractsError]);

  useEffect(() => {
    if (statisticsError != null) {
      logger.error('加载统计数据失败:', statisticsError);
    }
  }, [statisticsError]);

  useEffect(() => {
    if (assetsError != null || ownershipsError != null) {
      MessageManager.error('加载参考数据失败');
    }
  }, [assetsError, ownershipsError]);

  const contracts = Array.isArray(contractsResponse?.items) ? contractsResponse.items : [];
  const assets: Asset[] = assetsResponse?.items ?? [];
  const ownerships = ownershipsData ?? [];
  const statisticsData = statistics ?? null;
  const loading = isContractsLoading || isContractsFetching;
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: contractsResponse?.total ?? 0,
      pages: contractsResponse?.pages ?? 0,
    }),
    [
      contractsResponse?.pages,
      contractsResponse?.total,
      paginationState.current,
      paginationState.pageSize,
    ]
  );

  // 处理分页变化
  const handleTableChange = (next: { current?: number; pageSize?: number }) => {
    setPaginationState(prev => ({
      current: next.current ?? prev.current,
      pageSize: next.pageSize ?? prev.pageSize,
    }));
  };

  // 处理搜索
  const handleSearch = (values: Record<string, unknown>) => {
    setFilters(values as RentContractSearchFilters);
    setPaginationState(prev => ({
      ...prev,
      current: 1,
    }));
  };

  // 重置搜索
  const handleReset = () => {
    setFilters({});
    setPaginationState(prev => ({
      ...prev,
      current: 1,
    }));
  };

  const refreshListAndStatistics = useCallback(() => {
    void refetchContracts();
    void refetchStatistics();
  }, [refetchContracts, refetchStatistics]);

  // 删除合同
  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个合同吗？删除后将无法恢复。',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await rentContractService.deleteContract(id);
          MessageManager.success('删除成功');
          refreshListAndStatistics();
        } catch {
          MessageManager.error('删除失败');
        }
      },
    });
  };

  // 生成台账
  const handleGenerateLedger = async (contractId: string) => {
    try {
      await rentContractService.generateMonthlyLedger({ contract_id: contractId });
      MessageManager.success('生成台账成功');
    } catch {
      MessageManager.error('生成台账失败');
    }
  };

  // 终止合同
  const handleTerminate = async (contract: RentContract) => {
    Modal.confirm({
      title: '确认终止合同',
      content: `确定要终止合同「${contract.contract_number ?? ''}」吗？`,
      okText: '确认终止',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await rentContractService.terminateContract(
            contract.id,
            new Date().toISOString().split('T')[0]
          );
          MessageManager.success('合同已终止');
          refreshListAndStatistics();
        } catch {
          MessageManager.error('终止合同失败');
        }
      },
    });
  };

  // 导入成功的回调
  const handleImportSuccess = () => {
    refreshListAndStatistics();
  };

  const state = useMemo<RentContractPageState>(
    () => ({
      loading,
      contracts,
      pagination,
      filters,
      showModal: false,
      modalMode: 'create',
    }),
    [loading, contracts, pagination, filters]
  );

  return {
    state,
    assets,
    ownerships,
    statistics: statisticsData,
    handleTableChange,
    handleSearch,
    handleReset,
    handleDelete,
    handleGenerateLedger,
    handleTerminate,
    handleImportSuccess,
  };
};
