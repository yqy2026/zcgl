import React, { useState, useEffect, useCallback } from 'react';
import { Card, Form, Space, Row, Tag } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useQueries } from '@tanstack/react-query';
import type { Dayjs } from 'dayjs';

import type { AssetSearchParams } from '@/types/asset';
import { assetService } from '@/services/assetService';
import { useSearchHistory } from '@/hooks/useSearchHistory';
import { createLogger } from '@/utils/logger';
import { MessageManager } from '@/utils/messageManager';
import { AdvancedSearchFields } from '@/components/Asset/AssetSearch/AdvancedSearchFields';
import { BasicSearchFields } from '@/components/Asset/AssetSearch/BasicSearchFields';
import { SaveSearchModal } from '@/components/Asset/AssetSearch/SaveSearchModal';
import { SearchActionButtons } from '@/components/Asset/AssetSearch/SearchActionButtons';
import { SearchHistoryModal } from '@/components/Asset/AssetSearch/SearchHistoryModal';

const componentLogger = createLogger('AssetSearch');

interface AssetSearchFormValues {
  search?: string;
  ownership_status?: string;
  property_nature?: string;
  usage_status?: string;
  ownership_entity?: string;
  business_category?: string;
  areaRange?: [number, number];
  dateRange?: [Dayjs, Dayjs];
  area_min?: number;
  area_max?: number;
  created_start?: string;
  created_end?: string;
  [key: string]: unknown;
}

interface AssetSearchProps {
  onSearch: (params: AssetSearchParams) => void;
  onReset: () => void;
  initialValues?: Partial<AssetSearchParams>;
  loading?: boolean;
  showSaveButton?: boolean;
  showHistoryButton?: boolean;
}

const AssetSearch: React.FC<AssetSearchProps> = ({
  onSearch,
  onReset,
  initialValues = {},
  loading = false,
  showSaveButton = true,
  showHistoryButton = true,
}) => {
  const [form] = Form.useForm();
  const [expanded, setExpanded] = useState(false);
  const [areaRange, setAreaRange] = useState<[number, number]>([0, 100000]);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [historyModalVisible, setHistoryModalVisible] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [editingHistoryId, setEditingHistoryId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  // 搜索历史Hook
  const {
    searchHistory,
    addSearchHistory,
    removeSearchHistory,
    clearSearchHistory,
    updateSearchHistoryName,
  } = useSearchHistory();

  // 使用并行查询获取所有下拉框数据，简化逻辑避免错误
  const searchQueries = useQueries({
    queries: [
      {
        queryKey: ['ownership-entities'],
        queryFn: async () => {
          try {
            // 直接从专门的API获取
            return await assetService.getOwnershipEntities();
          } catch (error) {
            componentLogger.warn(`获取权属方失败，使用默认选项: ${String(error)}`);
            return ['政府', '企业', '事业单位', '社会团体', '其他'];
          }
        },
        staleTime: 30 * 60 * 1000,
        retry: 0, // 不重试，立即使用默认值
      },
      {
        queryKey: ['business-categories'],
        queryFn: async () => {
          try {
            // 直接从专门的API获取
            return await assetService.getBusinessCategories();
          } catch (error) {
            componentLogger.warn(`获取业态类别失败，使用默认选项: ${String(error)}`);
            return ['办公', '商业', '工业', '仓储', '住宅', '酒店', '餐饮', '其他'];
          }
        },
        staleTime: 30 * 60 * 1000,
        retry: 0,
      },
    ],
  });

  // 提取查询结果
  const ownershipEntities = searchQueries[0].data ?? [];
  const businessCategories = searchQueries[1].data ?? [];

  const ownershipLoading = searchQueries[0].isLoading;
  const businessLoading = searchQueries[1].isLoading;

  // 检查是否所有查询都已加载完成
  const isLoadingQueries = searchQueries.some(query => query.isLoading);

  // 合并外部loading和内部查询loading
  const isComponentLoading = loading || isLoadingQueries;

  // 设置初始值
  useEffect(() => {
    if (Object.keys(initialValues).length > 0) {
      form.setFieldsValue(initialValues);
    }
  }, [initialValues, form]);

  const handleToggleExpanded = useCallback(() => {
    setExpanded(prev => !prev);
  }, []);

  const handleAreaMinChange = useCallback((value: number | null) => {
    setAreaRange(prev => [value ?? 0, prev[1]]);
  }, []);

  const handleAreaMaxChange = useCallback((value: number | null) => {
    setAreaRange(prev => [prev[0], value ?? 100000]);
  }, []);

  // 处理搜索
  const handleSearch = useCallback(() => {
    const values = form.getFieldsValue() as AssetSearchFormValues;

    // 处理日期范围
    if (values.dateRange != null) {
      values.created_start = values.dateRange[0]?.format('YYYY-MM-DD');
      values.created_end = values.dateRange[1]?.format('YYYY-MM-DD');
      delete values.dateRange;
    }

    // 处理面积范围
    if (values.areaRange != null) {
      values.area_min = values.areaRange[0];
      values.area_max = values.areaRange[1];
      delete values.areaRange;
    }

    // 过滤空值
    const searchParams = Object.entries(values).reduce<AssetSearchParams>((acc, [key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        acc[key as keyof AssetSearchParams] = value as never;
      }
      return acc;
    }, {} as AssetSearchParams);

    onSearch(searchParams);
  }, [form, onSearch]);

  // 处理重置
  const handleReset = useCallback(() => {
    form.resetFields();
    setAreaRange([0, 100000]);
    onReset();
  }, [form, onReset]);

  const handleOpenSaveModal = useCallback(() => {
    setSaveModalVisible(true);
  }, []);

  const handleCloseSaveModal = useCallback(() => {
    setSaveModalVisible(false);
  }, []);

  const handleOpenHistoryModal = useCallback(() => {
    setHistoryModalVisible(true);
  }, []);

  const handleCloseHistoryModal = useCallback(() => {
    setHistoryModalVisible(false);
    setEditingHistoryId(null);
    setEditingName('');
  }, []);

  const handleSaveNameChange = useCallback((value: string) => {
    setSaveName(value);
  }, []);

  // 处理保存搜索条件
  const handleSaveSearch = useCallback(() => {
    const values = form.getFieldsValue() as AssetSearchFormValues;

    // 检查是否有搜索条件
    const hasConditions = Object.values(values).some(
      value => value !== undefined && value !== null && value !== ''
    );

    if (!hasConditions) {
      MessageManager.warning('请先设置搜索条件');
      return;
    }

    if (!saveName.trim()) {
      MessageManager.warning('请输入保存名称');
      return;
    }

    addSearchHistory({
      id: Date.now().toString(),
      name: saveName,
      conditions: values as Record<string, unknown>,
      createdAt: new Date().toISOString(),
    });

    setSaveName('');
    setSaveModalVisible(false);
    MessageManager.success('搜索条件已保存');
  }, [addSearchHistory, form, saveName]);

  // 处理应用历史搜索条件
  const handleApplyHistory = useCallback(
    (historyId: string) => {
      const history = searchHistory.find(h => h.id === historyId);
      if (history !== undefined && history !== null) {
        form.setFieldsValue(history.conditions);
        handleSearch();
        setHistoryModalVisible(false);
      }
    },
    [form, handleSearch, searchHistory]
  );

  // 处理删除历史记录
  const handleDeleteHistory = useCallback(
    (historyId: string) => {
      removeSearchHistory(historyId);
      MessageManager.success('历史记录已删除');
    },
    [removeSearchHistory]
  );

  // 处理编辑历史记录名称
  const handleEditHistory = useCallback((historyId: string, currentName: string) => {
    setEditingHistoryId(historyId);
    setEditingName(currentName);
  }, []);

  const handleEditNameChange = useCallback((value: string) => {
    setEditingName(value);
  }, []);

  // 保存编辑的名称
  const handleSaveEdit = useCallback(() => {
    if (editingHistoryId !== null && editingName.trim() !== '') {
      updateSearchHistoryName(editingHistoryId, editingName.trim());
      setEditingHistoryId(null);
      setEditingName('');
      MessageManager.success('名称已更新');
    }
  }, [editingHistoryId, editingName, updateSearchHistoryName]);

  return (
    <Card
      title={
        <Space>
          <SearchOutlined />
          <span>资产搜索</span>
          {isComponentLoading && <Tag color="processing">加载中…</Tag>}
        </Space>
      }
      extra={
        <SearchActionButtons
          expanded={expanded}
          loading={isComponentLoading}
          showSaveButton={showSaveButton}
          showHistoryButton={showHistoryButton}
          onSearch={handleSearch}
          onReset={handleReset}
          onToggleExpanded={handleToggleExpanded}
          onSave={handleOpenSaveModal}
          onShowHistory={handleOpenHistoryModal}
        />
      }
    >
      <Form form={form} layout="vertical" disabled={isComponentLoading}>
        <Row gutter={16}>
          <BasicSearchFields />
        </Row>

        {expanded && (
          <AdvancedSearchFields
            ownershipEntities={ownershipEntities}
            businessCategories={businessCategories}
            ownershipEntityLoading={ownershipLoading}
            businessCategoryLoading={businessLoading}
            areaRange={areaRange}
            onAreaMinChange={handleAreaMinChange}
            onAreaMaxChange={handleAreaMaxChange}
          />
        )}
      </Form>

      <SaveSearchModal
        open={saveModalVisible}
        value={saveName}
        onChange={handleSaveNameChange}
        onSave={handleSaveSearch}
        onCancel={handleCloseSaveModal}
      />

      <SearchHistoryModal
        open={historyModalVisible}
        historyItems={searchHistory}
        editingHistoryId={editingHistoryId}
        editingName={editingName}
        onApply={handleApplyHistory}
        onEdit={handleEditHistory}
        onDelete={handleDeleteHistory}
        onSaveEdit={handleSaveEdit}
        onEditNameChange={handleEditNameChange}
        onClear={clearSearchHistory}
        onCancel={handleCloseHistoryModal}
      />
    </Card>
  );
};

export default React.memo(AssetSearch);
