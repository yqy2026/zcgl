import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Asset, AssetSearchParams } from '@/types/asset'

/**
 * Asset UI State Store
 *
 * 注意: 服务器数据（资产列表、分页）由 React Query 管理。
 * 此 store 仅用于 UI 状态:
 * - selectedAsset: 当前选中的资产（用于详情页面）
 * - selectedIds: 多选的资产ID（用于批量操作）
 * - searchParams: 搜索/筛选参数
 * - viewMode: 显示模式（表格/卡片）
 */
interface AssetUIState {
  // 选择状态
  selectedAsset: Asset | null
  selectedIds: string[]

  // 搜索/筛选参数
  searchParams: AssetSearchParams

  // 视图模式
  viewMode: 'table' | 'card'

  // Actions
  setSelectedAsset: (asset: Asset | null) => void
  setSelectedIds: (ids: string[]) => void
  toggleSelectedId: (id: string) => void
  setSearchParams: (params: Partial<AssetSearchParams>) => void
  setViewMode: (mode: 'table' | 'card') => void

  // 重置状态
  reset: () => void
}

const initialState = {
  selectedAsset: null,
  selectedIds: [],
  searchParams: {
    page: 1,
    limit: 20,
    sort_field: 'created_at',
    sort_order: 'desc' as const,
  },
  viewMode: 'table' as const,
}

export const useAssetStore = create<AssetUIState>()(
  devtools(
    (set) => ({
      ...initialState,

      setSelectedAsset: (asset) => set({ selectedAsset: asset }),

      setSelectedIds: (ids) => set({ selectedIds: ids }),

      toggleSelectedId: (id) =>
        set((state) => ({
          selectedIds: state.selectedIds.includes(id)
            ? state.selectedIds.filter((i) => i !== id)
            : [...state.selectedIds, id]
        })),

      setSearchParams: (params) =>
        set((state) => ({
          searchParams: { ...state.searchParams, ...params }
        })),

      setViewMode: (mode) => set({ viewMode: mode }),

      reset: () => set(initialState),
    }),
    {
      name: 'asset-ui-store',
    }
  )
)
