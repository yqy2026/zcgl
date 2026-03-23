/**
 * useAssetStore 测试
 * 测试资产 UI 状态管理
 *
 * 注意: 服务器数据（资产列表、分页）由 React Query 管理。
 * 此 store 仅管理 UI 状态。
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@/test/utils/test-helpers';
import { useAssetStore } from '../useAssetStore';
import type { Asset } from '../../types/asset';

// =============================================================================
// Mock数据
// =============================================================================

const mockAsset = {
  id: 'asset-001',
  ownership_entity: '权属方A',
  asset_name: '物业A',
  address: '地址A',
  ownership_status: '自有',
  property_nature: '商业',
  usage_status: '使用中',
  land_area: 1000,
  actual_property_area: 900,
  rentable_area: 800,
  rented_area: 600,
  unrented_area: 200,
  occupancy_rate: 75,
  include_in_occupancy_rate: true,
  is_sublease: false,
  is_litigated: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
} as unknown as Asset;

// =============================================================================
// 基础功能测试
// =============================================================================

describe('useAssetStore - 初始化状态', () => {
  beforeEach(() => {
    useAssetStore.getState().reset();
  });

  it('应该有正确的初始状态', () => {
    const { result } = renderHook(() => useAssetStore());

    expect(result.current.selectedAsset).toBeNull();
    expect(Array.from(result.current.selectedIds)).toEqual([]);
    expect(result.current.viewMode).toBe('table');
  });

  it('searchParams应该有正确的初始值', () => {
    const { result } = renderHook(() => useAssetStore());

    expect(result.current.searchParams).toEqual({
      page: 1,
      page_size: 20,
      sort_field: 'created_at',
      sort_order: 'desc',
    });
  });
});

// =============================================================================
// 选择功能测试
// =============================================================================

describe('useAssetStore - 选择功能', () => {
  beforeEach(() => {
    useAssetStore.getState().reset();
  });

  describe('setSelectedAsset', () => {
    it('应该设置选中的资产', () => {
      const { result } = renderHook(() => useAssetStore());

      act(() => {
        result.current.setSelectedAsset(mockAsset);
      });

      expect(result.current.selectedAsset).toEqual(mockAsset);
      expect(result.current.selectedAsset?.id).toBe('asset-001');
    });

    it('应该支持取消选择', () => {
      const { result } = renderHook(() => useAssetStore());

      act(() => {
        result.current.setSelectedAsset(mockAsset);
      });

      expect(result.current.selectedAsset).not.toBeNull();

      act(() => {
        result.current.setSelectedAsset(null);
      });

      expect(result.current.selectedAsset).toBeNull();
    });
  });

  describe('setSelectedIds', () => {
    it('应该设置选中的ID列表', () => {
      const { result } = renderHook(() => useAssetStore());

      act(() => {
        result.current.setSelectedIds(['asset-001', 'asset-002']);
      });

      expect(Array.from(result.current.selectedIds)).toEqual(['asset-001', 'asset-002']);
    });

    it('应该支持清空选择', () => {
      const { result } = renderHook(() => useAssetStore());

      act(() => {
        result.current.setSelectedIds(['asset-001']);
      });

      act(() => {
        result.current.setSelectedIds([]);
      });

      expect(Array.from(result.current.selectedIds)).toEqual([]);
    });
  });

  describe('toggleSelectedId', () => {
    it('应该添加未选中的ID', () => {
      const { result } = renderHook(() => useAssetStore());

      act(() => {
        result.current.toggleSelectedId('asset-001');
      });

      expect(result.current.selectedIds.has('asset-001')).toBe(true);
    });

    it('应该移除已选中的ID', () => {
      const { result } = renderHook(() => useAssetStore());

      act(() => {
        result.current.setSelectedIds(['asset-001', 'asset-002']);
      });

      act(() => {
        result.current.toggleSelectedId('asset-001');
      });

      expect(result.current.selectedIds.has('asset-001')).toBe(false);
      expect(result.current.selectedIds.has('asset-002')).toBe(true);
    });
  });
});

// =============================================================================
// 搜索参数测试
// =============================================================================

describe('useAssetStore - 搜索参数', () => {
  beforeEach(() => {
    useAssetStore.getState().reset();
  });

  it('应该设置搜索参数', () => {
    const { result } = renderHook(() => useAssetStore());

    act(() => {
      result.current.setSearchParams({
        page: 2,
        page_size: 50,
      });
    });

    expect(result.current.searchParams.page).toBe(2);
    expect(result.current.searchParams.page_size).toBe(50);
  });

  it('应该合并现有参数', () => {
    const { result } = renderHook(() => useAssetStore());

    act(() => {
      result.current.setSearchParams({ page: 3 });
    });

    expect(result.current.searchParams.page).toBe(3);
    expect(result.current.searchParams.page_size).toBe(20); // 保持原值
    expect(result.current.searchParams.sort_field).toBe('created_at'); // 保持原值
  });

  it('应该支持更新排序参数', () => {
    const { result } = renderHook(() => useAssetStore());

    act(() => {
      result.current.setSearchParams({
        sort_field: 'asset_name',
        sort_order: 'asc',
      });
    });

    expect(result.current.searchParams.sort_field).toBe('asset_name');
    expect(result.current.searchParams.sort_order).toBe('asc');
  });
});

// =============================================================================
// 视图模式测试
// =============================================================================

describe('useAssetStore - 视图模式', () => {
  beforeEach(() => {
    useAssetStore.getState().reset();
  });

  it('应该切换到卡片视图', () => {
    const { result } = renderHook(() => useAssetStore());

    act(() => {
      result.current.setViewMode('card');
    });

    expect(result.current.viewMode).toBe('card');
  });

  it('应该切换回表格视图', () => {
    const { result } = renderHook(() => useAssetStore());

    act(() => {
      result.current.setViewMode('card');
    });

    act(() => {
      result.current.setViewMode('table');
    });

    expect(result.current.viewMode).toBe('table');
  });
});

// =============================================================================
// 重置功能测试
// =============================================================================

describe('useAssetStore - 重置功能', () => {
  it('reset应该重置所有状态到初始值', () => {
    const { result } = renderHook(() => useAssetStore());

    // 修改各种状态
    act(() => {
      result.current.setSelectedAsset(mockAsset);
      result.current.setSelectedIds(['asset-001', 'asset-002']);
      result.current.setViewMode('card');
      result.current.setSearchParams({ page: 5, page_size: 50 });
    });

    // 验证状态已修改
    expect(result.current.selectedAsset).not.toBeNull();
    expect(result.current.selectedIds.size).toBe(2);
    expect(result.current.viewMode).toBe('card');

    // 重置
    act(() => {
      result.current.reset();
    });

    // 验证所有状态回到初始值
    expect(result.current.selectedAsset).toBeNull();
    expect(Array.from(result.current.selectedIds)).toEqual([]);
    expect(result.current.viewMode).toBe('table');
    expect(result.current.searchParams).toEqual({
      page: 1,
      page_size: 20,
      sort_field: 'created_at',
      sort_order: 'desc',
    });
  });
});
