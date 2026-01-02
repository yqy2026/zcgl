/**
 * 权属方数据管理Hook
 * 基于React Query优化，避免重复请求
 */

import { useQuery } from '@tanstack/react-query'
import { ownershipService } from '@/services/ownershipService'
import type { Ownership } from '@/types/ownership'

interface UseOwnershipOptionsResult {
  ownerships: Ownership[]
  loading: boolean
  error: string | null
  refresh: () => void
}

/**
 * 获取权属方选项列表
 */
export const useOwnershipOptions = (isActive: boolean = true): UseOwnershipOptionsResult => {
  const queryKey = ['ownership-options', isActive]

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: async () => {
      try {
        const response = await ownershipService.getOwnershipOptions(isActive)
        return response
      } catch (err) {
        console.error(err)
        throw err
      }
    },
    staleTime: 10 * 60 * 1000, // 10分钟缓存
    gcTime: 30 * 60 * 1000, // 30分钟保留缓存 (React Query v4)
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: 1
  })

  return {
    ownerships: (data || []) as Ownership[],
    loading: isLoading,
    error: error?.message || null,
    refresh: refetch
  }
}

interface UseOwnershipDetailResult {
  ownership: Ownership | null
  loading: boolean
  error: string | null
  refresh: () => void
}

/**
 * 获取单个权属方详情
 */
export const useOwnershipDetail = (id?: string): UseOwnershipDetailResult => {
  const queryKey = ['ownership-detail', id]

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: async () => {
      if (!id) return null
      try {
        const response = await ownershipService.getOwnership(id)
        return response
      } catch (err) {
        console.error(err)
        throw err
      }
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    gcTime: 15 * 60 * 1000, // 15分钟保留缓存 (React Query v4)
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: 1,
    enabled: !!id
  })

  return {
    ownership: (data || null) as Ownership | null,
    loading: isLoading,
    error: error?.message || null,
    refresh: refetch
  }
}