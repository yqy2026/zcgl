/**
 * 统一字典Hook
 * 提供简单易用的字典数据获取和管理功能
 */

import { useState, useEffect, useCallback } from 'react'
import { useQuery, useQueries } from '@tanstack/react-query'
import { unifiedDictionaryService } from '../services/dictionary'
import type { DictionaryOption, DictionaryServiceResult } from '../services/dictionary'
import { createLogger } from '../utils/logger'

const dictLogger = createLogger('useDictionary')

interface UseDictionaryResult {
  options: DictionaryOption[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

/**
 * 使用字典数据的Hook - 基于React Query优化
 */
export const useDictionary = (dictType: string, isActive: boolean = true): UseDictionaryResult => {
  const queryKey = ['dictionary', dictType, isActive]

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: async () => {
      if (!dictType) return { success: false, data: [], error: '字典类型不能为空' }

      const result: DictionaryServiceResult = await unifiedDictionaryService.getOptions(dictType, {
        useCache: true,
        useFallback: true,
        isActive
      })

      return result
    },
    staleTime: 10 * 60 * 1000, // 10分钟缓存
    gcTime: 30 * 60 * 1000, // 30分钟保留缓存 (renamed from cacheTime)
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: 1,
    enabled: !!dictType
  })

  const options = data?.success ? (data.data ?? []) : []
  const errorMessage = data?.success ? null : (data?.error || error?.message || null)

  const refresh: () => Promise<void> = async () => {
    await refetch()
  }

  return {
    options,
    loading: isLoading,
    error: errorMessage,
    refresh
  }
}

/**
 * 批量使用多个字典的Hook - 基于React Query优化
 */
export const useDictionaries = (dictTypes: string[]): Record<string, UseDictionaryResult> => {
  // Use useQueries for proper React Hooks compliance
  const queryResults = useQueries({
    queries: dictTypes.map(dictType => ({
      queryKey: ['dictionary', dictType, true],
      queryFn: async () => {
        if (!dictType) return { success: false, data: [], error: '字典类型不能为空' }
        const result: DictionaryServiceResult = await unifiedDictionaryService.getOptions(dictType, {
          useCache: true,
          useFallback: true,
          isActive: true
        })
        return result
      },
      staleTime: 10 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      retry: 1,
      enabled: !!dictType
    }))
  })

  // Build results object from query results
  const results: Record<string, UseDictionaryResult> = {}
  dictTypes.forEach((dictType, index) => {
    const data = queryResults[index].data
    const error = queryResults[index].error
    const isLoading = queryResults[index].isLoading

    const options = data?.success ? (data.data ?? []) : []
    const errorMessage = data?.success ? null : (data?.error || error?.message || null)

    results[dictType] = {
      options,
      loading: isLoading,
      error: errorMessage,
      refresh: async () => {
        // This is a limitation - individual refresh not supported with useQueries
        // Users should use the main refetch from the query client
      }
    }
  })

  return results
}

/**
 * 字典管理Hook（用于管理界面）
 */
export const useDictionaryManager = () => {
  const [types, setTypes] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const loadTypes = useCallback(async () => {
    setLoading(true)
    try {
      const configs = unifiedDictionaryService.getAvailableTypes()
      const typeCodes = configs.map(config => config.code)
      setTypes(typeCodes)
    } catch (error) {
      dictLogger.error('获取字典类型失败:', error as Error)
    } finally {
      setLoading(false)
    }
  }, [])

  const createDictionary = useCallback(async (dictType: string, options: Array<{
    label: string
    value: string
    code?: string
  }>) => {
    try {
      const success = await unifiedDictionaryService.quickCreate(dictType, { options })
      if (success !== null && success !== undefined) {
        await loadTypes() // 刷新类型列表
      }
      return success
    } catch (error) {
      dictLogger.error('创建字典失败:', error as Error)
      return false
    }
  }, [loadTypes])

  const deleteDictionary = useCallback(async (dictType: string) => {
    try {
      const success = await unifiedDictionaryService.deleteType(dictType)
      if (success !== null && success !== undefined) {
        await loadTypes() // 刷新类型列表
      }
      return success
    } catch (error) {
      dictLogger.error('删除字典失败:', error as Error)
      return false
    }
  }, [loadTypes])

  useEffect(() => {
    loadTypes()
  }, [loadTypes])

  return {
    types,
    loading,
    createDictionary,
    deleteDictionary,
    refresh: loadTypes
  }
}
