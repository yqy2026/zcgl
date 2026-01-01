/**
 * 数据缓存和性能优化工具
 */

interface CacheEntry<T> {
  data: T
  timestamp: number
  ttl: number // Time to live in milliseconds
}

interface CacheConfig {
  ttl?: number
  maxSize?: number
  enableCompression?: boolean
}

export class DataCache {
  private cache = new Map<string, CacheEntry<unknown>>()
  private config: Required<CacheConfig>

  constructor(config: CacheConfig = {}) {
    this.config = {
      ttl: config.ttl || 5 * 60 * 1000, // 5 minutes default
      maxSize: config.maxSize || 100,
      enableCompression: config.enableCompression || false
    }
  }

  private generateKey(key: string, params?: unknown): string {
    if (!params) return key
    return `${key}_${JSON.stringify(params)}`
  }

  private isExpired(entry: CacheEntry<unknown>): boolean {
    return Date.now() - entry.timestamp > entry.ttl
  }

  set<T>(key: string, data: T, customTTL?: number): void {
    const fullKey = this.generateKey(key)

    // 如果缓存已满，清理最旧的条目
    if (this.cache.size >= this.config.maxSize) {
      const oldestKey = this.cache.keys().next().value
      if (oldestKey) {
        this.cache.delete(oldestKey)
      }
    }

    this.cache.set(fullKey, {
      data,
      timestamp: Date.now(),
      ttl: customTTL || this.config.ttl
    })
  }

  get<T>(key: string, params?: unknown): T | null {
    const fullKey = this.generateKey(key, params)
    const entry = this.cache.get(fullKey)

    if (!entry) return null
    if (this.isExpired(entry)) {
      this.cache.delete(fullKey)
      return null
    }

    return entry.data as T
  }

  has(key: string, params?: unknown): boolean {
    const fullKey = this.generateKey(key, params)
    const entry = this.cache.get(fullKey)
    return entry ? !this.isExpired(entry) : false
  }

  delete(key: string, params?: unknown): boolean {
    const fullKey = this.generateKey(key, params)
    return this.cache.delete(fullKey)
  }

  clear(): void {
    this.cache.clear()
  }

  cleanup(): number {
    let deletedCount = 0

    for (const [key, entry] of this.cache.entries()) {
      if (this.isExpired(entry)) {
        this.cache.delete(key)
        deletedCount++
      }
    }

    return deletedCount
  }

  getStats() {
    return {
      size: this.cache.size,
      maxSize: this.config.maxSize,
      entries: Array.from(this.cache.entries()).map(([key, entry]) => ({
        key,
        age: Date.now() - entry.timestamp,
        ttl: entry.ttl,
        expired: this.isExpired(entry)
      }))
    }
  }
}

// 批量请求优化器
export class BatchRequestOptimizer {
  private pendingRequests = new Map<string, Promise<unknown>>()
  private batchDelay = 50 // milliseconds

  async batchRequest<T>(
    key: string,
    requestFn: () => Promise<T>,
    options: {
      batchKey?: string
      delay?: number
    } = {}
  ): Promise<T> {
    const { batchKey, delay = this.batchDelay } = options
    const requestKey = batchKey || key

    // 如果有相同的请求正在进行，返回相同的Promise
    if (this.pendingRequests.has(requestKey)) {
      return this.pendingRequests.get(requestKey)! as T
    }

    const promise = (async () => {
      try {
        // 添加小延迟以批量处理相同的请求
        await new Promise<void>((resolve) => setTimeout(resolve, delay))
        const result = await requestFn()
        return result
      } finally {
        this.pendingRequests.delete(requestKey)
      }
    })()

    this.pendingRequests.set(requestKey, promise)
    return promise
  }

  clear(): void {
    this.pendingRequests.clear()
  }
}

// 数据预加载器
export class DataPreloader {
  private preloadQueue: Array<() => Promise<unknown>> = []
  private isPreloading = false

  addToPreload(requestFn: () => Promise<unknown>): void {
    this.preloadQueue.push(requestFn)
  }

  async preload(priority: boolean = false): Promise<void> {
    if (this.isPreloading) return

    this.isPreloading = true

    try {
      if (priority) {
        // 高优先级：立即执行
        await Promise.all(this.preloadQueue.map(fn => fn()))
      } else {
        // 低优先级：空闲时执行
        if (typeof requestIdleCallback !== 'undefined') {
          requestIdleCallback(async () => {
            await Promise.all(this.preloadQueue.map(fn => fn()))
          })
        } else {
          // 降级方案
          setTimeout(async () => {
            await Promise.all(this.preloadQueue.map(fn => fn()))
          }, 1000)
        }
      }
    } catch {
      console.warn('Data preloading failed:', error)
    } finally {
      this.isPreloading = false
    }
  }

  clear(): void {
    this.preloadQueue = []
  }
}

// 创建全局实例
export const globalDataCache = new DataCache({
  ttl: 5 * 60 * 1000, // 5 minutes
  maxSize: 200
})

export const batchOptimizer = new BatchRequestOptimizer()

export const dataPreloader = new DataPreloader()

// 导出工具函数
export const createCachedRequest = <T>(
  cacheKey: string,
  requestFn: () => Promise<T>,
  cache: DataCache = globalDataCache,
  ttl?: number
) => {
  return async (params?: unknown): Promise<T> => {
    // 尝试从缓存获取
    const cached = cache.get<T>(cacheKey, params)
    if (cached) {
      return cached
    }

    // 执行请求
    const result = await batchOptimizer.batchRequest(
      cacheKey,
      requestFn,
      { batchKey: params ? `${cacheKey}_${JSON.stringify(params)}` : cacheKey }
    )

    // 缓存结果
    cache.set(cacheKey, result, ttl)
    return result
  }
}