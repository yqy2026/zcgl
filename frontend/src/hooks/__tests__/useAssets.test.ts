/**
 * useAssets Hook 测试
 * 测试资产管理相关的自定义Hooks（简化版本）
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, createTestQueryClient, renderHookWithProviders, waitFor } from '@/test/test-utils';
import * as useAssetsHooks from '../useAssets';

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|perspective:owner',
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnershipSelectOptions: vi.fn(() => Promise.resolve([])),
  },
}));

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
    getAssets: vi.fn(() => Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 })),
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

import { assetService } from '@/services/assetService';

// =============================================================================
// useAssets Hook 测试
// =============================================================================

describe('useAssets - Hook验证', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

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

  it('useAsset 应把当前视角纳入详情 queryKey', async () => {
    const queryClient = createTestQueryClient();

    renderHookWithProviders(() => useAssetsHooks.useAsset('asset-1'), { queryClient });

    await waitFor(() => {
      expect(assetService.getAsset).toHaveBeenCalledWith('asset-1');
    });

    const queryKeys = queryClient
      .getQueryCache()
      .getAll()
      .map(query => query.queryKey);

    expect(
      queryKeys.some(
        queryKey =>
          Array.isArray(queryKey) &&
          queryKey[0] === 'asset' &&
          queryKey[1] === 'user:user-1|perspective:owner' &&
          queryKey[2] === 'asset-1'
      )
    ).toBe(true);
  });

  it('useAssets 应把当前视角纳入列表 queryKey 并使用 assets-list 前缀', async () => {
    const queryClient = createTestQueryClient();

    renderHookWithProviders(() => useAssetsHooks.useAssets({ keyword: '园区' } as never), {
      queryClient,
    });

    await waitFor(() => {
      expect(assetService.getAssets).toHaveBeenCalledWith({ keyword: '园区' });
    });

    const queryKeys = queryClient
      .getQueryCache()
      .getAll()
      .map(query => query.queryKey);

    expect(
      queryKeys.some(
        queryKey =>
          Array.isArray(queryKey) &&
          queryKey[0] === 'assets-list' &&
          queryKey[1] === 'user:user-1|perspective:owner' &&
          typeof queryKey[2] === 'object' &&
          queryKey[2] !== null &&
          'keyword' in queryKey[2] &&
          queryKey[2].keyword === '园区'
      )
    ).toBe(true);
  });

  it('useCreateAsset 成功后应失效资产列表与分析查询前缀', async () => {
    const queryClient = createTestQueryClient();
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHookWithProviders(() => useAssetsHooks.useCreateAsset(), {
      queryClient,
    });

    await act(async () => {
      await result.current.mutateAsync({ asset_name: '新增资产' } as never);
    });

    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['assets-list'] });
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['analytics'] });
  });

  it('useUpdateAsset 成功后应失效资产列表与详情的 scoped 查询前缀', async () => {
    const queryClient = createTestQueryClient();
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHookWithProviders(() => useAssetsHooks.useUpdateAsset(), {
      queryClient,
    });

    await act(async () => {
      await result.current.mutateAsync({
        id: 'asset-1',
        data: { asset_name: '更新后的资产' } as never,
      });
    });

    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['assets-list'] });
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['asset'] });
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['analytics'] });
  });

  it('useDeleteAsset 成功后应失效资产列表与分析查询前缀', async () => {
    const queryClient = createTestQueryClient();
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHookWithProviders(() => useAssetsHooks.useDeleteAsset(), {
      queryClient,
    });

    await act(async () => {
      await result.current.mutateAsync('asset-1');
    });

    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['assets-list'] });
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['analytics'] });
  });

  it('useBatchDeleteAssets 成功后应失效资产列表与分析查询前缀', async () => {
    const queryClient = createTestQueryClient();
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHookWithProviders(() => useAssetsHooks.useBatchDeleteAssets(), {
      queryClient,
    });

    await act(async () => {
      await result.current.mutateAsync(['asset-1', 'asset-2']);
    });

    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['assets-list'] });
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['analytics'] });
  });
});
