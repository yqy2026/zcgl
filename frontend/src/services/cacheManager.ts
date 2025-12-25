// API缓存管理器

import { CACHE } from '../api/config'

export interface CacheItem<T = unknown> {
  data: T
  timestamp: number
  ttl: number
  key: string
}

export interface CacheOptions {
  ttl?: number
  force?: boolean
  tags?: string[]
}

export class ApiCacheManager {
  private static instance: ApiCacheManager
  private cache = new Map<string, CacheItem>()
  private tagMap = new Map<string, Set<string>>()
  
  private constructor() {
    // 定期清理过期缓存
    setInterval(() => {
      this.cleanup()
    }, 60000) // 每分钟清理一次
  }
  
  static getInstance(): ApiCacheManager {
    if (!ApiCacheManager.instance) {
      ApiCacheManager.instance = new ApiCacheManager()
    }
    return ApiCacheManager.instance
  }
  
  // 生成缓存键
  private generateKey(url: string, params?: Record<string, unknown>): string {
    const paramStr = params ? JSON.stringify(params) : ''
    return `${url}:${paramStr}`
  }
  
  // 设置缓存
  set<T>(
    url: string,
    data: T,
    options: CacheOptions = {},
    params?: Record<string, unknown>
  ): void {
    const key = this.generateKey(url, params)
    const ttl = options.ttl || CACHE.DEFAULT_TTL
    
    const cacheItem: CacheItem<T> = {
      data,
      timestamp: Date.now(),
      ttl,
      key,
    }
    
    this.cache.set(key, cacheItem)
    
    // 处理标签
    if (options.tags) {
      options.tags.forEach(tag => {
        if (!this.tagMap.has(tag)) {
          this.tagMap.set(tag, new Set())
        }
        this.tagMap.get(tag)!.add(key)
      })
    }
  }
  
  // 获取缓存
  get<T>(url: string, params?: Record<string, unknown>): T | null {
    const key = this.generateKey(url, params)
    const cacheItem = this.cache.get(key)
    
    if (!cacheItem) {
      return null
    }
    
    // 检查是否过期
    if (this.isExpired(cacheItem)) {
      this.cache.delete(key)
      return null
    }
    
    return cacheItem.data as T
  }
  
  // 检查缓存是否存在且未过期
  has(url: string, params?: Record<string, unknown>): boolean {
    const key = this.generateKey(url, params)
    const cacheItem = this.cache.get(key)
    
    if (!cacheItem) {
      return false
    }
    
    if (this.isExpired(cacheItem)) {
      this.cache.delete(key)
      return false
    }
    
    return true
  }
  
  // 删除缓存
  delete(url: string, params?: Record<string, unknown>): boolean {
    const key = this.generateKey(url, params)
    return this.cache.delete(key)
  }
  
  // 根据标签删除缓存
  deleteByTag(tag: string): void {
    const keys = this.tagMap.get(tag)
    if (keys) {
      keys.forEach(key => {
        this.cache.delete(key)
      })
      this.tagMap.delete(tag)
    }
  }
  
  // 根据模式删除缓存
  deleteByPattern(pattern: RegExp): void {
    const keysToDelete: string[] = []
    
    this.cache.forEach((_, key) => {
      if (pattern.test(key)) {
        keysToDelete.push(key)
      }
    })
    
    keysToDelete.forEach(key => {
      this.cache.delete(key)
    })
  }
  
  // 清空所有缓存
  clear(): void {
    this.cache.clear()
    this.tagMap.clear()
  }
  
  // 检查缓存项是否过期
  private isExpired(cacheItem: CacheItem): boolean {
    return Date.now() - cacheItem.timestamp > cacheItem.ttl
  }
  
  // 清理过期缓存
  private cleanup(): void {
    const expiredKeys: string[] = []
    
    this.cache.forEach((cacheItem, key) => {
      if (this.isExpired(cacheItem)) {
        expiredKeys.push(key)
      }
    })
    
    expiredKeys.forEach(key => {
      this.cache.delete(key)
    })
    
    // 清理标签映射中的过期键
    this.tagMap.forEach((keys, tag) => {
      expiredKeys.forEach(expiredKey => {
        keys.delete(expiredKey)
      })
      
      // 如果标签下没有键了，删除标签
      if (keys.size === 0) {
        this.tagMap.delete(tag)
      }
    })
  }
  
  // 获取缓存统计信息
  getStats(): {
    totalItems: number
    totalSize: number
    hitRate: number
    tags: number
  } {
    let totalSize = 0
    this.cache.forEach(item => {
      totalSize += JSON.stringify(item.data).length
    })
    
    return {
      totalItems: this.cache.size,
      totalSize,
      hitRate: 0, // 需要实现命中率统计
      tags: this.tagMap.size,
    }
  }
  
  // 预热缓存
  async warmup(urls: Array<{ url: string; params?: Record<string, unknown> }>): Promise<void> {
    // 这里可以实现缓存预热逻辑
    // Cache warmup
  }
}

// 导出单例实例
export const cacheManager = ApiCacheManager.getInstance()

// 缓存装饰器
export function cached(options: CacheOptions = {}) {
  return function (target: unknown, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value

    descriptor.value = async function (...args: unknown[]) {
      const cacheKey = `${(target as any).constructor.name}.${propertyKey}`
      const params = args.length > 0 ? args[0] : undefined

      // 如果强制刷新或没有缓存，执行原方法
      if (options.force || !cacheManager.has(cacheKey, params as any)) {
        const result = await originalMethod.apply(this, args)
        cacheManager.set(cacheKey, result, options, params as any)
        return result
      }

      // 返回缓存结果
      return cacheManager.get(cacheKey, params as any)
    }

    return descriptor
  }
}

// 缓存失效装饰器
export function invalidateCache(tags: string[]) {
  return function (target: unknown, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value
    
    descriptor.value = async function (...args: unknown[]) {
      const result = await originalMethod.apply(this, args)
      
      // 执行成功后失效相关缓存
      tags.forEach(tag => {
        cacheManager.deleteByTag(tag)
      })
      
      return result
    }
    
    return descriptor
  }
}