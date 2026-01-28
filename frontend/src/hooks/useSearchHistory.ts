import { useState, useEffect, useCallback } from 'react';
import type { AssetSearchParams } from '@/types/asset';
import { createLogger } from '@/utils/logger';

const searchLogger = createLogger('SearchHistory');

export interface SearchHistoryItem {
  id: string;
  name: string;
  conditions: AssetSearchParams;
  createdAt: string;
  usageCount: number;
}

const STORAGE_KEY = 'asset_search_history';
const MAX_HISTORY_ITEMS = 10;

export const useSearchHistory = () => {
  const [searchHistory, setSearchHistory] = useState<SearchHistoryItem[]>([]);

  // 从localStorage加载搜索历史
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored != null) {
        const history = JSON.parse(stored);
        setSearchHistory(history);
      }
    } catch (error) {
      searchLogger.error('Failed to load search history:', error as Error);
    }
  }, []);

  // 保存搜索历史到localStorage
  const saveToStorage = useCallback((history: SearchHistoryItem[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (error) {
      searchLogger.error('Failed to save search history:', error as Error);
    }
  }, []);

  // 添加搜索记录
  const addSearchHistory = useCallback(
    (historyItem: {
      id: string;
      name: string;
      conditions: AssetSearchParams;
      createdAt: string;
    }) => {
      const { id, name, conditions, createdAt } = historyItem;
      const newItem: SearchHistoryItem = {
        id: id || Date.now().toString(),
        name,
        conditions,
        createdAt: createdAt || new Date().toISOString(),
        usageCount: 1,
      };

      setSearchHistory(prev => {
        // 检查是否已存在相同的搜索条件
        const existingIndex = prev.findIndex(
          item => JSON.stringify(item.conditions) === JSON.stringify(conditions)
        );

        let newHistory: SearchHistoryItem[];

        if (existingIndex >= 0) {
          // 如果存在，更新使用次数和时间
          newHistory = [...prev];
          newHistory[existingIndex] = {
            ...newHistory[existingIndex],
            usageCount: newHistory[existingIndex].usageCount + 1,
            createdAt: new Date().toISOString(),
          };
        } else {
          // 如果不存在，添加新记录
          newHistory = [newItem, ...prev];

          // 限制历史记录数量
          if (newHistory.length > MAX_HISTORY_ITEMS) {
            newHistory = newHistory.slice(0, MAX_HISTORY_ITEMS);
          }
        }

        // 按使用次数和时间排序
        newHistory.sort((a, b) => {
          if (a.usageCount !== b.usageCount) {
            return b.usageCount - a.usageCount;
          }
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        });

        saveToStorage(newHistory);
        return newHistory;
      });
    },
    [saveToStorage]
  );

  // 删除搜索记录
  const removeSearchHistory = useCallback(
    (id: string) => {
      setSearchHistory(prev => {
        const newHistory = prev.filter(item => item.id !== id);
        saveToStorage(newHistory);
        return newHistory;
      });
    },
    [saveToStorage]
  );

  // 清空搜索历史
  const clearSearchHistory = useCallback(() => {
    setSearchHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  // 更新搜索记录名称
  const updateSearchHistoryName = useCallback(
    (id: string, newName: string) => {
      setSearchHistory(prev => {
        const newHistory = prev.map(item => (item.id === id ? { ...item, name: newName } : item));
        saveToStorage(newHistory);
        return newHistory;
      });
    },
    [saveToStorage]
  );

  return {
    searchHistory,
    addSearchHistory,
    removeSearchHistory,
    clearSearchHistory,
    updateSearchHistoryName,
  };
};
