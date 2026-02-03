import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Typography, Button, Space, Alert } from 'antd';
import { PlusOutlined, ExportOutlined, ImportOutlined } from '@ant-design/icons';
import { MessageManager } from '@/utils/messageManager';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type {
  FilterValue,
  SorterResult,
  TableCurrentDataSource,
  TablePaginationConfig,
} from 'antd/es/table/interface';
import { assetService } from '@/services/assetService';
import { analyticsService } from '@/services/analyticsService';
import { useListData } from '@/hooks/useListData';
import AssetList from '@/components/Asset/AssetList';
import AssetSearch from '@/components/Asset/AssetSearch';
import AssetAreaSummary from '@/components/Asset/AssetAreaSummary';
import type { Asset, AssetSearchParams } from '@/types/asset';
import { createLogger } from '@/utils/logger';
import { PageContainer, ContentSection, LoadingContainer } from '@/components/Common/StateContainer';

const pageLogger = createLogger('AssetList');

const { Title } = Typography;

type AssetListFilters = Omit<AssetSearchParams, 'page' | 'page_size'>;

const AssetListPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const fetchAssets = useCallback(
    async ({ page, pageSize, ...filters }: { page: number; pageSize: number } & AssetListFilters) => {
      const response = await assetService.getAssets({
        ...filters,
        page,
        page_size: pageSize,
      });
      return {
        items: response.items,
        total: response.total,
        pages: response.pages,
      };
    },
    []
  );

  const {
    data: assetRows,
    loading: isLoading,
    error,
    pagination,
    filters,
    loadList,
    applyFilters,
    resetFilters: resetListFilters,
  } = useListData<Asset, AssetListFilters>({
    fetcher: fetchAssets,
    initialFilters: {},
    initialPageSize: 20,
    onError: error => {
      const message = error instanceof Error ? error.message : '加载资产数据失败';
      pageLogger.error('资产列表加载失败:', error as Error);
      MessageManager.error(message);
    },
  });

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const analyticsFilters = useMemo(() => {
    const { sort_by: _sort_by, sort_order: _sort_order, ...rest } = filters;
    return rest;
  }, [filters]);

  // 获取统计分析数据
  const { data: analyticsData, isLoading: analyticsLoading } = useQuery({
    queryKey: ['analytics', analyticsFilters],
    queryFn: () => analyticsService.getComprehensiveAnalytics(analyticsFilters),
  });

  const listData = useMemo(
    () => ({
      items: assetRows,
      total: pagination.total,
      page: pagination.current,
      page_size: pagination.pageSize,
      pages:
        pagination.pageSize > 0 ? Math.ceil(pagination.total / pagination.pageSize) : 0,
    }),
    [assetRows, pagination.current, pagination.pageSize, pagination.total]
  );
  const showInitialLoading = isLoading && assetRows.length === 0;

  // 处理搜索
  const handleSearch = useCallback(
    (params: AssetSearchParams) => {
      const { page: _page, page_size: _pageSize, ...nextFilters } = params;
      applyFilters(nextFilters);
    },
    [applyFilters]
  );

  // 重置搜索
  const handleReset = useCallback(() => {
    resetListFilters();
  }, [resetListFilters]);

  // 处理表格变化
  const handleTableChange = useCallback(
    (
      paginationConfig: TablePaginationConfig,
      _filters: Record<string, FilterValue | null>,
      sorter: SorterResult<Asset> | SorterResult<Asset>[],
      _extra: TableCurrentDataSource<Asset>
    ) => {
      const normalizedSorter = Array.isArray(sorter) ? sorter[0] : sorter;
      const sortField =
        typeof normalizedSorter?.field === 'string' ? normalizedSorter.field : undefined;
      const sortOrder =
        normalizedSorter?.order === 'ascend'
          ? 'asc'
          : normalizedSorter?.order === 'descend'
            ? 'desc'
            : undefined;

      const nextFilters: AssetListFilters = { ...filters };

      if (sortField != null) {
        nextFilters.sort_by = sortField;
      } else {
        delete nextFilters.sort_by;
      }

      if (sortOrder != null) {
        nextFilters.sort_order = sortOrder;
      } else {
        delete nextFilters.sort_order;
      }

      void loadList({
        page: paginationConfig.current ?? pagination.current,
        pageSize: paginationConfig.pageSize ?? pagination.pageSize,
        filters: nextFilters,
        replaceFilters: true,
      });
    },
    [filters, loadList, pagination.current, pagination.pageSize]
  );

  // 处理编辑
  const handleEdit = useCallback((asset: { id: string }) => {
    navigate(`/assets/${asset.id}/edit`);
  }, [navigate]);

  // 处理删除
  const handleDelete = useCallback(async (id: string) => {
    try {
      await assetService.deleteAsset(id);
      MessageManager.success('删除成功');
      // 重新加载数据
      void loadList();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '删除失败';
      MessageManager.error(errorMessage);
    }
  }, [loadList]);

  // 处理查看
  const handleView = useCallback((asset: { id: string }) => {
    navigate(`/assets/${asset.id}`);
  }, [navigate]);

  // 处理查看历史
  const handleViewHistory = useCallback((asset: { id: string }) => {
    navigate(`/assets/${asset.id}/history`);
  }, [navigate]);

  // 处理选择变化
  const handleSelectChange = useCallback((selectedRowKeys: React.Key[]) => {
    setSelectedRowKeys(selectedRowKeys);
  }, []);

  // 处理导出所有资产
  const handleExportAll = async () => {
    try {
      MessageManager.success('正在导出资产数据，请稍候...');
      const blob = await assetService.exportAssets(filters, { format: 'xlsx' });

      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `资产数据导出_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      MessageManager.success('资产数据导出成功');
    } catch (error) {
      pageLogger.error('导出失败:', error as Error);
      const errorMessage = error instanceof Error ? error.message : '导出失败，请稍后重试';
      MessageManager.error(errorMessage);
    }
  };

  // 处理导出选中资产
  const handleExportSelected = async () => {
    if (selectedRowKeys.length === 0) {
      MessageManager.warning('请先选择要导出的资产');
      return;
    }

    try {
      MessageManager.success('正在导出选中的资产数据，请稍候...');
      const blob = await assetService.exportSelectedAssets(
        selectedRowKeys.map(key => String(key)),
        {
          format: 'xlsx',
        }
      );

      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `选中资产数据导出_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      MessageManager.success('选中资产数据导出成功');
    } catch (error) {
      pageLogger.error('导出失败:', error as Error);
      const errorMessage = error instanceof Error ? error.message : '导出失败，请稍后重试';
      MessageManager.error(errorMessage);
    }
  };

  if (showInitialLoading) {
    return <LoadingContainer text="加载资产数据中..." />;
  }

  if (error) {
    return (
      <PageContainer>
        <Alert
          title="数据加载失败"
          description={
            error instanceof Error && error.message.includes('Network Error')
              ? '无法连接到服务器，请检查后端服务是否正常运行'
              : `错误详情: ${error instanceof Error ? error.message : '未知错误'}`
          }
          type="error"
          showIcon
          action={
            <Button size="small" onClick={() => void loadList()}>
              重新加载
            </Button>
          }
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <ContentSection spacing="lg">
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            flexWrap: 'wrap',
          }}
        >
          <Title level={2} style={{ margin: 0 }}>
            资产列表
          </Title>
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/assets/new')}>
              新增资产
            </Button>
            <Button icon={<ImportOutlined />} onClick={() => navigate('/assets/import')}>
              导入资产
            </Button>
            <Button icon={<ExportOutlined />} onClick={handleExportAll}>
              导出全部
            </Button>
            {selectedRowKeys.length > 0 && (
              <Button type="dashed" icon={<ExportOutlined />} onClick={handleExportSelected}>
                导出选中 ({selectedRowKeys.length})
              </Button>
            )}
          </Space>
        </div>
      </ContentSection>

      {/* 搜索组件 */}
      <AssetSearch
        onSearch={handleSearch}
        onReset={handleReset}
        initialValues={filters}
        loading={isLoading}
      />

      {/* 面积汇总组件 */}
      <AssetAreaSummary analyticsData={analyticsData?.data} loading={analyticsLoading} />

      {/* 资产列表组件 */}
      <AssetList
        data={listData}
        loading={isLoading}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onView={handleView}
        onViewHistory={handleViewHistory}
        onTableChange={handleTableChange}
        selectedRowKeys={selectedRowKeys}
        onSelectChange={handleSelectChange}
      />
    </PageContainer>
  );
};

export default AssetListPage;
