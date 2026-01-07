import React from 'react';
import type { Asset, AssetListResponse } from '@/types/asset';
import type {
  TablePaginationConfig,
  SorterResult,
  TableCurrentDataSource,
} from 'antd/es/table/interface';
import type { FilterValue } from 'antd/es/table/interface';
import AssetTable from './AssetTable';
import AssetSummary from './AssetSummary';

/**
 * AssetList组件属性接口
 */
interface AssetListProps {
  /** 资产列表数据 */
  data?: AssetListResponse;
  /** 加载状态 */
  loading?: boolean;
  /** 编辑资产回调函数 */
  onEdit: (asset: Asset) => void;
  /** 删除资产回调函数 */
  onDelete: (id: string) => void;
  /** 查看资产详情回调函数 */
  onView: (asset: Asset) => void;
  /** 查看资产历史回调函数 */
  onViewHistory: (asset: Asset) => void;
  /** 表格变化回调函数 */
  onTableChange: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Asset> | SorterResult<Asset>[],
    extra: TableCurrentDataSource<Asset>
  ) => void;
  /** 选中的行键值 */
  selectedRowKeys?: React.Key[];
  /** 行选择变化回调函数 */
  onSelectChange?: (
    selectedRowKeys: React.Key[],
    selectedRows: Asset[],
    info: { type: 'all' | 'none' | 'invert' | 'single' | 'multiple' }
  ) => void;
}

/**
 * 资产列表组件
 * 主要用于展示资产列表数据，包含表格和汇总信息
 */
const AssetList: React.FC<AssetListProps> = props => {
  // 汇总行渲染函数
  const renderSummary = () => {
    return <AssetSummary data={props.data} />;
  };

  return <AssetTable {...props} summary={renderSummary} />;
};

export default React.memo(AssetList);
