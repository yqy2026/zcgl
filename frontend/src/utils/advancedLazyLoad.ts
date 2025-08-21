/**
 * 高级懒加载管理器
 * 提供智能预加载、缓存管理和性能监控
 */

import { lazy, ComponentType, ReactElement } from 'react'
import { SkeletonLoader } from '@/components/Loading'

// 懒加载配置接口
interface LazyLoadConfig {
  fallback?: ComponentType
  delay?: number
  timeout?: number
  retries?: number
  preload?: boolean
  priority?: 'high' | 'medium' | 'low'
  cacheKey?: string
}

// 组件缓存
const componentCache = new Map<string, ComponentType<any>>()
const loadingPromises = new Map<string, Promise<any>>()

// 性能监控
interface LoadMetrics {
  startTime: number
  endTime?: number
  duration?: number
  success: boolean
  error?: string
  retryCount: number
}

const loadMetrics = new Map<string, LoadMetrics>()

// 预加载队列管理
class PreloadQueue {
  private queue: Array<{ importFunc: () => Promise<any>; priority: number }> = []
  private isProcessing = false
  private maxConcurrent = 3
  private currentLoading = 0

  add(importFunc: () => Promise<any>, priority: 'high' | 'medium' | 'low' = 'medium') {
    const priorityMap = { high: 3, medium: 2, low: 1 }
    this.queue.push({ importFunc, priority: priorityMap[priority] })
    this.queue.sort((a, b) => b.priority - a.priority)
    this.process()
  }

  private async process() {
    if (this.isProcessing || this.currentLoading >= this.maxConcurrent) {
      return
    }

    this.isProcessing = true

    while (this.queue.length > 0 && this.currentLoading < this.maxConcurrent) {
      const item = this.queue.shift()
      if (item) {
        this.currentLoading++
        this.loadWithIdle(item.importFunc).finally(() => {
          this.currentLoading--
          this.process()
        })
      }
    }

    this.isProcessing = false
  }

  private loadWithIdle(importFunc: () => Promise<any>): Promise<any> {
    return new Promise((resolve, reject) => {
      const load = () => {
        importFunc()
          .then(resolve)
          .catch(reject)
      }

      // 使用requestIdleCallback在空闲时加载
      if ('requestIdleCallback' in window) {
        requestIdleCallback(load, { timeout: 5000 })
      } else {
        setTimeout(load, 100)
      }
    })
  }
}

const preloadQueue = new PreloadQueue()

// 高级懒加载组件创建器
export const createAdvancedLazyComponent = <T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  config: LazyLoadConfig = {}
): T => {
  const {
    fallback = () => <SkeletonLoader type="list" loading={true} />,
    delay = 200,
    timeout = 15000,
    retries = 3,
    preload = false,
    priority = 'medium',
    cacheKey,
  } = config

  const key = cacheKey || importFunc.toString()

  // 如果已缓存，直接返回
  if (componentCache.has(key)) {
    return componentCache.get(key)!
  }

  // 创建带重试的导入函数
  const importWithRetry = async (attempt = 1): Promise<{ default: T }> => {
    const startTime = performance.now()
    
    if (!loadMetrics.has(key)) {
      loadMetrics.set(key, {
        startTime,
        success: false,
        retryCount: 0
      })
    }

    try {
      // 检查是否已有正在进行的加载
      if (loadingPromises.has(key)) {
        return await loadingPromises.get(key)!
      }

      // 创建加载Promise
      const loadPromise = Promise.race([
        // 添加延迟避免闪烁
        new Promise<{ default: T }>((resolve) => {
          setTimeout(async () => {
            try {
              const module = await importFunc()
              resolve(module)
            } catch (error) {
              throw error
            }
          }, delay)
        }),
        // 超时处理
        new Promise<never>((_, reject) => {
          setTimeout(() => {
            reject(new Error(`Component load timeout after ${timeout}ms`))
          }, timeout)
        }),
      ])

      loadingPromises.set(key, loadPromise)
      const result = await loadPromise

      // 更新性能指标
      const metrics = loadMetrics.get(key)!
      metrics.endTime = performance.now()
      metrics.duration = metrics.endTime - metrics.startTime
      metrics.success = true

      // 缓存组件
      componentCache.set(key, result.default)
      loadingPromises.delete(key)

      return result

    } catch (error) {
      loadingPromises.delete(key)
      
      // 更新错误指标
      const metrics = loadMetrics.get(key)!
      metrics.retryCount = attempt
      metrics.error = error instanceof Error ? error.message : String(error)

      // 重试逻辑
      if (attempt < retries) {
        console.warn(`Component load failed (attempt ${attempt}/${retries}):`, error)
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000))
        return importWithRetry(attempt + 1)
      }

      metrics.success = false
      console.error(`Component load failed after ${retries} attempts:`, error)
      throw error
    }
  }

  // 如果需要预加载
  if (preload) {
    preloadQueue.add(importFunc, priority)
  }

  return lazy(importWithRetry) as T
}

// 智能预加载管理器
export class SmartPreloader {
  private static instance: SmartPreloader
  private preloadedComponents = new Set<string>()
  private userBehaviorData = {
    visitedRoutes: new Set<string>(),
    commonTransitions: new Map<string, Map<string, number>>(),
    timeSpentOnRoutes: new Map<string, number>(),
  }

  static getInstance(): SmartPreloader {
    if (!SmartPreloader.instance) {
      SmartPreloader.instance = new SmartPreloader()
    }
    return SmartPreloader.instance
  }

  // 记录用户行为
  recordRouteVisit(route: string, timeSpent?: number) {
    this.userBehaviorData.visitedRoutes.add(route)
    if (timeSpent) {
      this.userBehaviorData.timeSpentOnRoutes.set(route, timeSpent)
    }
  }

  recordRouteTransition(from: string, to: string) {
    if (!this.userBehaviorData.commonTransitions.has(from)) {
      this.userBehaviorData.commonTransitions.set(from, new Map())
    }
    const transitions = this.userBehaviorData.commonTransitions.get(from)!
    transitions.set(to, (transitions.get(to) || 0) + 1)
  }

  // 基于用户行为预测并预加载
  predictAndPreload(currentRoute: string) {
    const transitions = this.userBehaviorData.commonTransitions.get(currentRoute)
    if (!transitions) return

    // 获取最可能的下一个路由
    const sortedTransitions = Array.from(transitions.entries())
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3) // 预加载前3个最可能的路由

    sortedTransitions.forEach(([route, count]) => {
      if (count > 2) { // 只预加载访问过2次以上的路由
        this.preloadRouteComponents(route)
      }
    })
  }

  // 预加载路由组件
  private preloadRouteComponents(route: string) {
    const routeComponentMap: Record<string, () => Promise<any>> = {
      '/dashboard': () => import('@/pages/Dashboard/DashboardPage'),
      '/assets/list': () => import('@/pages/Assets/AssetListPage'),
      '/assets/new': () => import('@/pages/Assets/AssetCreatePage'),
      '/assets/import': () => import('@/pages/Assets/AssetImportPage'),
      '/assets/analytics': () => import('@/pages/Assets/AssetAnalyticsPage'),
    }

    const importFunc = routeComponentMap[route]
    if (importFunc && !this.preloadedComponents.has(route)) {
      this.preloadedComponents.add(route)
      preloadQueue.add(importFunc, 'medium')
    }
  }

  // 基于网络状态调整预加载策略
  adjustPreloadStrategy() {
    if ('connection' in navigator) {
      const connection = (navigator as any).connection
      if (connection) {
        const { effectiveType, saveData } = connection
        
        // 在慢网络或省流量模式下减少预加载
        if (effectiveType === 'slow-2g' || effectiveType === '2g' || saveData) {
          preloadQueue['maxConcurrent'] = 1
        } else if (effectiveType === '3g') {
          preloadQueue['maxConcurrent'] = 2
        } else {
          preloadQueue['maxConcurrent'] = 3
        }
      }
    }
  }

  // 获取性能报告
  getPerformanceReport() {
    const report = {
      totalComponents: loadMetrics.size,
      successfulLoads: 0,
      failedLoads: 0,
      averageLoadTime: 0,
      slowestComponent: '',
      fastestComponent: '',
      totalRetries: 0,
    }

    let totalLoadTime = 0
    let slowestTime = 0
    let fastestTime = Infinity

    loadMetrics.forEach((metrics, key) => {
      if (metrics.success) {
        report.successfulLoads++
        if (metrics.duration) {
          totalLoadTime += metrics.duration
          if (metrics.duration > slowestTime) {
            slowestTime = metrics.duration
            report.slowestComponent = key
          }
          if (metrics.duration < fastestTime) {
            fastestTime = metrics.duration
            report.fastestComponent = key
          }
        }
      } else {
        report.failedLoads++
      }
      report.totalRetries += metrics.retryCount
    })

    report.averageLoadTime = report.successfulLoads > 0 ? totalLoadTime / report.successfulLoads : 0

    return report
  }
}

// 导出预配置的懒加载组件
export const LazyDashboardPage = createAdvancedLazyComponent(
  () => import('@/pages/Dashboard/DashboardPage'),
  {
    fallback: () => <SkeletonLoader type="chart" loading={true} />,
    priority: 'high',
    preload: true,
    cacheKey: 'dashboard-page'
  }
)

export const LazyAssetListPage = createAdvancedLazyComponent(
  () => import('@/pages/Assets/AssetListPage'),
  {
    fallback: () => <SkeletonLoader type="table" loading={true} />,
    priority: 'high',
    preload: true,
    cacheKey: 'asset-list-page'
  }
)

export const LazyAssetDetailPage = createAdvancedLazyComponent(
  () => import('@/pages/Assets/AssetDetailPage'),
  {
    fallback: () => <SkeletonLoader type="detail" loading={true} />,
    priority: 'medium',
    cacheKey: 'asset-detail-page'
  }
)

export const LazyAssetCreatePage = createAdvancedLazyComponent(
  () => import('@/pages/Assets/AssetCreatePage'),
  {
    fallback: () => <SkeletonLoader type="form" loading={true} />,
    priority: 'medium',
    cacheKey: 'asset-create-page'
  }
)

export const LazyAssetImportPage = createAdvancedLazyComponent(
  () => import('@/pages/Assets/AssetImportPage'),
  {
    fallback: () => <SkeletonLoader type="form" loading={true} />,
    priority: 'low',
    cacheKey: 'asset-import-page'
  }
)

export const LazyAssetAnalyticsPage = createAdvancedLazyComponent(
  () => import('@/pages/Assets/AssetAnalyticsPage'),
  {
    fallback: () => <SkeletonLoader type="chart" loading={true} />,
    priority: 'low',
    cacheKey: 'asset-analytics-page'
  }
)

// 组件级懒加载
export const LazyAssetChart = createAdvancedLazyComponent(
  () => import('@/components/Charts/AssetDistributionChart'),
  {
    priority: 'low',
    cacheKey: 'asset-chart'
  }
)

export const LazyOccupancyChart = createAdvancedLazyComponent(
  () => import('@/components/Charts/OccupancyRateChart'),
  {
    priority: 'low',
    cacheKey: 'occupancy-chart'
  }
)

// 工具函数
export const preloadCriticalComponents = () => {
  const preloader = SmartPreloader.getInstance()
  preloader.adjustPreloadStrategy()
  
  // 预加载关键组件
  preloadQueue.add(() => import('@/pages/Dashboard/DashboardPage'), 'high')
  preloadQueue.add(() => import('@/pages/Assets/AssetListPage'), 'high')
}

export const getComponentLoadMetrics = () => {
  return SmartPreloader.getInstance().getPerformanceReport()
}

export default {
  createAdvancedLazyComponent,
  SmartPreloader,
  preloadCriticalComponents,
  getComponentLoadMetrics,
}