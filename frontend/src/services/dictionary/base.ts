/**
 * 基础字典服务 - 统一响应处理版本
 *
 * @description 提供核心的字典数据获取功能，支持缓存、批量操作、预加载等高级特性
 * @author Claude Code
 * @updated 2025-11-10
 */

import { enhancedApiClient } from '@/api/client';
import { ApiErrorHandler } from '../../utils/responseExtractor';
import {
  DictionaryConfig,
  DictionaryOption,
  DICTIONARY_CONFIGS,
  getDictionaryConfig
} from './config';

// 字典服务结果接口
export interface DictionaryServiceResult {
  success: boolean;
  data: DictionaryOption[];
  error?: string;
  source: 'api' | 'fallback' | 'cache';
  metadata?: {
    totalItems?: number;
    activeItems?: number;
    lastUpdated?: string;
    cacheTimestamp?: number;
  };
}

// 字典统计信息接口
export interface DictionaryStatistics {
  totalTypes: number;
  cachedTypes: number;
  totalItems: number;
  activeItems: number;
  cacheSize: number;
  lastCacheCleanup: number;
  cacheHitRate: number;
  mostUsedTypes: Array<{
    type: string;
    hitCount: number;
    lastAccessed: string;
  }>;
}

// 字典预加载结果接口
export interface PreloadResult {
  success: boolean;
  loadedTypes: string[];
  failedTypes: Array<{
    type: string;
    error: string;
  }>;
  totalItems: number;
  loadTime: number; // 毫秒
}

// 字典缓存项接口
interface CacheItem {
  data: DictionaryOption[];
  timestamp: number;
  hitCount: number;
  lastAccessed: number;
  metadata: {
    totalItems?: number;
    activeItems?: number;
    source: string;
  };
}

/**
 * 增强的字典缓存管理
 */
class DictionaryCache {
  private cache = new Map<string, CacheItem>();
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5分钟缓存
  private readonly MAX_CACHE_SIZE = 100; // 最大缓存数量
  private hitCount = 0;
  private missCount = 0;
  private lastCleanup = Date.now();

  /**
   * 获取最后一次清理时间
   */
  public getLastCleanup(): number {
    return this.lastCleanup;
  }

  get(dictType: string): DictionaryOption[] | null {
    const cached = this.cache.get(dictType);
    if (!cached) {
      this.missCount++;
      return null;
    }

    // 检查是否过期
    if (Date.now() - cached.timestamp > this.CACHE_TTL) {
      this.cache.delete(dictType);
      this.missCount++;
      return null;
    }

    // 更新访问统计
    cached.hitCount++;
    cached.lastAccessed = Date.now();
    this.hitCount++;

    return cached.data;
  }

  set(dictType: string, data: DictionaryOption[], metadata?: Partial<CacheItem['metadata']>): void {
    const item: CacheItem = {
      data,
      timestamp: Date.now(),
      hitCount: 0,
      lastAccessed: Date.now(),
      metadata: {
        totalItems: data.length,
        activeItems: data.filter(item => item.isActive !== false).length,
        source: 'api',
        ...metadata
      }
    };

    this.cache.set(dictType, item);

    // 定期清理过期缓存
    this.periodicCleanup();
  }

  delete(dictType: string): boolean {
    return this.cache.delete(dictType);
  }

  clear(): void {
    this.cache.clear();
    this.hitCount = 0;
    this.missCount = 0;
    this.lastCleanup = Date.now();
  }

  clearForType(dictType: string): void {
    this.cache.delete(dictType);
  }

  // 清理过期和最少使用的缓存项
  private periodicCleanup(): void {
    const now = Date.now();

    // 每10分钟清理一次
    if (now - this.lastCleanup < 10 * 60 * 1000) {
      return;
    }

    // 1. 清理过期项
    for (const [key, item] of this.cache.entries()) {
      if (now - item.timestamp > this.CACHE_TTL) {
        this.cache.delete(key);
      }
    }

    // 2. 如果缓存过多，清理最少使用的项
    if (this.cache.size > this.MAX_CACHE_SIZE) {
      const sortedItems = Array.from(this.cache.entries())
        .sort(([, a], [, b]) => {
          // 优先删除命中次数少的，其次是最后访问时间早的
          if (a.hitCount !== b.hitCount) {
            return a.hitCount - b.hitCount;
          }
          return a.lastAccessed - b.lastAccessed;
        });

      const itemsToDelete = sortedItems.slice(0, this.cache.size - this.MAX_CACHE_SIZE);
      itemsToDelete.forEach(([key]) => this.cache.delete(key));
    }

    this.lastCleanup = now;
  }

  getCacheInfo(): {
    keys: string[];
    size: number;
    hitRate: number;
    totalHits: number;
    totalMisses: number;
  } {
    const total = this.hitCount + this.missCount;
    return {
      keys: Array.from(this.cache.keys()),
      size: this.cache.size,
      hitRate: total > 0 ? this.hitCount / total : 0,
      totalHits: this.hitCount,
      totalMisses: this.missCount
    };
  }

  getDetailedInfo(): Array<{
    type: string;
    itemCount: number;
    hitCount: number;
    lastAccessed: string;
    age: number;
    isExpired: boolean;
  }> {
    const now = Date.now();
    return Array.from(this.cache.entries()).map(([type, item]) => ({
      type,
      itemCount: item.data.length,
      hitCount: item.hitCount,
      lastAccessed: new Date(item.lastAccessed).toISOString(),
      age: now - item.timestamp,
      isExpired: now - item.timestamp > this.CACHE_TTL
    }));
  }

  preloadCache(dictTypes: string[]): Map<string, DictionaryOption[]> {
    const preloaded = new Map<string, DictionaryOption[]>();

    for (const type of dictTypes) {
      const cached = this.cache.get(type);
      if (cached) {
        preloaded.set(type, cached.data);
      }
    }

    return preloaded;
  }
}

const cache = new DictionaryCache();

/**
 * 基础字典服务类
 */
class BaseDictionaryService {
  private readonly BATCH_SIZE = 10; // 批量请求的分批大小
  private readonly REQUEST_TIMEOUT = 8000; // 请求超时时间

  /**
   * 获取字典选项（核心方法）
   */
  async getOptions(
    dictType: string,
    options: {
      useCache?: boolean;
      useFallback?: boolean;
      isActive?: boolean;
      forceRefresh?: boolean;
      includeMetadata?: boolean;
    } = {}
  ): Promise<DictionaryServiceResult> {
    const {
      useCache = true,
      useFallback = true,
      isActive = true,
      forceRefresh = false,
      includeMetadata = false
    } = options;

    // 检查字典类型是否存在
    const config = getDictionaryConfig(dictType);
    if (!config) {
      return {
        success: false,
        data: [],
        error: `字典类型不存在: ${dictType}`,
        source: 'fallback',
        metadata: includeMetadata ? {
          totalItems: 0,
          activeItems: 0,
          lastUpdated: new Date().toISOString()
        } : undefined
      };
    }

    // 强制刷新时清除缓存
    if (forceRefresh) {
      cache.clearForType(dictType);
    }

    // 检查缓存
    if (useCache && !forceRefresh) {
      const cached = cache.get(dictType);
      if (cached) {
        const result: DictionaryServiceResult = {
          success: true,
          data: cached,
          source: 'cache'
        };

        if (includeMetadata) {
          const cacheInfo = cache.getDetailedInfo().find(info => info.type === dictType);
          result.metadata = {
            totalItems: cached.length,
            activeItems: cached.filter(item => item.isActive !== false).length,
            lastUpdated: cacheInfo ? new Date(cacheInfo.lastAccessed).toISOString() : new Date().toISOString(),
            cacheTimestamp: Date.now()
          };
        }

        return result;
      }
    }

    // 尝试从API获取
    try {
      const result = await enhancedApiClient.get<DictionaryOption[]>(
        config.apiEndpoint,
        {
          params: { is_active: isActive },
          timeout: this.REQUEST_TIMEOUT,
          cache: false, // 使用自定义缓存
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取字典数据失败: ${result.error}`);
      }

      const data = result.data!;

      // 缓存数据
      if (useCache) {
        cache.set(dictType, data, {
          source: 'api',
          totalItems: data.length,
          activeItems: data.filter(item => item.isActive !== false).length
        });
      }

      const response: DictionaryServiceResult = {
        success: true,
        data,
        source: 'api'
      };

      if (includeMetadata) {
        response.metadata = {
          totalItems: data.length,
          activeItems: data.filter(item => item.isActive !== false).length,
          lastUpdated: new Date().toISOString()
        };
      }

      return response;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);

      // 如果启用备用数据，返回备用数据
      if (useFallback && config.fallbackOptions != null) {
        const fallbackData = config.fallbackOptions.filter(option =>
          isActive ? option.isActive !== false : true
        );

        if (useCache) {
          cache.set(dictType, fallbackData, {
            source: 'fallback',
            totalItems: fallbackData.length,
            activeItems: fallbackData.filter(item => item.isActive !== false).length
          });
        }

        const response: DictionaryServiceResult = {
          success: true,
          data: fallbackData,
          source: 'fallback',
          error: enhancedError.message
        };

        if (includeMetadata) {
          response.metadata = {
            totalItems: fallbackData.length,
            activeItems: fallbackData.filter(item => item.isActive !== false).length,
            lastUpdated: new Date().toISOString()
          };
        }

        return response;
      }

      return {
        success: false,
        data: [],
        error: enhancedError.message,
        source: 'fallback',
        metadata: includeMetadata ? {
          totalItems: 0,
          activeItems: 0,
          lastUpdated: new Date().toISOString()
        } : undefined
      };
    }
  }

  /**
   * 批量获取字典选项（优化版本）
   */
  async getBatchOptions(
    dictTypes: string[],
    options: {
      useCache?: boolean;
      useFallback?: boolean;
      isActive?: boolean;
      forceRefresh?: boolean;
      includeMetadata?: boolean;
    } = {}
  ): Promise<Record<string, DictionaryServiceResult>> {
    const {
      useCache = true,
      useFallback = true,
      isActive = true,
      forceRefresh = false,
      includeMetadata = false
    } = options;

    // 预加载缓存数据
    const preloaded = useCache && !forceRefresh ? cache.preloadCache(dictTypes) : new Map();

    const results: Record<string, DictionaryServiceResult> = {};
    const typesToFetch: string[] = [];

    // 首先处理已缓存的数据
    for (const dictType of dictTypes) {
      const cached = preloaded.get(dictType);
      if (cached != null && !forceRefresh) {
        results[dictType] = {
          success: true,
          data: cached,
          source: 'cache',
          metadata: includeMetadata ? {
            totalItems: cached.length,
            activeItems: cached.filter((item: DictionaryOption) => item.isActive !== false).length,
            lastUpdated: new Date().toISOString(),
            cacheTimestamp: Date.now()
          } : undefined
        };
      } else {
        typesToFetch.push(dictType);
      }
    }

    // 分批获取未缓存的数据
    if (typesToFetch.length > 0) {
      const batches = this.chunkArray(typesToFetch, this.BATCH_SIZE);

      for (const batch of batches) {
        const batchPromises = batch.map(async (dictType) => {
          try {
            const result = await this.getOptions(dictType, {
              useCache,
              useFallback,
              isActive,
              forceRefresh,
              includeMetadata
            });
            return { dictType, result };
          } catch (error) {
            const enhancedError = ApiErrorHandler.handleError(error);
            return {
              dictType,
              result: {
                success: false,
                data: [],
                error: enhancedError.message,
                source: 'fallback' as const,
                metadata: includeMetadata ? {
                  totalItems: 0,
                  activeItems: 0,
                  lastUpdated: new Date().toISOString()
                } : undefined
              }
            };
          }
        });

        const batchResults = await Promise.allSettled(batchPromises);

        batchResults.forEach((promiseResult) => {
          if (promiseResult.status === 'fulfilled') {
            const { dictType, result } = promiseResult.value;
            results[dictType] = result;
          } else {
            // 处理Promise拒绝的情况
            console.error('批量获取字典数据失败:', promiseResult.reason);
          }
        });
      }
    }

    return results;
  }

  /**
   * 并行获取多个字典类型（高性能版本）
   */
  async getParallelOptions(
    dictTypes: string[],
    options: {
      useCache?: boolean;
      useFallback?: boolean;
      isActive?: boolean;
      timeout?: number;
    } = {}
  ): Promise<Record<string, DictionaryServiceResult>> {
    const { useCache = true, useFallback = true, isActive = true } = options;

    const promises = dictTypes.map(async (dictType) => {
      const result = await this.getOptions(dictType, { useCache, useFallback, isActive });
      return [dictType, result] as [string, DictionaryServiceResult];
    });

    // 使用Promise.allSettled确保一个失败不影响其他请求
    const settledResults = await Promise.allSettled(promises);

    const results: Record<string, DictionaryServiceResult> = {};

    settledResults.forEach((promiseResult, index) => {
      const dictType = dictTypes[index];

      if (promiseResult.status === 'fulfilled') {
        const [type, result] = promiseResult.value;
        results[type] = result;
      } else {
        const enhancedError = ApiErrorHandler.handleError(promiseResult.reason);
        results[dictType] = {
          success: false,
          data: [],
          error: enhancedError.message,
          source: 'fallback'
        };
      }
    });

    return results;
  }

  /**
   * 获取所有可用的字典类型
   */
  getAvailableTypes(): DictionaryConfig[] {
    return Object.values(DICTIONARY_CONFIGS);
  }

  /**
   * 搜索字典类型
   */
  searchTypes(keyword: string): DictionaryConfig[] {
    const lowerKeyword = keyword.toLowerCase();
    return Object.values(DICTIONARY_CONFIGS).filter(config =>
      config.name.toLowerCase().includes(lowerKeyword) ||
      config.description.toLowerCase().includes(lowerKeyword) ||
      (config.tags?.some((tag: string) => tag.toLowerCase().includes(lowerKeyword)) ?? false)
    );
  }

  /**
   * 检查字典类型是否可用
   */
  isTypeAvailable(dictType: string): boolean {
    return dictType in DICTIONARY_CONFIGS;
  }

  /**
   * 获取字典类型配置
   */
  getTypeConfig(dictType: string): DictionaryConfig | null {
    return getDictionaryConfig(dictType);
  }

  /**
   * 清除缓存
   */
  clearCache(dictType?: string): void {
    if (dictType != null) {
      cache.clearForType(dictType);
    } else {
      cache.clear();
    }
  }

  /**
   * 清除过期缓存
   */
  cleanupExpiredCache(): void {
    const detailedInfo = cache.getDetailedInfo();

    detailedInfo.forEach(info => {
      if (info.isExpired) {
        cache.clearForType(info.type);
      }
    });
  }

  /**
   * 预加载字典数据
   */
  async preload(dictTypes: string[], options: {
    useFallback?: boolean;
    batchSize?: number;
    onProgress?: (loaded: number, total: number, currentType: string) => void;
  } = {}): Promise<PreloadResult> {
    const { useFallback = false, batchSize = 5, onProgress } = options;
    const startTime = Date.now();
    const loadedTypes: string[] = [];
    const failedTypes: Array<{ type: string; error: string }> = [];
    let totalItems = 0;

    // 分批预加载
    const batches = this.chunkArray(dictTypes, batchSize);

    for (let i = 0; i < batches.length; i++) {
      const batch = batches[i];

      const batchPromises = batch.map(async (dictType) => {
        try {
          const result = await this.getOptions(dictType, {
            useCache: true,
            useFallback,
            forceRefresh: true
          });

          if (result.success) {
            loadedTypes.push(dictType);
            totalItems += result.data.length;
          } else {
            failedTypes.push({ type: dictType, error: result.error ?? 'Unknown error' });
          }

          onProgress?.(loadedTypes.length + failedTypes.length, dictTypes.length, dictType);
        } catch (error) {
          const enhancedError = ApiErrorHandler.handleError(error);
          failedTypes.push({ type: dictType, error: enhancedError.message });
          onProgress?.(loadedTypes.length + failedTypes.length, dictTypes.length, dictType);
        }
      });

      await Promise.allSettled(batchPromises);
    }

    const loadTime = Date.now() - startTime;

    return {
      success: failedTypes.length === 0,
      loadedTypes,
      failedTypes,
      totalItems,
      loadTime
    };
  }

  /**
   * 智能预加载（基于使用频率）
   */
  async smartPreload(): Promise<void> {
    const cacheInfo = cache.getDetailedInfo();
    const mostUsedTypes = cacheInfo
      .filter(info => info.hitCount > 0)
      .sort((a, b) => b.hitCount - a.hitCount)
      .slice(0, 20) // 预加载前20个最常用的类型
      .map(info => info.type);

    if (mostUsedTypes.length > 0) {
      await this.preload(mostUsedTypes, {
        useFallback: true,
        batchSize: 3 // 小批次以避免阻塞
      });
    }
  }

  /**
   * 获取字典统计信息
   */
  getStats(): DictionaryStatistics {
    const cacheInfo = cache.getCacheInfo();
    const detailedInfo = cache.getDetailedInfo();
    const mostUsedTypes = detailedInfo
      .sort((a, b) => b.hitCount - a.hitCount)
      .slice(0, 10)
      .map(info => ({
        type: info.type,
        hitCount: info.hitCount,
        lastAccessed: info.lastAccessed
      }));

    const totalItems = detailedInfo.reduce((sum, info) => sum + info.itemCount, 0);
    const activeItems = detailedInfo.reduce((sum, info) => {
      const cacheItem = cache.get(info.type);
      if (cacheItem) {
        return sum + cacheItem.filter(item => item.isActive !== false).length;
      }
      return sum;
    }, 0);

    return {
      totalTypes: Object.keys(DICTIONARY_CONFIGS).length,
      cachedTypes: cacheInfo.size,
      totalItems,
      activeItems,
      cacheSize: cacheInfo.size,
      lastCacheCleanup: cache.getLastCleanup(),
      cacheHitRate: cacheInfo.hitRate,
      mostUsedTypes
    };
  }

  /**
   * 获取详细的缓存报告
   */
  getCacheReport(): {
    summary: DictionaryStatistics;
    details: Array<{
      type: string;
      itemCount: number;
      hitCount: number;
      lastAccessed: string;
      age: number;
      isExpired: boolean;
    }>;
    recommendations: string[];
  } {
    const summary = this.getStats();
    const details = cache.getDetailedInfo();
    const recommendations: string[] = [];

    // 生成建议
    if (summary.cacheHitRate < 0.5) {
      recommendations.push('缓存命中率较低，建议增加预加载或优化缓存策略');
    }

    if (summary.cachedTypes < summary.totalTypes * 0.3) {
      recommendations.push('缓存覆盖率较低，建议预加载更多字典类型');
    }

    const expiredItems = details.filter(info => info.isExpired);
    if (expiredItems.length > 0) {
      recommendations.push(`发现${expiredItems.length}个过期缓存项，建议执行清理`);
    }

    const lowHitItems = details.filter(info => info.hitCount === 0 && info.age > 30 * 60 * 1000);
    if (lowHitItems.length > 0) {
      recommendations.push(`发现${lowHitItems.length}个长期未使用的缓存项，建议清理`);
    }

    return {
      summary,
      details,
      recommendations
    };
  }

  /**
   * 刷新指定的字典类型
   */
  async refreshTypes(dictTypes: string[]): Promise<{
    success: string[];
    failed: Array<{ type: string; error: string }>;
  }> {
    const success: string[] = [];
    const failed: Array<{ type: string; error: string }> = [];

    for (const dictType of dictTypes) {
      try {
        const result = await this.getOptions(dictType, {
          useCache: true,
          forceRefresh: true,
          useFallback: false
        });

        if (result.success) {
          success.push(dictType);
        } else {
          failed.push({ type: dictType, error: result.error ?? 'Unknown error' });
        }
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        failed.push({ type: dictType, error: enhancedError.message });
      }
    }

    return { success, failed };
  }

  /**
   * 工具方法：数组分块
   */
  private chunkArray<T>(array: T[], chunkSize: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
  }

  /**
   * 验证字典数据完整性
   */
  validateDictionaryData(dictType: string): {
    isValid: boolean;
    issues: string[];
    suggestions: string[];
  } {
    const config = getDictionaryConfig(dictType);
    const cached = cache.get(dictType);

    if (!config) {
      return {
        isValid: false,
        issues: [`字典类型不存在: ${dictType}`],
        suggestions: ['检查字典类型是否正确配置']
      };
    }

    const issues: string[] = [];
    const suggestions: string[] = [];

    if (!cached || cached.length === 0) {
      issues.push('字典数据为空');
      suggestions.push('尝试从API重新加载数据或使用备用数据');
    } else {
      // 检查数据结构
      const invalidItems = cached.filter(item =>
        !item.value || !item.label || typeof item.value !== 'string' || typeof item.label !== 'string'
      );

      if (invalidItems.length > 0) {
        issues.push(`发现${invalidItems.length}个无效的字典项`);
        suggestions.push('检查字典项的value和label字段');
      }

      // 检查重复值
      const values = cached.map(item => item.value);
      const duplicates = values.filter((value, index) => values.indexOf(value) !== index);

      if (duplicates.length > 0) {
        issues.push(`发现重复的字典值: ${[...new Set(duplicates)].join(', ')}`);
        suggestions.push('清理重复的字典项或使用不同的值');
      }

      // 检查必需字段
      if (config.requiredFields) {
        const missingFields = config.requiredFields.filter(field =>
          cached.some(item => !(field in item))
        );

        if (missingFields.length > 0) {
          issues.push(`缺少必需字段: ${missingFields.join(', ')}`);
          suggestions.push('确保所有字典项都包含必需字段');
        }
      }
    }

    return {
      isValid: issues.length === 0,
      issues,
      suggestions
    };
  }
}

// 创建单例实例
export const baseDictionaryService = new BaseDictionaryService();

// 为了向后兼容，导出默认实例
export default baseDictionaryService;