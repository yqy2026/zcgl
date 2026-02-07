/**
 * 字典Hook
 * 提供简单易用的字典数据获取和管理功能
 */

import { useState, useEffect, useCallback } from 'react';
import { useQuery, useQueries } from '@tanstack/react-query';
import { dictionaryService } from '@/services/dictionary';
import type { DictionaryOption, DictionaryServiceResult } from '@/services/dictionary';
import { createLogger } from '@/utils/logger';

const dictLogger = createLogger('useDictionary');

interface UseDictionaryResult {
  options: DictionaryOption[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

/**
 * 使用字典数据的Hook - 基于React Query优化
 */
export const useDictionary = (dictType: string, isActive: boolean = true): UseDictionaryResult => {
  const queryKey = ['dictionary', dictType, isActive];

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: async () => {
      if (!dictType) return { success: false, data: [], error: '字典类型不能为空' };

      const result: DictionaryServiceResult = await dictionaryService.getOptions(dictType, {
        useCache: true,
        useFallback: true,
        isActive,
      });

      return result;
    },
    staleTime: 10 * 60 * 1000, // 10分钟缓存
    gcTime: 30 * 60 * 1000, // 30分钟保留缓存 (renamed from cacheTime)
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: 1,
    enabled: !!dictType,
  });

  const options = data?.success === true ? (data.data ?? []) : [];
  const errorMessage = data?.success === true ? null : (data?.error ?? error?.message ?? null);

  const refresh: () => Promise<void> = async () => {
    await refetch();
  };

  return {
    options,
    isLoading: isLoading,
    error: errorMessage,
    refresh,
  };
};

/**
 * 批量使用多个字典的Hook - 基于React Query优化
 */
export const useDictionaries = (dictTypes: string[]): Record<string, UseDictionaryResult> => {
  // Use useQueries for proper React Hooks compliance
  const queryResults = useQueries({
    queries: dictTypes.map(dictType => ({
      queryKey: ['dictionary', dictType, true],
      queryFn: async () => {
        if (!dictType) return { success: false, data: [], error: '字典类型不能为空' };
        const result: DictionaryServiceResult = await dictionaryService.getOptions(dictType, {
          useCache: true,
          useFallback: true,
          isActive: true,
        });
        return result;
      },
      staleTime: 10 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      retry: 1,
      enabled: !!dictType,
    })),
  });

  // Build results object from query results
  const results: Record<string, UseDictionaryResult> = {};
  dictTypes.forEach((dictType, index) => {
    const data = queryResults[index].data;
    const error = queryResults[index].error;
    const isLoading = queryResults[index].isLoading;

    const options = data?.success === true ? (data.data ?? []) : [];
    const errorMessage = data?.success === true ? null : (data?.error ?? error?.message ?? null);

    results[dictType] = {
      options,
      isLoading: isLoading,
      error: errorMessage,
      refresh: async () => {
        // This is a limitation - individual refresh not supported with useQueries
        // Users should use the main refetch from the query client
      },
    };
  });

  return results;
};

/**
 * 字典管理Hook（用于管理界面）
 */
export const useDictionaryManager = () => {
  const [types, setTypes] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadTypes = useCallback(async () => {
    setIsLoading(true);
    try {
      const configs = dictionaryService.getAvailableTypes();
      const typeCodes = configs.map(config => config.code);
      setTypes(typeCodes);
    } catch (error) {
      dictLogger.error('获取字典类型失败:', error as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createDictionary = useCallback(
    async (
      dictType: string,
      options: Array<{
        label: string;
        value: string;
        code?: string;
      }>
    ) => {
      try {
        const result = await dictionaryService.quickCreate(dictType, { options });
        if (result.success === true) {
          await loadTypes(); // 刷新类型列表
        }
        return result.success;
      } catch (error) {
        dictLogger.error('创建字典失败:', error as Error);
        return false;
      }
    },
    [loadTypes]
  );

  const deleteDictionary = useCallback(
    async (dictType: string) => {
      try {
        const result = await dictionaryService.deleteType(dictType);
        if (result.success === true) {
          await loadTypes(); // 刷新类型列表
        }
        return result.success;
      } catch (error) {
        dictLogger.error('删除字典失败:', error as Error);
        return false;
      }
    },
    [loadTypes]
  );

  useEffect(() => {
    loadTypes();
  }, [loadTypes]);

  return {
    types,
    isLoading,
    createDictionary,
    deleteDictionary,
    refresh: loadTypes,
  };
};
