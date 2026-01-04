/**
 * 路由缓存工具
 * 提供路由组件缓存、性能监控和内存管理功能
 */

import { createLogger } from './logger'

const routeLogger = createLogger('RouteCache')

// 缓存接口定义
export interface RouteCacheItem {
  component: React.ComponentType<any>
  loadTime: number
  hitCount: number
  lastAccess: number
  ttl?: number
}

export interface RouteCacheMetrics {
  hitRate: number
  size: number
  totalHits: number
  totalMisses: number
  memoryUsage: number
}

export interface RouteCache {
  get: (key: string) => RouteCacheItem | null
  set: (key: string, component: RouteCacheItem['component'], ttl?: number) => void
  clear: () => void
  delete: (key: string) => boolean
  getMetrics: () => RouteCacheMetrics
  cleanup: () => number
}

// 内存缓存实现
class MemoryRouteCache implements RouteCache {
  private cache = new Map<string, RouteCacheItem>()
  private hits = 0
  private misses = 0
  private readonly defaultTTL = 5 * 60 * 1000 // 5分钟

  get(key: string): RouteCacheItem | null {
    const item = this.cache.get(key)

    if (!item) {
      this.misses++
      return null
    }

    // 检查TTL
    if ((item.ttl !== null && item.ttl !== undefined) && Date.now() - item.lastAccess > item.ttl) {
      this.cache.delete(key)
      this.misses++
      return null
    }

    // 更新访问信息
    item.hitCount++
    item.lastAccess = Date.now()
    this.hits++

    return item
  }

  set(key: string, component: RouteCacheItem['component'], ttl?: number): void {
    const item: RouteCacheItem = {
      component,
      loadTime: Date.now(),
      hitCount: 0,
      lastAccess: Date.now(),
      ttl: (ttl !== null && ttl !== undefined) ? ttl : this.defaultTTL
    }

    this.cache.set(key, item)
  }

  clear(): void {
    this.cache.clear()
    this.hits = 0
    this.misses = 0
  }

  delete(key: string): boolean {
    return this.cache.delete(key)
  }

  getMetrics(): RouteCacheMetrics {
    const total = this.hits + this.misses
    const hitRate = total > 0 ? this.hits / total : 0

    // 估算内存使用（简单计算）
    let memoryUsage = 0
    for (const item of this.cache.values()) {
      memoryUsage += JSON.stringify(item.component).length * 2 // 粗略估算
    }

    return {
      hitRate,
      size: this.cache.size,
      totalHits: this.hits,
      totalMisses: this.misses,
      memoryUsage
    }
  }

  cleanup(): number {
    const now = Date.now()
    let cleaned = 0

    for (const [key, item] of this.cache.entries()) {
      if ((item.ttl !== null && item.ttl !== undefined) && now - item.lastAccess > item.ttl) {
        this.cache.delete(key)
        cleaned++
      }
    }

    return cleaned
  }
}

// 全局缓存实例
const routeCacheInstance = new MemoryRouteCache()

// 定期清理过期缓存
setInterval(() => {
  routeCacheInstance.cleanup()
}, 60000) // 每分钟清理一次

/**
 * 使用路由缓存的Hook
 * @returns 路由缓存实例
 */
export const useRouteCache = (): RouteCache => {
  return routeCacheInstance
}

/**
 * 路由缓存React Hook（用于组件中）
 * @returns 缓存操作方法和性能指标
 */
export const useRouteCacheState = () => {
  const cache = useRouteCache()

  const getMetrics = (): RouteCacheMetrics => {
    return cache.getMetrics()
  }

  const preloadRoute = async (key: string, loader: () => Promise<React.ComponentType<any>>) => {
    const cached = cache.get(key)
    if (cached) {
      return cached.component
    }

    try {
      const component = await loader()
      cache.set(key, component)
      return component
    } catch (error) {
      routeLogger.error(`Failed to preload route: ${key}`, error as Error)
      throw error
    }
  }

  return {
    cache,
    getMetrics,
    preloadRoute,
    clear: cache.clear.bind(cache),
    delete: cache.delete.bind(cache)
  }
}

/**
 * 路由性能监控工具
 */
export class RoutePerformanceMonitor {
  private metrics = new Map<string, {
    loadTime: number
    hitCount: number
    errorCount: number
    lastLoad: number
  }>()

  recordLoadTime(key: string, loadTime: number): void {
    const current = this.metrics.get(key) || {
      loadTime: 0,
      hitCount: 0,
      errorCount: 0,
      lastLoad: Date.now()
    }

    current.loadTime = (current.loadTime + loadTime) / 2 // 平均值
    current.hitCount++
    current.lastLoad = Date.now()

    this.metrics.set(key, current)
  }

  recordError(key: string): void {
    const current = this.metrics.get(key) || {
      loadTime: 0,
      hitCount: 0,
      errorCount: 0,
      lastLoad: Date.now()
    }

    current.errorCount++
    this.metrics.set(key, current)
  }

  getMetrics() {
    const result: Record<string, any> = {}

    for (const [key, value] of this.metrics.entries()) {
      result[key] = {
        averageLoadTime: value.loadTime,
        hitCount: value.hitCount,
        errorCount: value.errorCount,
        errorRate: value.hitCount > 0 ? value.errorCount / value.hitCount : 0,
        lastLoad: value.lastLoad
      }
    }

    return result
  }

  clear(): void {
    this.metrics.clear()
  }
}

// 全局性能监控实例
export const routePerformanceMonitor = new RoutePerformanceMonitor()

export default routeCacheInstance
