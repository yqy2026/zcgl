/**
 * 路由缓存管理器
 * 提供智能的路由级缓存策略
 */

import { useCallback } from 'react'

interface CacheConfig {
  maxSize: number
  defaultTTL: number
  enableCompression: boolean
  enablePersistence: boolean
  storageQuota: number // 字节
}

interface CacheEntry<T> {
  data: T
  timestamp: number
  ttl: number
  accessCount: number
  lastAccessed: number
  compressed?: boolean
  size: number
}

interface CacheStats {
  hits: number
  misses: number
  size: number
  memoryUsage: number
  evictionCount: number
  compressionRatio: number
}

class RouteCacheManager {
  private cache: Map<string, CacheEntry<any>>
  private config: CacheConfig
  private stats: CacheStats
  private storageKey = 'route_cache_v2'
  private compressionWorker: Worker | null = null

  constructor(config: Partial<CacheConfig> = {}) {
    this.config = {
      maxSize: 50,
      defaultTTL: 5 * 60 * 1000, // 5分钟
      enableCompression: true,
      enablePersistence: true,
      storageQuota: 10 * 1024 * 1024, // 10MB
      ...config
    }

    this.cache = new Map()
    this.stats = {
      hits: 0,
      misses: 0,
      size: 0,
      memoryUsage: 0,
      evictionCount: 0,
      compressionRatio: 1
    }

    this.initializeCompression()
    this.loadFromPersistence()
  }

  private initializeCompression() {
    if (this.config.enableCompression && typeof Worker !== 'undefined') {
      try {
        // 创建压缩Worker（简化版本）
        this.compressionWorker = new Worker('/workers/compression.js')
        this.compressionWorker.onerror = () => {
          console.warn('压缩Worker初始化失败，禁用压缩')
          this.config.enableCompression = false
        }
      } catch (error) {
        console.warn('Worker不可用，禁用压缩')
        this.config.enableCompression = false
      }
    }
  }

  private calculateSize(data: any): number {
    // 简单计算对象大小
    return JSON.stringify(data).length * 2 // 假设每个字符2字节
  }

  private async compress(data: string): Promise<{ compressed: string; ratio: number }> {
    if (!this.config.enableCompression) {
      return { compressed: data, ratio: 1 }
    }

    try {
      // 使用CompressionStream API（如果可用）
      if ('CompressionStream' in window) {
        const stream = new CompressionStream('gzip')
        const writer = stream.writable.getWriter()
        const reader = stream.readable.getReader()

        writer.write(new TextEncoder().encode(data))
        writer.close()

        const chunks: Uint8Array[] = []
        let done = false

        while (!done) {
          const { value, done: readerDone } = await reader.read()
          done = readerDone
          if (value) chunks.push(value)
        }

        const compressed = new Uint8Array(chunks.reduce((acc, chunk) => acc + chunk.length, 0))
        let offset = 0
        for (const chunk of chunks) {
          compressed.set(chunk, offset)
          offset += chunk.length
        }

        const compressedStr = btoa(String.fromCharCode(...compressed))
        const ratio = compressedStr.length / data.length

        return { compressed: compressedStr, ratio }
      }
    } catch (error) {
      console.warn('压缩失败，使用原始数据', error)
    }

    return { compressed: data, ratio: 1 }
  }

  private async decompress(compressed: string): Promise<string> {
    try {
      if (compressed.length > 0 && this.config.enableCompression) {
        // 尝试解压
        const binaryString = atob(compressed)
        const bytes = new Uint8Array(binaryString.length)
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i)
        }

        if ('DecompressionStream' in window) {
          const stream = new DecompressionStream('gzip')
          const writer = stream.writable.getWriter()
          const reader = stream.readable.getReader()

          writer.write(bytes)
          writer.close()

          const chunks: Uint8Array[] = []
          let done = false

          while (!done) {
            const { value, done: readerDone } = await reader.read()
            done = readerDone
            if (value) chunks.push(value)
          }

          const decompressed = new Uint8Array(chunks.reduce((acc, chunk) => acc + chunk.length, 0))
          let offset = 0
          for (const chunk of chunks) {
            decompressed.set(chunk, offset)
            offset += chunk.length
          }

          return new TextDecoder().decode(decompressed)
        }
      }
    } catch (error) {
      console.warn('解压失败，返回原始数据', error)
    }

    return compressed
  }

  private async persistCache() {
    if (!this.config.enablePersistence) return

    try {
      const entries = Array.from(this.cache.entries())
      const serializable = entries.map(([key, entry]) => ({
        key,
        data: entry.data,
        timestamp: entry.timestamp,
        ttl: entry.ttl,
        accessCount: entry.accessCount,
        lastAccessed: entry.lastAccessed,
        compressed: entry.compressed || false
      }))

      const serialized = JSON.stringify(serializable)

      // 检查存储配额
      if (serialized.length > this.config.storageQuota) {
        console.warn('缓存数据超过存储配额，跳过持久化')
        return
      }

      localStorage.setItem(this.storageKey, serialized)
    } catch (error) {
      console.warn('缓存持久化失败', error)
    }
  }

  private loadFromPersistence() {
    if (!this.config.enablePersistence) return

    try {
      const serialized = localStorage.getItem(this.storageKey)
      if (!serialized) return

      const entries = JSON.parse(serialized)
      const now = Date.now()

      for (const entry of entries) {
        // 检查是否过期
        if (now - entry.timestamp > entry.ttl) {
          continue
        }

        // 检查内存限制
        if (this.cache.size >= this.config.maxSize) {
          break
        }

        this.cache.set(entry.key, {
          ...entry,
          size: this.calculateSize(entry.data)
        })
      }

      console.log(`从持久化存储加载了 ${this.cache.size} 个缓存项`)
    } catch (error) {
      console.warn('加载持久化缓存失败', error)
    }
  }

  private evictLRU() {
    // 找到最少使用的项
    let lruKey: string | null = null
    let lruTime = Date.now()

    for (const [key, entry] of this.cache.entries()) {
      if (entry.lastAccessed < lruTime) {
        lruTime = entry.lastAccessed
        lruKey = key
      }
    }

    if (lruKey) {
      this.cache.delete(lruKey)
      this.stats.evictionCount++
    }
  }

  private updateAccessInfo(_key: string, entry: CacheEntry<any>) {
    entry.accessCount++
    entry.lastAccessed = Date.now()
  }

  async set<T>(key: string, data: T, ttl?: number): Promise<void> {
    const actualTTL = ttl || this.config.defaultTTL
    const now = Date.now()

    // 检查缓存大小限制
    if (this.cache.size >= this.config.maxSize) {
      this.evictLRU()
    }

    let finalData = data
    let compressed = false
    let compressionRatio = 1
    const originalSize = this.calculateSize(data)

    // 尝试压缩
    if (this.config.enableCompression && originalSize > 1024) { // 只压缩大于1KB的数据
      try {
        const serialized = JSON.stringify(data)
        const { compressed: compressedData, ratio } = await this.compress(serialized)

        if (ratio < 0.8) { // 只有压缩率超过20%才使用压缩数据
          finalData = compressedData as T
          compressed = true
          compressionRatio = ratio
        }
      } catch (error) {
        console.warn('压缩失败，使用原始数据', error)
      }
    }

    const entry: CacheEntry<T> = {
      data: finalData,
      timestamp: now,
      ttl: actualTTL,
      accessCount: 1,
      lastAccessed: now,
      compressed,
      size: compressed ? originalSize * compressionRatio : originalSize
    }

    this.cache.set(key, entry)
    this.stats.size = this.cache.size
    this.stats.memoryUsage = Array.from(this.cache.values()).reduce((sum, entry) => sum + entry.size, 0)

    // 异步持久化
    this.persistCache()
  }

  async get<T>(key: string): Promise<T | null> {
    const entry = this.cache.get(key)

    if (!entry) {
      this.stats.misses++
      return null
    }

    const now = Date.now()

    // 检查是否过期
    if (now - entry.timestamp > entry.ttl) {
      this.cache.delete(key)
      this.stats.misses++
      return null
    }

    this.updateAccessInfo(key, entry)
    this.stats.hits++

    // 解压数据
    if (entry.compressed && typeof entry.data === 'string') {
      try {
        const decompressed = await this.decompress(entry.data)
        return JSON.parse(decompressed)
      } catch (error) {
        console.warn('解压失败，返回null', error)
        this.cache.delete(key)
        return null
      }
    }

    return entry.data
  }

  delete(key: string): boolean {
    const deleted = this.cache.delete(key)
    if (deleted) {
      this.stats.size = this.cache.size
      this.persistCache()
    }
    return deleted
  }

  clear(): void {
    this.cache.clear()
    this.stats.size = 0
    this.stats.memoryUsage = 0
    localStorage.removeItem(this.storageKey)
  }

  // 清理过期项
  cleanup(): number {
    const now = Date.now()
    let cleaned = 0

    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        this.cache.delete(key)
        cleaned++
      }
    }

    if (cleaned > 0) {
      this.stats.size = this.cache.size
      this.persistCache()
    }

    return cleaned
  }

  // 获取缓存统计
  getStats(): CacheStats {
    return { ...this.stats }
  }

  // 获取缓存信息
  getCacheInfo(): Array<{ key: string; size: number; ttl: number; accessCount: number; compressed: boolean }> {
    return Array.from(this.cache.entries()).map(([key, entry]) => ({
      key,
      size: entry.size,
      ttl: entry.ttl - (Date.now() - entry.timestamp),
      accessCount: entry.accessCount,
      compressed: entry.compressed || false
    }))
  }

  // 预热缓存
  async warmup(items: Array<{ key: string; data: any; ttl?: number }>): Promise<void> {
    const promises = items.map(item => this.set(item.key, item.data, item.ttl))
    await Promise.all(promises)
    console.log(`缓存预热完成，加载了 ${items.length} 个项`)
  }

  // 销毁
  destroy(): void {
    this.clear()
    if (this.compressionWorker) {
      this.compressionWorker.terminate()
    }
  }
}

// 全局缓存管理器实例
const globalCacheManager = new RouteCacheManager()

// 路由特定的缓存配置
export const ROUTE_CACHE_CONFIG = {
  '/dashboard': { ttl: 2 * 60 * 1000 },      // 2分钟
  '/assets/list': { ttl: 5 * 60 * 1000 },    // 5分钟
  '/assets/analytics': { ttl: 10 * 60 * 1000 }, // 10分钟
  '/rental/contracts': { ttl: 5 * 60 * 1000 }, // 5分钟
  '/system/users': { ttl: 10 * 60 * 1000 },   // 10分钟
}

// 缓存Hook
export const useRouteCache = () => {
  const cache = globalCacheManager

  const get = useCallback(<T>(key: string) => cache.get<T>(key), [cache])
  const set = useCallback(<T>(key: string, data: T, ttl?: number) => cache.set(key, data, ttl), [cache])
  const remove = useCallback((key: string) => cache.delete(key), [cache])
  const clear = useCallback(() => cache.clear(), [cache])
  const cleanup = useCallback(() => cache.cleanup(), [cache])
  const getStats = useCallback(() => cache.getStats(), [cache])
  const getCacheInfo = useCallback(() => cache.getCacheInfo(), [cache])

  return {
    get,
    set,
    remove,
    clear,
    cleanup,
    getStats,
    getCacheInfo,
    warmup: cache.warmup.bind(cache)
  }
}

// 缓存装饰器
export function cached(ttl?: number) {
  return function (target: any, propertyName: string, descriptor: PropertyDescriptor) {
    const method = descriptor.value

    descriptor.value = async function (...args: any[]) {
      const cacheKey = `${target.constructor.name}:${propertyName}:${JSON.stringify(args)}`

      // 尝试从缓存获取
      const cachedResult = await globalCacheManager.get(cacheKey)
      if (cachedResult !== null) {
        return cachedResult
      }

      // 执行原方法
      const result = await method.apply(this, args)

      // 缓存结果
      await globalCacheManager.set(cacheKey, result, ttl)

      return result
    }
  }
}

export default globalCacheManager