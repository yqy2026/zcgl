import { useQuery } from '@tanstack/react-query'
import { analyticsService } from '../services/analyticsService'
import type { AssetSearchParams } from '../types/asset'

export const useAnalytics = (filters?: AssetSearchParams) => {
  return useQuery({
    queryKey: ['analytics', filters],
    queryFn: () => analyticsService.getComprehensiveAnalytics(filters),
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    cacheTime: 10 * 60 * 1000, // 10分钟缓存
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    onError: (error) => {
      console.error('Analytics query error:', error)
    }
  })
}

export const useBasicStatistics = (filters?: AssetSearchParams) => {
  return useQuery({
    queryKey: ['basic-statistics', filters],
    queryFn: () => analyticsService.getBasicStatistics(filters),
    staleTime: 2 * 60 * 1000, // 2分钟缓存
    cacheTime: 5 * 60 * 1000, // 5分钟缓存
  })
}

export const useAreaSummary = () => {
  return useQuery({
    queryKey: ['area-summary'],
    queryFn: () => analyticsService.getAreaSummary(),
    staleTime: 3 * 60 * 1000, // 3分钟缓存
    cacheTime: 6 * 60 * 1000, // 6分钟缓存
  })
}

export const useFinancialSummary = () => {
  return useQuery({
    queryKey: ['financial-summary'],
    queryFn: () => analyticsService.getFinancialSummary(),
    staleTime: 3 * 60 * 1000, // 3分钟缓存
    cacheTime: 6 * 60 * 1000, // 6分钟缓存
  })
}