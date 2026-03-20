/**
 * 基础字典服务 - 类型定义与缓存管理
 *
 * @description 从 base.ts 拆分出的类型定义和缓存管理模块
 */

import { DictionaryOption } from './config';

// ============================================================================
// 导出的接口定义
// ============================================================================

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

// ============================================================================
// 内部接口定义
// ============================================================================

// 字典缓存项接口
export interface CacheItem {
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

// ============================================================================
// 缓存管理
// ============================================================================

/**
 * 增强的字典缓存管理
 */
export class DictionaryCache {
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
        ...metadata,
      },
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
      const sortedItems = Array.from(this.cache.entries()).sort(([, a], [, b]) => {
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
      totalMisses: this.missCount,
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
      isExpired: now - item.timestamp > this.CACHE_TTL,
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

/** 字典缓存单例 */
export const dictionaryCache = new DictionaryCache();
