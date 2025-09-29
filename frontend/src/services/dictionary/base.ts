/**
 * 基础字典服务
 * 提供核心的字典数据获取功能
 */

import { apiRequest } from '@/utils/request'
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

    console.log(`🔍 获取字典选项: ${dictType}`, { useCache, useFallback, isActive })

    // 检查字典类型是否存在
    const config = getDictionaryConfig(dictType)
    if (!config) {
      console.warn(`⚠️ 字典类型不存在: ${dictType}`)
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
        console.log(`✅ 从缓存获取字典数据 [${dictType}]: ${cached.length} 项`)
        return {
          success: true,
          data: cached,
          source: 'cache'
        }
      }
    }

    // 尝试从API获取
    try {
      console.log(`🌐 请求API: ${config.apiEndpoint}`)
      const response = await apiRequest.get(config.apiEndpoint, {
        params: { is_active: isActive },
        timeout: 5000
      })

      const data = response.data || []
      console.log(`✅ API响应成功 [${dictType}]: ${data.length} 项`)

      // 缓存数据
      if (useCache) {
        cache.set(dictType, data)
      }

      return {
        success: true,
        data,
        source: 'api'
      }
    } catch (error: any) {
      console.error(`❌ API请求失败 [${dictType}]:`, error)

      // 如果启用备用数据，返回备用数据
      if (useFallback) {
        const fallbackData = config.fallbackOptions || []
        console.log(`🔄 使用备用数据 [${dictType}]: ${fallbackData.length} 项`)

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
    console.log(`🔍 批量获取字典选项: ${dictTypes.join(', ')}`)

    const promises = dictTypes.map(async (dictType) => {
      const result = await this.getOptions(dictType, options)
      return [dictType, result]
    })

    const results = await Promise.all(promises)

    return results.reduce((acc, [dictType, result]) => {
      acc[dictType] = result
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
      console.log(`🧹 清除字典缓存: ${dictType}`)
    } else {
      cache.clear()
      console.log(`🧹 清除所有字典缓存`)
    }
  }

  /**
   * 预加载字典数据
   */
  async preload(dictTypes: string[]): Promise<void> {
    console.log(`🚀 预加载字典数据: ${dictTypes.join(', ')}`)
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
    const cachedTypes = Array.from(cache.cache.keys())
    return {
      cachedTypes,
      totalTypes: Object.keys(DICTIONARY_CONFIGS).length,
      cacheSize: cache.cache.size
    }
  }
}

// 创建单例实例
export const baseDictionaryService = new BaseDictionaryService()

// 为了向后兼容，导出默认实例
export default baseDictionaryService