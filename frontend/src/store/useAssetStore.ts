import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Asset, AssetSearchParams } from '@/types/asset'

interface AssetState {
  // 资产列表状态
  assets: Asset[]
  selectedAsset: Asset | null
  searchParams: AssetSearchParams
  loading: boolean
  error: string | null
  
  // 分页状态
  total: number
  page: number
  limit: number
  hasNext: boolean
  hasPrev: boolean
  
  // Actions
  setAssets: (assets: Asset[]) => void
  setSelectedAsset: (asset: Asset | null) => void
  setSearchParams: (params: AssetSearchParams) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setPagination: (pagination: {
    total: number
    page: number
    limit: number
    hasNext: boolean
    hasPrev: boolean
  }) => void
  
  // 资产操作
  addAsset: (asset: Asset) => void
  updateAsset: (id: string, updates: Partial<Asset>) => void
  removeAsset: (id: string) => void
  
  // 重置状态
  reset: () => void
}

const initialState = {
  assets: [],
  selectedAsset: null,
  searchParams: {
    page: 1,
    limit: 20,
    sort_field: 'created_at',
    sort_order: 'desc' as const,
  },
  loading: false,
  error: null,
  total: 0,
  page: 1,
  limit: 20,
  hasNext: false,
  hasPrev: false,
}

export const useAssetStore = create<AssetState>()(
  devtools(
    (set, get) => ({
      ...initialState,
      
      setAssets: (assets) => set({ assets }),
      
      setSelectedAsset: (asset) => set({ selectedAsset: asset }),
      
      setSearchParams: (params) => 
        set((state) => ({ 
          searchParams: { ...state.searchParams, ...params } 
        })),
      
      setLoading: (loading) => set({ loading }),
      
      setError: (error) => set({ error }),
      
      setPagination: (pagination) => set(pagination),
      
      addAsset: (asset) => 
        set((state) => ({ 
          assets: [asset, ...state.assets],
          total: state.total + 1 
        })),
      
      updateAsset: (id, updates) =>
        set((state) => ({
          assets: state.assets.map((asset) =>
            asset.id === id ? { ...asset, ...updates } : asset
          ),
          selectedAsset: state.selectedAsset?.id === id 
            ? { ...state.selectedAsset, ...updates }
            : state.selectedAsset
        })),
      
      removeAsset: (id) =>
        set((state) => ({
          assets: state.assets.filter((asset) => asset.id !== id),
          selectedAsset: state.selectedAsset?.id === id ? null : state.selectedAsset,
          total: state.total - 1
        })),
      
      reset: () => set(initialState),
    }),
    {
      name: 'asset-store',
    }
  )
)