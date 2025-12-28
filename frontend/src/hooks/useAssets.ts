import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { message } from 'antd'

import { assetService } from '@/services/assetService'
import { useAssetStore } from '@/store/useAssetStore'
import type {
  Asset,
  AssetSearchParams,
  AssetCreateRequest,
  AssetUpdateRequest,
} from '@/types/asset'

/**
 * 资产列表查询 Hook
 */
export const useAssets = (params?: AssetSearchParams) => {
  const { setAssets, setPagination, setLoading, setError } = useAssetStore()

  return useQuery({
    queryKey: ['assets', params],
    queryFn: async () => {
      setLoading(true)
      try {
        const result = await assetService.getAssets(params)
        setAssets((result as any).items || result)
        setPagination({
          total: result.total,
          page: result.page,
          limit: result.limit,
          hasNext: (result as any).hasNext || (result as any).has_next,
          hasPrev: (result as any).hasPrev || (result as any).has_prev,
        })
        setError(null)
        return result
      } catch (error: unknown) {
        setError(error instanceof Error ? error.message : 'Unknown error')
        throw error
      } finally {
        setLoading(false)
      }
    },
    placeholderData: (previousData) => previousData, // React Query v4 syntax
    staleTime: 30 * 1000, // 30秒内不重新请求
  })
}

/**
 * 单个资产查询 Hook
 */
export const useAsset = (id: string) => {
  const { setSelectedAsset } = useAssetStore()

  return useQuery({
    queryKey: ['asset', id],
    queryFn: async () => {
      const asset = await assetService.getAsset(id)
      setSelectedAsset(asset)
      return asset
    },
    enabled: !!id,
  })
}

/**
 * 创建资产 Hook
 */
export const useCreateAsset = () => {
  const queryClient = useQueryClient()
  const { addAsset } = useAssetStore()

  return useMutation({
    mutationFn: (data: AssetCreateRequest) => assetService.createAsset(data),
    onSuccess: (asset) => {
      // 更新缓存
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      
      // 更新状态
      addAsset(asset)
      
      message.success('资产创建成功')
    },
    onError: (error: { message: string }) => {
      message.error(`创建失败: ${error.message}`)
    },
  })
}

/**
 * 更新资产 Hook
 */
export const useUpdateAsset = () => {
  const queryClient = useQueryClient()
  const { updateAsset } = useAssetStore()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AssetUpdateRequest }) =>
      assetService.updateAsset(id, data),
    onSuccess: (asset) => {
      // 更新缓存
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['asset', asset.id] })
      
      // 更新状态
      updateAsset(asset.id, asset)
      
      message.success('资产更新成功')
    },
    onError: (error: { message: string }) => {
      message.error(`更新失败: ${error.message}`)
    },
  })
}

/**
 * 删除资产 Hook
 */
export const useDeleteAsset = () => {
  const queryClient = useQueryClient()
  const { removeAsset } = useAssetStore()

  return useMutation({
    mutationFn: (id: string) => assetService.deleteAsset(id),
    onSuccess: (_, id) => {
      // 更新缓存
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      
      // 更新状态
      removeAsset(id)
      
      message.success('资产删除成功')
    },
    onError: (error: { message: string }) => {
      message.error(`删除失败: ${error.message}`)
    },
  })
}

/**
 * 批量删除资产 Hook
 */
export const useBatchDeleteAssets = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ids: string[]) => assetService.deleteAssets(ids),
    onSuccess: (_, ids) => {
      // 更新缓存
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      
      message.success(`成功删除 ${ids.length} 个资产`)
    },
    onError: (error: { message: string }) => {
      message.error(`批量删除失败: ${error.message}`)
    },
  })
}

/**
 * 资产历史查询 Hook
 */
export const useAssetHistory = (
  assetId: string,
  page = 1,
  limit = 20,
  changeType?: string
) => {
  return useQuery({
    queryKey: ['asset-history', assetId, page, limit, changeType],
    queryFn: () => assetService.getAssetHistory(assetId, page, limit, changeType),
    enabled: !!assetId,
  })
}

/**
 * 资产统计 Hook
 */
export const useAssetStats = (filters?: Record<string, any>) => {
  return useQuery({
    queryKey: ['asset-stats', filters],
    queryFn: () => assetService.getAssetStats(filters),
    staleTime: 5 * 60 * 1000, // 5分钟缓存
  })
}

/**
 * 权属方列表 Hook
 */
export const useOwnershipEntities = () => {
  return useQuery({
    queryKey: ['ownership-entities'],
    queryFn: () => assetService.getOwnershipEntities(),
    staleTime: 10 * 60 * 1000, // 10分钟缓存
  })
}

/**
 * 管理方列表 Hook
 */
export const useManagementEntities = () => {
  return useQuery({
    queryKey: ['management-entities'],
    queryFn: () => assetService.getManagementEntities(),
    staleTime: 10 * 60 * 1000, // 10分钟缓存
  })
}

/**
 * 业态类别列表 Hook
 */
export const useBusinessCategories = () => {
  return useQuery({
    queryKey: ['business-categories'],
    queryFn: () => assetService.getBusinessCategories(),
    staleTime: 10 * 60 * 1000, // 10分钟缓存
  })
}

/**
 * 资产搜索 Hook
 */
export const useAssetSearch = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ query, filters }: { query: string; filters?: Record<string, any> }) =>
      assetService.searchAssets(query, filters),
    onSuccess: (result) => {
      // 可以选择性地更新缓存
      queryClient.setQueryData(['assets', { search: result }], result)
    },
  })
}

/**
 * 资产验证 Hook
 */
export const useValidateAsset = () => {
  return useMutation({
    mutationFn: (data: AssetCreateRequest | AssetUpdateRequest) =>
      assetService.validateAsset(data),
  })
}