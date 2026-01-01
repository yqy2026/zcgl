/**
 * useAssetStore 测试
 * 测试资产状态管理
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAssetStore } from '../useAssetStore'
import type { Asset } from '@/types/asset'

// =============================================================================
// Mock数据
// =============================================================================

const mockAssets: Asset[] = [
  {
    id: 'asset-001',
    ownershipEntity: '权属方A',
    propertyName: '物业A',
    address: '地址A',
    ownershipStatus: '自有',
    propertyNature: '商业',
    usageStatus: '使用中',
    landArea: 1000,
    actualPropertyArea: 900,
    rentableArea: 800,
    rentedArea: 600,
    unrentedArea: 200,
    occupancyRate: 75,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'asset-002',
    ownershipEntity: '权属方B',
    propertyName: '物业B',
    address: '地址B',
    ownershipStatus: '租赁',
    propertyNature: '办公',
    usageStatus: '使用中',
    landArea: 2000,
    actualPropertyArea: 1800,
    rentableArea: 1600,
    rentedArea: 1200,
    unrentedArea: 400,
    occupancyRate: 75,
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-02T00:00:00Z',
  },
]

// =============================================================================
// 基础功能测试
// =============================================================================

describe('useAssetStore - 基础功能', () => {
  beforeEach(() => {
    // 重置store状态
    useAssetStore.getState().reset()
  })

  describe('初始化状态', () => {
    it('应该有正确的初始状态', () => {
      const { result } = renderHook(() => useAssetStore())

      expect(result.current.assets).toEqual([])
      expect(result.current.selectedAsset).toBeNull()
      expect(result.current.loading).toBe(false)
      expect(result.current.error).toBeNull()
      expect(result.current.total).toBe(0)
      expect(result.current.page).toBe(1)
      expect(result.current.limit).toBe(20)
      expect(result.current.hasNext).toBe(false)
      expect(result.current.hasPrev).toBe(false)
    })

    it('searchParams应该有正确的初始值', () => {
      const { result } = renderHook(() => useAssetStore())

      expect(result.current.searchParams).toEqual({
        page: 1,
        limit: 20,
        sort_field: 'created_at',
        sort_order: 'desc',
      })
    })
  })

  describe('setAssets', () => {
    it('应该设置资产列表', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setAssets(mockAssets)
      })

      expect(result.current.assets).toEqual(mockAssets)
      expect(result.current.assets).toHaveLength(2)
    })

    it('应该覆盖现有资产', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setAssets([mockAssets[0]])
      })

      expect(result.current.assets).toHaveLength(1)

      act(() => {
        result.current.setAssets(mockAssets)
      })

      expect(result.current.assets).toHaveLength(2)
    })

    it('应该接受空数组', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setAssets([])
      })

      expect(result.current.assets).toEqual([])
    })
  })

  describe('setSelectedAsset', () => {
    it('应该设置选中的资产', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setSelectedAsset(mockAssets[0])
      })

      expect(result.current.selectedAsset).toEqual(mockAssets[0])
      expect(result.current.selectedAsset?.id).toBe('asset-001')
    })

    it('应该支持取消选择', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setSelectedAsset(mockAssets[0])
      })

      expect(result.current.selectedAsset).not.toBeNull()

      act(() => {
        result.current.setSelectedAsset(null)
      })

      expect(result.current.selectedAsset).toBeNull()
    })

    it('应该支持切换选中的资产', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setSelectedAsset(mockAssets[0])
      })

      expect(result.current.selectedAsset?.id).toBe('asset-001')

      act(() => {
        result.current.setSelectedAsset(mockAssets[1])
      })

      expect(result.current.selectedAsset?.id).toBe('asset-002')
    })
  })

  describe('setSearchParams', () => {
    it('应该设置搜索参数', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setSearchParams({
          page: 2,
          limit: 50
        })
      })

      expect(result.current.searchParams.page).toBe(2)
      expect(result.current.searchParams.limit).toBe(50)
    })

    it('应该合并现有参数', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setSearchParams({ page: 3 })
      })

      expect(result.current.searchParams.page).toBe(3)
      expect(result.current.searchParams.limit).toBe(20) // 保持原值
      expect(result.current.searchParams.sort_field).toBe('created_at') // 保持原值
    })

    it('应该支持完全不同的参数集', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setSearchParams({
          sort_field: 'property_name',
          sort_order: 'asc'
        })
      })

      expect(result.current.searchParams.sort_field).toBe('property_name')
      expect(result.current.searchParams.sort_order).toBe('asc')
    })
  })

  describe('setLoading', () => {
    it('应该设置加载状态', () => {
      const { result } = renderHook(() => useAssetStore())

      expect(result.current.loading).toBe(false)

      act(() => {
        result.current.setLoading(true)
      })

      expect(result.current.loading).toBe(true)

      act(() => {
        result.current.setLoading(false)
      })

      expect(result.current.loading).toBe(false)
    })
  })

  describe('setError', () => {
    it('应该设置错误信息', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setError('网络错误')
      })

      expect(result.current.error).toBe('网络错误')

      act(() => {
        result.current.setError(null)
      })

      expect(result.current.error).toBeNull()
    })

    it('应该支持清除错误', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setError('加载失败')
      })

      expect(result.current.error).toBe('加载失败')

      act(() => {
        result.current.setError(null)
      })

      expect(result.current.error).toBeNull()
    })
  })

  describe('setPagination', () => {
    it('应该设置分页信息', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setPagination({
          total: 100,
          page: 2,
          limit: 20,
          hasNext: true,
          hasPrev: true
        })
      })

      expect(result.current.total).toBe(100)
      expect(result.current.page).toBe(2)
      expect(result.current.limit).toBe(20)
      expect(result.current.hasNext).toBe(true)
      expect(result.current.hasPrev).toBe(true)
    })

    it('应该支持部分分页更新', () => {
      const { result } = renderHook(() => useAssetStore())

      const initialTotal = result.current.total

      act(() => {
        result.current.setPagination({
          total: initialTotal + 10,
          page: result.current.page + 1,
          limit: result.current.limit,
          hasNext: false,
          hasPrev: result.current.hasPrev
        })
      })

      expect(result.current.total).toBe(initialTotal + 10)
    })
  })
})

// =============================================================================
// 资产操作测试
// =============================================================================

describe('useAssetStore - 资产操作', () => {
  beforeEach(() => {
    useAssetStore.getState().reset()
    // 设置初始资产
    useAssetStore.getState().setAssets(mockAssets)
    useAssetStore.getState().setPagination({
      total: 2,
      page: 1,
      limit: 20,
      hasNext: false,
      hasPrev: false
    })
  })

  describe('addAsset', () => {
    it('应该添加新资产到列表顶部', () => {
      const { result } = renderHook(() => useAssetStore())

      const newAsset: Asset = {
        id: 'asset-003',
        ownershipEntity: '权属方C',
        propertyName: '物业C',
        address: '地址C',
        ownershipStatus: '自有',
        propertyNature: '住宅',
        usageStatus: '空闲',
        landArea: 1500,
        actualPropertyArea: 1400,
        rentableArea: 1300,
        rentedArea: 0,
        unrentedArea: 1300,
        occupancyRate: 0,
        createdAt: '2024-01-03T00:00:00Z',
        updatedAt: '2024-01-03T00:00:00Z',
      }

      act(() => {
        result.current.addAsset(newAsset)
      })

      expect(result.current.assets).toHaveLength(3)
      expect(result.current.assets[0].id).toBe('asset-003')
      expect(result.current.total).toBe(3)
    })

    it('应该保持总计数同步', () => {
      const { result } = renderHook(() => useAssetStore())

      const initialTotal = result.current.total

      act(() => {
        result.current.addAsset(mockAssets[0])
      })

      expect(result.current.total).toBe(initialTotal + 1)
    })
  })

  describe('updateAsset', () => {
    it('应该更新指定ID的资产', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.updateAsset('asset-001', {
          propertyName: '更新后的物业A'
        })
      })

      const updatedAsset = result.current.assets.find(a => a.id === 'asset-001')
      expect(updatedAsset?.propertyName).toBe('更新后的物业A')

      // 其他资产不变
      const unchangedAsset = result.current.assets.find(a => a.id === 'asset-002')
      expect(unchangedAsset?.propertyName).toBe('物业B')
    })

    it('应该更新多个字段', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.updateAsset('asset-001', {
          propertyName: '新名称',
          occupancyRate: 80
        })
      })

      const updatedAsset = result.current.assets.find(a => a.id === 'asset-001')
      expect(updatedAsset?.propertyName).toBe('新名称')
      expect(updatedAsset?.occupancyRate).toBe(80)
    })

    it('更新不存在的资产不应该改变列表', () => {
      const { result } = renderHook(() => useAssetStore())

      const initialAssets = result.current.assets

      act(() => {
        result.current.updateAsset('non-existent-id', {
          propertyName: '新名称'
        })
      })

      expect(result.current.assets).toEqual(initialAssets)
    })

    it('应该同步更新选中的资产', () => {
      const { result } = renderHook(() => useAssetStore())

      // 先选中一个资产
      act(() => {
        result.current.setSelectedAsset(mockAssets[0])
      })

      expect(result.current.selectedAsset?.propertyName).toBe('物业A')

      // 更新该资产
      act(() => {
        result.current.updateAsset('asset-001', {
          propertyName: '已更新的物业A'
        })
      })

      // 选中资产应该也被更新
      expect(result.current.selectedAsset?.propertyName).toBe('已更新的物业A')
      expect(result.current.selectedAsset?.id).toBe('asset-001')
    })

    it('更新其他资产不应该影响选中资产', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setSelectedAsset(mockAssets[0])
      })

      const selectedId = result.current.selectedAsset?.id

      act(() => {
        result.current.updateAsset('asset-002', {
          propertyName: '新物业B'
        })
      })

      // 选中资产不变
      expect(result.current.selectedAsset?.id).toBe(selectedId)
      expect(result.current.selectedAsset?.propertyName).toBe('物业A')
    })
  })

  describe('removeAsset', () => {
    it('应该删除指定ID的资产', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.removeAsset('asset-001')
      })

      expect(result.current.assets).toHaveLength(1)
      expect(result.current.assets[0].id).toBe('asset-002')
      expect(result.current.total).toBe(1)
    })

    it('删除不存在的资产不应该改变列表', () => {
      const { result } = renderHook(() => useAssetStore())

      const _initialCount = result.current.assets.length

      act(() => {
        result.current.removeAsset('non-existent-id')
      })

      expect(result.current.assets).toHaveLength(initialCount)
    })

    it('删除资产后应该取消选中', () => {
      const { result } = renderHook(() => useAssetStore())

      // 先选中asset-001
      act(() => {
        result.current.setSelectedAsset(mockAssets[0])
      })

      expect(result.current.selectedAsset?.id).toBe('asset-001')

      // 删除asset-001
      act(() => {
        result.current.removeAsset('asset-001')
      })

      // 选中资产应该被取消
      expect(result.current.selectedAsset).toBeNull()
    })

    it('删除其他资产不应该影响选中资产', () => {
      const { result } = renderHook(() => useAssetStore())

      act(() => {
        result.current.setSelectedAsset(mockAssets[0])
      })

      act(() => {
        result.current.removeAsset('asset-002')
      })

      // 选中资产不变
      expect(result.current.selectedAsset?.id).toBe('asset-001')
    })

    it('应该正确更新总计数', () => {
      const { result } = renderHook(() => useAssetStore())

      const initialTotal = result.current.total

      act(() => {
        result.current.removeAsset('asset-001')
      })

      expect(result.current.total).toBe(initialTotal - 1)
    })
  })
})

// =============================================================================
// 重置功能测试
// =============================================================================

describe('useAssetStore - 重置功能', () => {
  it('reset应该重置所有状态到初始值', () => {
    const { result } = renderHook(() => useAssetStore())

    // 修改各种状态
    act(() => {
      result.current.setAssets(mockAssets)
      result.current.setSelectedAsset(mockAssets[0])
      result.current.setLoading(true)
      result.current.setError('测试错误')
      result.current.setPagination({
        total: 100,
        page: 5,
        limit: 50,
        hasNext: true,
        hasPrev: true
      })
      })

    // 验证状态已修改
    expect(result.current.assets).toHaveLength(2)
    expect(result.current.selectedAsset).not.toBeNull()
    expect(result.current.loading).toBe(true)
    expect(result.current.error).toBe('测试错误')
    expect(result.current.total).toBe(100)

    // 重置
    act(() => {
      result.current.reset()
    })

    // 验证所有状态回到初始值
    expect(result.current.assets).toEqual([])
    expect(result.current.selectedAsset).toBeNull()
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(result.current.total).toBe(0)
    expect(result.current.page).toBe(1)
    expect(result.current.limit).toBe(20)
    expect(result.current.hasNext).toBe(false)
    expect(result.current.hasPrev).toBe(false)
  })

  it('reset应该重置搜索参数', () => {
    const { result } = renderHook(() => useAssetStore())

    // 修改搜索参数
    act(() => {
      result.current.setSearchParams({
        page: 10,
        limit: 100,
        sort_field: 'property_name',
        sort_order: 'asc'
      })
    })

    expect(result.current.searchParams.page).toBe(10)

    // 重置
    act(() => {
      result.current.reset()
    })

    // 搜索参数应该回到初始值
    expect(result.current.searchParams).toEqual({
      page: 1,
      limit: 20,
      sort_field: 'created_at',
      sort_order: 'desc',
    })
  })
})

// =============================================================================
// 边界情况测试
// =============================================================================

describe('useAssetStore - 边界情况', () => {
  it('应该处理空资产列表的更新', () => {
    const { result } = renderHook(() => useAssetStore())

    expect(() => {
      act(() => {
        result.current.updateAsset('non-existent', { propertyName: '测试' })
      })
    }).not.toThrow()
  })

  it('应该处理null选中资产', () => {
    const { result } = renderHook(() => useAssetStore())

    act(() => {
      result.current.setSelectedAsset(null)
    })

    expect(result.current.selectedAsset).toBeNull()

    // 更新不存在的资产不应该影响null选中状态
    act(() => {
      result.current.updateAsset('any-id', { propertyName: '测试' })
    })

    expect(result.current.selectedAsset).toBeNull()
  })

  it('应该处理连续添加多个资产', () => {
    const { result } = renderHook(() => useAssetStore())

    mockAssets.forEach(asset => {
      act(() => {
        result.current.addAsset(asset)
      })
    })

    expect(result.current.assets).toHaveLength(2)
    expect(result.current.total).toBe(2)
  })

  it('应该处理批量删除', () => {
    const { result } = renderHook(() => useAssetStore())

    // 添加多个资产
    act(() => {
      result.current.setAssets(mockAssets)
    })

    const _initialCount = result.current.assets.length

    // 逐个删除
    result.current.assets.forEach(asset => {
      act(() => {
        result.current.removeAsset(asset.id)
      })
    })

    expect(result.current.assets).toHaveLength(0)
    expect(result.current.total).toBe(0)
  })
})
