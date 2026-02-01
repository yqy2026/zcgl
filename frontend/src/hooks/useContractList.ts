import { useState, useEffect, useCallback, useMemo } from 'react';
import { Modal } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import { rentContractService } from '@/services/rentContractService';
import { assetService } from '@/services/assetService';
import { ownershipService } from '@/services/ownershipService';
import type {
  RentContract,
  RentContractPageState,
  RentContractSearchFilters,
  RentStatisticsOverview,
} from '@/types/rentContract';
import type { Asset } from '@/types/asset';
import type { Ownership } from '@/types/ownership';
import { useListData } from '@/hooks/useListData';

const logger = createLogger('useContractList');

export const useContractList = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [ownerships, setOwnerships] = useState<Ownership[]>([]);
  const [statistics, setStatistics] = useState<RentStatisticsOverview | null>(null);

  // 加载合同列表
  const fetchContracts = useCallback(
    async ({
      page,
      pageSize,
      ...filters
    }: { page: number; pageSize: number } & RentContractSearchFilters) => {
      const response = await rentContractService.getContracts({
        page,
        pageSize,
        ...filters,
      });
      const contracts = Array.isArray(response.items) ? response.items : [];
      return {
        items: contracts,
        total: response.total ?? 0,
        pages: response.pages ?? 0,
      };
    },
    []
  );

  const handleListError = useCallback((error: unknown) => {
    logger.error('加载合同列表失败:', error as Error);
    MessageManager.error(
      `加载合同列表失败: ${error instanceof Error ? error.message : '未知错误'}`
    );
  }, []);

  const {
    data: contracts,
    loading,
    pagination,
    filters,
    loadList,
    applyFilters,
    resetFilters,
    updatePagination,
  } = useListData<RentContract, RentContractSearchFilters>({
    fetcher: fetchContracts,
    initialFilters: {},
    initialPageSize: 10,
    onError: handleListError,
  });

  // 加载统计数据
  const loadStatistics = useCallback(async () => {
    try {
      const stats = await rentContractService.getRentStatistics();
      setStatistics(stats);
    } catch (error) {
      logger.error('加载统计数据失败:', error as Error);
    }
  }, []);

  // 加载资产和权属方数据
  const loadReferenceData = useCallback(async () => {
    try {
      const [assetsResponse, ownershipsData] = await Promise.all([
        assetService.getAssets({ pageSize: 100 }),
        ownershipService.getOwnershipOptions(true),
      ]);
      setAssets(assetsResponse.items);
      setOwnerships(ownershipsData);
    } catch {
      MessageManager.error('加载参考数据失败');
    }
  }, []);

  useEffect(() => {
    void loadList();
    void loadStatistics();
    void loadReferenceData();
  }, [loadList, loadStatistics, loadReferenceData]);

  // 处理分页变化
  const handleTableChange = (next: { current?: number; pageSize?: number }) => {
    updatePagination(next);
  };

  // 处理搜索
  const handleSearch = (values: Record<string, unknown>) => {
    applyFilters(values as RentContractSearchFilters);
  };

  // 重置搜索
  const handleReset = () => {
    resetFilters();
  };

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
          void loadList(); // Reload list
          void loadStatistics(); // Reload stats
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
          void loadList();
          void loadStatistics();
        } catch {
          MessageManager.error('终止合同失败');
        }
      },
    });
  };

  // 导入成功的回调
  const handleImportSuccess = () => {
    void loadList();
    void loadStatistics();
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
    statistics,
    handleTableChange,
    handleSearch,
    handleReset,
    handleDelete,
    handleGenerateLedger,
    handleTerminate,
    handleImportSuccess,
  };
};
