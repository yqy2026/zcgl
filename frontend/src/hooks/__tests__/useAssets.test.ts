/**
 * useAssets Hook 测试
 * 测试资产管理相关的自定义Hooks（简化版本）
 */

import { describe, it, expect, vi } from 'vitest';
import * as useAssetsHooks from '../useAssets';

// =============================================================================
// 类型定义
// =============================================================================

interface _Asset {
  id: string;
  ownershipEntity: string;
  propertyName: string;
  address: string;
  ownershipStatus: string;
  propertyNature: string;
  usageStatus: string;
  landArea?: number;
  actualPropertyArea?: number;
  rentableArea?: number;
  rentedArea?: number;
  unrentedArea?: number;
  occupancyRate?: number;
  createdAt: string;
  updatedAt: string;
}

// =============================================================================
// Mock Hooks
// =============================================================================

vi.mock('@/services/assetService', () => ({
  assetService: {
    getAssets: vi.fn(() => Promise.resolve({ items: [], total: 0, page: 1, limit: 20 })),
    getAsset: vi.fn(() => Promise.resolve({ id: '1', propertyName: 'Test' })),
    createAsset: vi.fn(() => Promise.resolve({ id: 'new-1', propertyName: 'New' })),
    updateAsset: vi.fn(() => Promise.resolve({ id: '1', propertyName: 'Updated' })),
    deleteAsset: vi.fn(() => Promise.resolve({ success: true })),
    deleteAssets: vi.fn(() => Promise.resolve({ success: true, deleted: 2 })),
    getAssetHistory: vi.fn(() => Promise.resolve([])),
    getAssetStats: vi.fn(() => Promise.resolve({})),
    getOwnershipEntities: vi.fn(() => Promise.resolve([])),
    getManagementEntities: vi.fn(() => Promise.resolve([])),
    getBusinessCategories: vi.fn(() => Promise.resolve([])),
    searchAssets: vi.fn(() => Promise.resolve({ items: [], total: 0 })),
    validateAsset: vi.fn(() => Promise.resolve({ valid: true })),
  },
}));

// =============================================================================
// useAssets Hook 测试
// =============================================================================

describe('useAssets - Hook验证', () => {
  it('应该导出useAssets hook', () => {
    expect(typeof useAssetsHooks.useAssets).toBe('function');
  });

  it('应该导出useAsset hook', () => {
    expect(typeof useAssetsHooks.useAsset).toBe('function');
  });

  it('应该导出useCreateAsset hook', () => {
    expect(typeof useAssetsHooks.useCreateAsset).toBe('function');
  });

  it('应该导出useUpdateAsset hook', () => {
    expect(typeof useAssetsHooks.useUpdateAsset).toBe('function');
  });

  it('应该导出useDeleteAsset hook', () => {
    expect(typeof useAssetsHooks.useDeleteAsset).toBe('function');
  });

  it('应该导出useBatchDeleteAssets hook', () => {
    expect(typeof useAssetsHooks.useBatchDeleteAssets).toBe('function');
  });

  it('应该导出useAssetHistory hook', () => {
    expect(typeof useAssetsHooks.useAssetHistory).toBe('function');
  });

  it('应该导出useAssetStats hook', () => {
    expect(typeof useAssetsHooks.useAssetStats).toBe('function');
  });

  it('应该导出useOwnershipEntities hook', () => {
    expect(typeof useAssetsHooks.useOwnershipEntities).toBe('function');
  });

  it('应该导出useManagementEntities hook', () => {
    expect(typeof useAssetsHooks.useManagementEntities).toBe('function');
  });

  it('应该导出useBusinessCategories hook', () => {
    expect(typeof useAssetsHooks.useBusinessCategories).toBe('function');
  });

  it('应该导出useAssetSearch hook', () => {
    expect(typeof useAssetsHooks.useAssetSearch).toBe('function');
  });

  it('应该导出useValidateAsset hook', () => {
    expect(typeof useAssetsHooks.useValidateAsset).toBe('function');
  });
});
