/**
 * 统一字典Hook
 * 提供简单易用的字典数据获取和管理功能
 */

import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { dictionaryService, DictionaryOption } from '../services/dictionary'
import type { DictionaryServiceResult } from '../services/dictionary'

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

      const result: DictionaryServiceResult = await dictionaryService.getOptions(dictType, {
        useCache: true,
        useFallback: true,
        isActive
      })

      return result
    },
    staleTime: 10 * 60 * 1000, // 10分钟缓存
    cacheTime: 30 * 60 * 1000, // 30分钟保留缓存
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: 1,
    enabled: !!dictType
  })

  const options = data?.success ? data.data : []
  const errorMessage = data?.success ? null : (data?.error || error?.message)

  return {
    options,
    loading: isLoading,
    error: errorMessage,
    refresh: refetch
  }
}

/**
 * 批量使用多个字典的Hook - 基于React Query优化
 */
export const useDictionaries = (dictTypes: string[]): Record<string, UseDictionaryResult> => {
  const results: Record<string, UseDictionaryResult> = {}

  dictTypes.forEach(dictType => {
    const { options, loading, error, refresh } = useDictionary(dictType, true)
    results[dictType] = {
      options,
      loading,
      error,
      refresh
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
      const configs = dictionaryService.getAvailableTypes()
      const typeCodes = configs.map(config => config.code)
      setTypes(typeCodes)
    } catch (error) {
      console.error('获取字典类型失败:', error)
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
      const success = await dictionaryService.quickCreate(dictType, { options })
      if (success) {
        await loadTypes() // 刷新类型列表
      }
      return success
    } catch (error) {
      console.error('创建字典失败:', error)
      return false
    }
  }, [loadTypes])

  const deleteDictionary = useCallback(async (dictType: string) => {
    try {
      const success = await dictionaryService.deleteType(dictType)
      if (success) {
        await loadTypes() // 刷新类型列表
      }
      return success
    } catch (error) {
      console.error('删除字典失败:', error)
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