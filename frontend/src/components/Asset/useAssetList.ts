/**
 * useAssetList.ts
 *
 * Shared utilities, constants, and types for the AssetList component family.
 * Extracted from AssetList.tsx as part of a structural refactor.
 */

import type { Asset, AssetListResponse } from '@/types/asset';
import { DataStatus } from '@/types/asset';
import type {
  TablePaginationConfig,
  SorterResult,
  TableCurrentDataSource,
  FilterValue,
} from 'antd/es/table/interface';

// ─── Constants ───────────────────────────────────────────────────────────────

export const UUID_LENGTH = 36;

// ─── Utility Functions ───────────────────────────────────────────────────────

/**
 * 格式化权属类别显示文本
 * 从系统字典选项中查找对应的标签,如果找不到则返回原始值或默认值
 */
export function formatOwnershipCategory(
  text: string | undefined,
  options: Array<{ label: string; value: string }>
): string {
  if (!text || options.length === 0) {
    return text ?? '其他';
  }

  const matchedOption = options.find(opt => opt.value === String(text));
  return matchedOption?.label ?? text;
}

export function getDataStatusColor(status?: string): string {
  switch (status) {
    case DataStatus.NORMAL:
      return 'green';
    case DataStatus.DELETED:
      return 'red';
    case DataStatus.ARCHIVED:
      return 'orange';
    case DataStatus.ABNORMAL:
      return 'volcano';
    default:
      return 'default';
  }
}

export function getOccupancyRateClassName(
  rate: number,
  styles: Record<string, string>
): string {
  if (rate >= 80) {
    return styles.occupancyRateSuccess;
  }
  if (rate >= 60) {
    return styles.occupancyRateWarning;
  }
  return styles.occupancyRateError;
}

const normalizeOwnerName = (value: string | undefined): string | undefined => {
  if (value == null) {
    return undefined;
  }
  const normalized = value.trim();
  return normalized === '' ? undefined : normalized;
};

export function resolveOwnerPartyName(
  record: Pick<Asset, 'owner_party_name' | 'ownership_entity'>
): string | undefined {
  const ownerPartyName = normalizeOwnerName(record.owner_party_name);
  if (ownerPartyName != null) {
    return ownerPartyName;
  }
  return normalizeOwnerName(record.ownership_entity);
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface AssetListProps {
  data?: AssetListResponse;
  loading?: boolean;
  onEdit: (asset: Asset) => void;
  onDelete: (id: string) => void;
  onRestore: (id: string) => void;
  onHardDelete: (id: string) => void;
  onView: (asset: Asset) => void;
  onViewHistory: (asset: Asset) => void;
  onTableChange: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Asset> | SorterResult<Asset>[],
    extra: TableCurrentDataSource<Asset>
  ) => void;
  selectedRowKeys?: React.Key[];
  onSelectChange?: (selectedRowKeys: React.Key[]) => void;
}
