/**
 * 基础字典服务
 * 提供核心的字典数据获取功能
 */

import { apiClient } from '../api'
import {
  DictionaryConfig,
  DictionaryOption,
  DICTIONARY_CONFIGS,
  getDictionaryConfig
} from './config'

export interface DictionaryServiceResult {
  success: boolean
  data: DictionaryOption[]
  error?: string
  source: 'api' | 'fallback' | 'cache'
}

/**
 * 字典缓存管理
 */
class DictionaryCache {
  private cache = new Map<string, { data: DictionaryOption[]; timestamp: number }>()
  private readonly CACHE_TTL = 5 * 60 * 1000 // 5分钟缓存

  get(dictType: string): DictionaryOption[] | null {
    const cached = this.cache.get(dictType)
    if (!cached) return null

    if (Date.now() - cached.timestamp > this.CACHE_TTL) {
      this.cache.delete(dictType)
      return null
    }

    return cached.data
  }

  set(dictType: string, data: DictionaryOption[]): void {
    this.cache.set(dictType, {
      data,
      timestamp: Date.now()
    })
  }

  clear(): void {
    this.cache.clear()
  }

  clearForType(dictType: string): void {
    this.cache.delete(dictType)
  }

  getCacheInfo(): { keys: string[]; size: number } {
    return {
      keys: Array.from(this.cache.keys()),
      size: this.cache.size
    }
  }
}

const cache = new DictionaryCache()

class BaseDictionaryService {
  /**
   * 获取字典选项（核心方法）
   */
  async getOptions(
    dictType: string,
    options: {
      useCache?: boolean
      useFallback?: boolean
      isActive?: boolean
    } = {}
  ): Promise<DictionaryServiceResult> {
    const { useCache = true, useFallback = true, isActive = true } = options

    // 检查字典类型是否存在
    const config = getDictionaryConfig(dictType)
    if (!config) {
      return {
        success: false,
        data: [],
        error: `字典类型不存在: ${dictType}`,
        source: 'fallback'
      }
    }

    // 检查缓存
    if (useCache) {
      const cached = cache.get(dictType)
      if (cached) {
        return {
          success: true,
          data: cached,
          source: 'cache'
        }
      }
    }

    // 尝试从API获取
    try {
      const response = await apiClient.get(config.apiEndpoint, {
        params: { is_active: isActive },
        timeout: 5000
      })

      // apiClient 直接返回数据，不是包装的响应对象
      const data = Array.isArray(response) ? response : (response.data || [])

      // 缓存数据
      if (useCache) {
        cache.set(dictType, data)
      }

      return {
        success: true,
        data,
        source: 'api'
      }
    } catch (error: unknown) {
      // 如果启用备用数据，返回备用数据
      if (useFallback) {
        const fallbackData = config.fallbackOptions || []
        return {
          success: true,
          data: fallbackData,
          source: 'fallback'
        }
      }

      return {
        success: false,
        data: [],
        error: error.message || 'API请求失败',
        source: 'fallback'
      }
    }
  }

  /**
   * 批量获取字典选项
   */
  async getBatchOptions(
    dictTypes: string[],
    options: {
      useCache?: boolean
      useFallback?: boolean
      isActive?: boolean
    } = {}
  ): Promise<Record<string, DictionaryServiceResult>> {

    const promises = dictTypes.map(async (dictType) => {
      const result = await this.getOptions(dictType, options)
      return [dictType, result]
    })

    const results = await Promise.all(promises)

    return results.reduce((acc, [dictType, result]) => {
      acc[dictType as string] = result
      return acc
    }, {} as Record<string, DictionaryServiceResult>)
  }

  /**
   * 获取所有可用的字典类型
   */
  getAvailableTypes(): DictionaryConfig[] {
    return Object.values(DICTIONARY_CONFIGS)
  }

  /**
   * 检查字典类型是否可用
   */
  isTypeAvailable(dictType: string): boolean {
    return dictType in DICTIONARY_CONFIGS
  }

  /**
   * 清除缓存
   */
  clearCache(dictType?: string): void {
    if (dictType) {
      cache.clearForType(dictType)
    } else {
      cache.clear()
    }
  }

  /**
   * 预加载字典数据
   */
  async preload(dictTypes: string[]): Promise<void> {
    await this.getBatchOptions(dictTypes, { useCache: true, useFallback: false })
  }

  /**
   * 获取字典统计信息
   */
  getStats(): {
    cachedTypes: string[]
    totalTypes: number
    cacheSize: number
  } {
    const cacheInfo = cache.getCacheInfo()
    return {
      cachedTypes: cacheInfo.keys,
      totalTypes: Object.keys(DICTIONARY_CONFIGS).length,
      cacheSize: cacheInfo.size
    }
  }
}

// 创建单例实例
export const baseDictionaryService = new BaseDictionaryService()

// 为了向后兼容，导出默认实例
export default baseDictionaryService
