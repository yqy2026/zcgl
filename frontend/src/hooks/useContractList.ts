import React, { useState, useEffect, useCallback } from 'react';
import { Modal } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import { rentContractService } from '@/services/rentContractService';
import { assetService } from '@/services/assetService';
import { ownershipService } from '@/services/ownershipService';
import type { TableProps } from 'antd';
import type {
  RentContract,
  RentContractQueryParams,
  RentContractPageState,
  RentStatisticsOverview,
} from '@/types/rentContract';
import type { Asset } from '@/types/asset';
import type { Ownership } from '@/types/ownership';

const logger = createLogger('useContractList');

export const useContractList = () => {
  const [state, setState] = useState<RentContractPageState>({
    loading: false,
    contracts: [],
    pagination: {
      current: 1,
      pageSize: 10,
      total: 0,
    },
    filters: {},
    showModal: false,
    modalMode: 'create',
  });

  const [assets, setAssets] = useState<Asset[]>([]);
  const [ownerships, setOwnerships] = useState<Ownership[]>([]);
  const [statistics, setStatistics] = useState<RentStatisticsOverview | null>(null);

  // 加载合同列表
  const loadContracts = useCallback(
    async (params?: RentContractQueryParams) => {
      setState(prev => ({ ...prev, loading: true }));
      try {
        const response = await rentContractService.getContracts({
          page: state.pagination.current,
          pageSize: state.pagination.pageSize,
          ...state.filters,
          ...params,
        });

        // 确保items是一个数组
        const contracts = Array.isArray(response.items) ? response.items : [];

        setState(prev => ({
          ...prev,
          loading: false,
          contracts: contracts,
          pagination: {
            ...prev.pagination,
            total: response.total ?? 0,
            pages: response.pages ?? 0,
          },
        }));
      } catch (error) {
        logger.error('加载合同列表失败:', error as Error);
        MessageManager.error(
          `加载合同列表失败: ${error instanceof Error ? error.message : '未知错误'}`
        );
        setState(prev => ({ ...prev, loading: false, contracts: [] }));
      }
    },
    [state.pagination.current, state.pagination.pageSize, state.filters]
  );

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
    loadContracts();
    loadStatistics();
    loadReferenceData();
  }, [loadContracts, loadStatistics, loadReferenceData]);

  // 处理分页变化
  const handleTableChange: TableProps<RentContract>['onChange'] = pagination => {
    setState(prev => ({
      ...prev,
      pagination: {
        ...prev.pagination,
        current: pagination.current ?? 1,
        pageSize: pagination.pageSize ?? 10,
      },
    }));
    loadContracts({
      page: pagination.current ?? 1,
      pageSize: pagination.pageSize ?? 10,
    });
  };

  // 处理搜索
  const handleSearch = (values: Record<string, unknown>) => {
    setState(prev => ({
      ...prev,
      filters: values,
      pagination: { ...prev.pagination, current: 1 },
    }));
    loadContracts({ ...values, page: 1 });
  };

  // 重置搜索
  const handleReset = () => {
    setState(prev => ({
      ...prev,
      filters: {},
      pagination: { ...prev.pagination, current: 1 },
    }));
    loadContracts({ page: 1 });
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
          loadContracts(); // Reload list
          loadStatistics(); // Reload stats
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
          loadContracts();
          loadStatistics();
        } catch {
          MessageManager.error('终止合同失败');
        }
      },
    });
  };

  // 导入成功的回调
  const handleImportSuccess = () => {
    loadContracts();
    loadStatistics();
  };

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
