import React, { useEffect } from 'react';
import { Card, Space, Tag, Button, Tooltip } from 'antd';
import {
  FilterOutlined,
  ClearOutlined,
  SaveOutlined,
  HistoryOutlined,
  ReloadOutlined,
  DownOutlined,
  UpOutlined,
} from '@ant-design/icons';
import type { AssetSearchParams } from '@/types/asset';

// Import section components
import {
  AnalyticsFiltersProvider,
  useAnalyticsFiltersContext,
  BasicFiltersSection,
  FiltersSection,
  SearchPresetsSection,
  FilterHistorySection,
  FilterActionsSection,
  FILTER_PRESETS,
} from './Filters';

interface AnalyticsFiltersProps {
  filters: AssetSearchParams;
  onFiltersChange: (filters: AssetSearchParams) => void;
  onApplyFilters?: () => void;
  onResetFilters?: () => void;
  onPresetSelect?: (presetKey: string) => void;
  loading?: boolean;
  showAdvanced?: boolean;
  onToggleAdvanced?: () => void;
  realTimeUpdate?: boolean;
}

/**
 * Card header with action buttons
 */
const FiltersCardHeader: React.FC = () => {
  const {
    activeFiltersCount,
    setSaveName,
    showHistory,
    setShowHistory,
    handleReset,
    handleApply,
    loading,
    showAdvanced,
    onToggleAdvanced,
  } = useAnalyticsFiltersContext();

  return (
    <Card
      size="small"
      title={
        <Space>
          <FilterOutlined />
          <span>数据筛选</span>
          {activeFiltersCount > 0 && <Tag color="blue">{activeFiltersCount} 个筛选条件</Tag>}
        </Space>
      }
      extra={
        <Space>
          <Tooltip title="保存筛选条件">
            <Button
              type="text"
              icon={<SaveOutlined />}
              onClick={() => setSaveName('')}
              disabled={activeFiltersCount === 0}
              size="small"
            />
          </Tooltip>

          <Tooltip title="筛选历史">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => setShowHistory(!showHistory)}
              size="small"
            />
          </Tooltip>

          <Tooltip title="重置筛选">
            <Button
              type="text"
              icon={<ClearOutlined />}
              onClick={handleReset}
              disabled={activeFiltersCount === 0}
              size="small"
            />
          </Tooltip>

          <Tooltip title="刷新数据">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={handleApply}
              loading={loading}
              size="small"
            />
          </Tooltip>

          {onToggleAdvanced !== undefined && (
            <Button
              type="text"
              icon={showAdvanced ? <UpOutlined /> : <DownOutlined />}
              onClick={onToggleAdvanced}
              size="small"
            >
              {showAdvanced ? '收起' : '高级'}
            </Button>
          )}
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <FilterHistorySection />
      <SearchPresetsSection />
      <BasicFiltersSection />
      <FiltersSection />
      <FilterActionsSection />
    </Card>
  );
};

/**
 * Inner component that uses context
 */
const AnalyticsFiltersInner: React.FC = () => {
  const { filters } = useAnalyticsFiltersContext();

  // Initialize with default preset
  useEffect(() => {
    if (Object.keys(filters).length === 0) {
      const defaultPreset = FILTER_PRESETS.find(preset => preset.key === 'all');
      if (defaultPreset !== undefined) {
        // Default filters are handled by parent
      }
    }
  }, [filters]);

  return <FiltersCardHeader />;
};

/**
 * AnalyticsFilters - Filter panel for analytics data
 * Refactored to use section components for better maintainability
 */
export const AnalyticsFilters: React.FC<AnalyticsFiltersProps> = ({
  filters,
  onFiltersChange,
  onApplyFilters,
  onResetFilters,
  onPresetSelect,
  loading = false,
  showAdvanced = false,
  onToggleAdvanced,
  realTimeUpdate = true,
}) => {
  return (
    <AnalyticsFiltersProvider
      filters={filters}
      onFiltersChange={onFiltersChange}
      onApplyFilters={onApplyFilters}
      onResetFilters={onResetFilters}
      onPresetSelect={onPresetSelect}
      loading={loading}
      showAdvanced={showAdvanced}
      onToggleAdvanced={onToggleAdvanced}
      realTimeUpdate={realTimeUpdate}
    >
      <AnalyticsFiltersInner />
    </AnalyticsFiltersProvider>
  );
};

export default AnalyticsFilters;
