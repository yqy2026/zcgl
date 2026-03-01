/**
 * Asset Mock 工厂函数
 * 用于生成类型安全的测试数据
 */

import type { Asset } from '@/types/asset';
import { OwnershipStatus, PropertyNature, UsageStatus } from '@/types/asset';

/**
 * 默认 Asset 对象，包含所有必填字段
 */
const defaultAsset: Asset = {
  id: 'test-asset-1',
  property_name: '测试物业',
  owner_party_name: '测试权属方',
  address: '测试地址',
  ownership_status: OwnershipStatus.CONFIRMED,
  property_nature: PropertyNature.COMMERCIAL,
  usage_status: UsageStatus.VACANT,
  include_in_occupancy_rate: true,
  is_sublease: false,
  is_litigated: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

/**
 * 创建 Mock Asset 对象
 * @param overrides - 覆盖默认值的字段
 * @returns 完整的 Asset 对象
 */
export function createMockAsset(overrides?: Partial<Asset>): Asset {
  return { ...defaultAsset, ...overrides };
}

/**
 * 创建多个 Mock Asset 对象
 * @param count - 数量
 * @param overrides - 每个对象的覆盖值，可以是固定值或生成函数
 * @returns Asset 数组
 */
export function createMockAssets(
  count: number,
  overrides?: Partial<Asset> | ((index: number) => Partial<Asset>)
): Asset[] {
  return Array.from({ length: count }, (_, index) => {
    const override = typeof overrides === 'function' ? overrides(index) : overrides;
    return createMockAsset({
      id: `test-asset-${index + 1}`,
      property_name: `测试物业 ${index + 1}`,
      ...override,
    });
  });
}

/**
 * 创建已出租的 Asset
 */
export function createRentedAsset(overrides?: Partial<Asset>): Asset {
  return createMockAsset({
    usage_status: UsageStatus.RENTED,
    tenant_name: '测试租户',
    rented_area: 500,
    rentable_area: 500,
    monthly_rent: 10000,
    ...overrides,
  });
}

/**
 * 创建空置的 Asset
 */
export function createVacantAsset(overrides?: Partial<Asset>): Asset {
  return createMockAsset({
    usage_status: UsageStatus.VACANT,
    rented_area: 0,
    rentable_area: 1000,
    ...overrides,
  });
}
