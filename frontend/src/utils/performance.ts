/**
 * 前端性能优化工具
 */

import { lazy, ComponentType } from 'react'

// 性能监控配置
export interface PerformanceConfig {
  enableMetrics: boolean
  enableResourceTiming: boolean
  enableUserTiming: boolean
  enableLongTaskMonitoring: boolean
  thresholds: {
    fcp: number // First Contentful Paint
    lcp: number // Largest Contentful Paint
    fid: number // First Input Delay
    cls: number // Cumulative Layout Shift
  }
}

export const defaultPerformanceConfig: PerformanceConfig = {
  enableMetrics: true,
  enableResourceTiming: true,
  enableUserTiming: true,
  enableLongTaskMonitoring: true,
  thresholds: {
    fcp: 1800, // 1.8s
    lcp: 2500, // 2.5s
    fid: 100,  // 100ms
    cls: 0.1,  // 0.1
  }
}

// 懒加载组件工厂
export function createLazyComponent<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  chunkName?: string
) {
  return lazy(() => {
    // 添加性能标记
    if (chunkName && performance.mark) {
      performance.mark(`lazy-load-start-${chunkName}`)
    }

    return importFn().then(module => {
      if (chunkName && performance.mark && performance.measure) {
        performance.mark(`lazy-load-end-${chunkName}`)
        performance.measure(
          `lazy-load-${chunkName}`,
          `lazy-load-start-${chunkName}`,
          `lazy-load-end-${chunkName}`
        )
      }
      return module
    })
  })
}

// 预加载管理器
class PreloadManager {
  private preloadedModules = new Set<string>()
  private preloadPromises = new Map<string, Promise<any>>()

  preload<T>(
    importFn: () => Promise<T>,
    key: string,
    priority: 'high' | 'low' = 'low'
  ): Promise<T> {
    if (this.preloadPromises.has(key)) {
      return this.preloadPromises.get(key)!
    }

    const promise = this.schedulePreload(importFn, priority)
    this.preloadPromises.set(key, promise)

    promise.then(() => {
      this.preloadedModules.add(key)
    }).catch(error => {
      console.warn(`Failed to preload module ${key}:`, error)
      this.preloadPromises.delete(key)
    })

    return promise
  }

  private schedulePreload<T>(
    importFn: () => Promise<T>,
    priority: 'high' | 'low'
  ): Promise<T> {
    if (priority === 'high') {
      return importFn()
    }

    // 低优先级预加载：等待空闲时间
    return new Promise((resolve, reject) => {
      const load = () => {
        importFn().then(resolve).catch(reject)
      }

      if ('requestIdleCallback' in window) {
        requestIdleCallback(load, { timeout: 5000 })
      } else {
        setTimeout(load, 0)
      }
    })
  }

  isPreloaded(key: string): boolean {
    return this.preloadedModules.has(key)
  }

  getPreloadedModules(): string[] {
    return Array.from(this.preloadedModules)
  }
}

export const preloadManager = new PreloadManager()

// 性能监控类
class PerformanceMonitor {
  private config: PerformanceConfig
  private observer?: PerformanceObserver
  private metrics: Map<string, number> = new Map()

  constructor(config: PerformanceConfig = defaultPerformanceConfig) {
    this.config = config
    this.init()
  }

  private init() {
    if (!this.config.enableMetrics || typeof window === 'undefined') {
      return
    }

    // 监控Web Vitals
    this.observeWebVitals()

    // 监控资源加载
    if (this.config.enableResourceTiming) {
      this.observeResourceTiming()
    }

    // 监控长任务
    if (this.config.enableLongTaskMonitoring) {
      this.observeLongTasks()
    }

    // 监控用户自定义指标
    if (this.config.enableUserTiming) {
      this.observeUserTiming()
    }
  }

  private observeWebVitals() {
    // First Contentful Paint
    this.observeMetric('first-contentful-paint', (entry) => {
      const fcp = entry.startTime
      this.metrics.set('fcp', fcp)
      
      if (fcp > this.config.thresholds.fcp) {
        console.warn(`FCP is slow: ${fcp}ms (threshold: ${this.config.thresholds.fcp}ms)`)
      }
    })

    // Largest Contentful Paint
    this.observeMetric('largest-contentful-paint', (entry) => {
      const lcp = entry.startTime
      this.metrics.set('lcp', lcp)
      
      if (lcp > this.config.thresholds.lcp) {
        console.warn(`LCP is slow: ${lcp}ms (threshold: ${this.config.thresholds.lcp}ms)`)
      }
    })

    // First Input Delay
    this.observeMetric('first-input', (entry) => {
      const fid = (entry as any).processingStart - entry.startTime
      this.metrics.set('fid', fid)

      if (fid > this.config.thresholds.fid) {
        console.warn(`FID is slow: ${fid}ms (threshold: ${this.config.thresholds.fid}ms)`)
      }
    })

    // Cumulative Layout Shift
    this.observeMetric('layout-shift', (entry) => {
      if (!(entry as any).hadRecentInput) {
        const currentCLS = this.metrics.get('cls') || 0
        const newCLS = currentCLS + (entry as any).value
        this.metrics.set('cls', newCLS)

        if (newCLS > this.config.thresholds.cls) {
          console.warn(`CLS is high: ${newCLS} (threshold: ${this.config.thresholds.cls})`)
        }
      }
    })
  }

  private observeResourceTiming() {
    this.observeMetric('resource', (entry) => {
      const duration = (entry as any).responseEnd - entry.startTime

      // 记录慢资源
      if (duration > 1000) { // 超过1秒
        console.warn(`Slow resource: ${entry.name} took ${duration}ms`)
      }

      // 按资源类型分类
      const resourceType = this.getResourceType(entry.name)
      const typeMetrics = this.metrics.get(`resource-${resourceType}`) || 0
      this.metrics.set(`resource-${resourceType}`, typeMetrics + duration)
    })
  }

  private observeLongTasks() {
    this.observeMetric('longtask', (entry) => {
      const duration = entry.duration
      console.warn(`Long task detected: ${duration}ms`)
      
      const longTasks = this.metrics.get('long-tasks') || 0
      this.metrics.set('long-tasks', longTasks + 1)
    })
  }

  private observeUserTiming() {
    this.observeMetric('measure', (entry) => {
      this.metrics.set(`user-timing-${entry.name}`, entry.duration)
      
      // 记录慢操作
      if (entry.duration > 100) {
        console.warn(`Slow operation: ${entry.name} took ${entry.duration}ms`)
      }
    })
  }

  private observeMetric(
    entryType: string,
    callback: (entry: PerformanceEntry) => void
  ) {
    if (!('PerformanceObserver' in window)) {
      return
    }

    try {
      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach(callback)
      })

      observer.observe({ entryTypes: [entryType] })
    } catch (error) {
      console.warn(`Failed to observe ${entryType}:`, error)
    }
  }

  private getResourceType(url: string): string {
    if (url.includes('.js')) return 'script'
    if (url.includes('.css')) return 'style'
    if (url.match(/\.(png|jpg|jpeg|gif|svg|webp)$/)) return 'image'
    if (url.includes('/api/')) return 'api'
    return 'other'
  }

  // 手动记录性能指标
  mark(name: string) {
    if (performance.mark) {
      performance.mark(name)
    }
  }

  measure(name: string, startMark: string, endMark?: string) {
    if (performance.measure) {
      performance.measure(name, startMark, endMark)
    }
  }

  // 获取性能指标
  getMetrics(): Record<string, number> {
    return Object.fromEntries(this.metrics)
  }

  // 获取性能报告
  getPerformanceReport(): {
    metrics: Record<string, number>
    navigation: PerformanceNavigationTiming | null
    resources: PerformanceResourceTiming[]
    memory?: any
  } {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[]
    const memory = (performance as any).memory

    return {
      metrics: this.getMetrics(),
      navigation,
      resources: resources.slice(-20), // 最近20个资源
      memory: memory ? {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit,
      } : undefined,
    }
  }

  // 清理
  disconnect() {
    if (this.observer) {
      this.observer.disconnect()
    }
  }
}

export const performanceMonitor = new PerformanceMonitor()

// 资源预加载工具
export class ResourcePreloader {
  private static instance: ResourcePreloader
  private preloadedResources = new Set<string>()

  static getInstance(): ResourcePreloader {
    if (!ResourcePreloader.instance) {
      ResourcePreloader.instance = new ResourcePreloader()
    }
    return ResourcePreloader.instance
  }

  preloadImage(src: string): Promise<void> {
    if (this.preloadedResources.has(src)) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => {
        this.preloadedResources.add(src)
        resolve()
      }
      img.onerror = reject
      img.src = src
    })
  }

  preloadScript(src: string): Promise<void> {
    if (this.preloadedResources.has(src)) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const link = document.createElement('link')
      link.rel = 'preload'
      link.as = 'script'
      link.href = src
      link.onload = () => {
        this.preloadedResources.add(src)
        resolve()
      }
      link.onerror = reject
      document.head.appendChild(link)
    })
  }

  preloadStyle(href: string): Promise<void> {
    if (this.preloadedResources.has(href)) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const link = document.createElement('link')
      link.rel = 'preload'
      link.as = 'style'
      link.href = href
      link.onload = () => {
        this.preloadedResources.add(href)
        resolve()
      }
      link.onerror = reject
      document.head.appendChild(link)
    })
  }
}

// 内存管理工具
export class MemoryManager {
  private static instance: MemoryManager
  private cleanupTasks: (() => void)[] = []

  static getInstance(): MemoryManager {
    if (!MemoryManager.instance) {
      MemoryManager.instance = new MemoryManager()
    }
    return MemoryManager.instance
  }

  addCleanupTask(task: () => void) {
    this.cleanupTasks.push(task)
  }

  cleanup() {
    this.cleanupTasks.forEach(task => {
      try {
        task()
      } catch (error) {
        console.warn('Cleanup task failed:', error)
      }
    })
    this.cleanupTasks = []
  }

  getMemoryUsage(): any {
    const memory = (performance as any).memory
    if (memory) {
      return {
        used: memory.usedJSHeapSize,
        total: memory.totalJSHeapSize,
        limit: memory.jsHeapSizeLimit,
        usagePercentage: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100,
      }
    }
    return null
  }

  checkMemoryPressure(): boolean {
    const usage = this.getMemoryUsage()
    return usage ? usage.usagePercentage > 80 : false
  }
}

export const memoryManager = MemoryManager.getInstance()
export const resourcePreloader = ResourcePreloader.getInstance()

// 导出便捷函数
export const markPerformance = (name: string) => performanceMonitor.mark(name)
export const measurePerformance = (name: string, startMark: string, endMark?: string) => 
  performanceMonitor.measure(name, startMark, endMark)
export const getPerformanceReport = () => performanceMonitor.getPerformanceReport()