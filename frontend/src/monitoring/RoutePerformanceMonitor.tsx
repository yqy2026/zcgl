/**
 * 路由性能监控器
 * 监控路由加载时间、交互性能和用户体验指标
 */

import { useEffect, useRef, useCallback } from 'react'
import { useLocation, useNavigationType } from 'react-router-dom'

interface RoutePerformanceMetrics {
  // Core Web Vitals
  FCP?: number  // First Contentful Paint
  LCP?: number  // Largest Contentful Paint
  FID?: number  // First Input Delay
  CLS?: number  // Cumulative Layout Shift

  // Route specific metrics
  routeLoadTime: number
  componentLoadTime: number
  renderTime: number
  interactiveTime: number

  // Memory metrics
  memoryUsage?: number
  jsHeapSize?: number

  // Network metrics
  resourceLoadTimes: Array<{ name: string; duration: number; size: number }>

  // User experience metrics
  errorCount: number
  retryCount: number

  // Metadata
  route: string
  navigationType: string
  timestamp: number
  userAgent: string
  sessionId: string
}

interface RoutePerformanceConfig {
  enableWebVitals: boolean
  enableMemoryTracking: boolean
  enableNetworkTracking: boolean
  sampleRate: number
  maxStoredMetrics: number
  reportInterval: number
  enableAutoReporting: boolean
}

class RoutePerformanceMonitor {
  private config: RoutePerformanceConfig
  private metrics: RoutePerformanceMetrics[]
  private observers: PerformanceObserver[]
  private sessionId: string
  private reportTimer: NodeJS.Timeout | null = null
  private isSupported: boolean

  constructor(config: Partial<RoutePerformanceConfig> = {}) {
    this.config = {
      enableWebVitals: true,
      enableMemoryTracking: true,
      enableNetworkTracking: true,
      sampleRate: 1.0,
      maxStoredMetrics: 100,
      reportInterval: 30000, // 30秒
      enableAutoReporting: true,
      ...config
    }

    this.metrics = []
    this.observers = []
    this.sessionId = this.generateSessionId()
    this.isSupported = this.checkSupport()

    if (this.isSupported) {
      this.initializeObservers()
      this.startAutoReporting()
    }
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  private checkSupport(): boolean {
    return window.performance != null && window.PerformanceObserver != null
  }

  private initializeObservers() {
    if (!this.isSupported) return

    // Core Web Vitals
    if (this.config.enableWebVitals) {
      this.observeWebVitals()
    }

    // Resource timing
    if (this.config.enableNetworkTracking) {
      this.observeResourceTiming()
    }

    // Memory timing (Chrome only)
    if (this.config.enableMemoryTracking && (performance as unknown as { memory?: { usedJSHeapSize: number; totalJSHeapSize: number } }).memory) {
      this.observeMemory()
    }
  }

  private observeWebVitals() {
    try {
      // First Contentful Paint
      const fcpObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.name === 'first-contentful-paint') {
            this.updateCurrentMetric('FCP', entry.startTime)
          }
        }
      })
      fcpObserver.observe({ entryTypes: ['paint'] })
      this.observers.push(fcpObserver)

      // Largest Contentful Paint
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        const lastEntry = entries[entries.length - 1]
        if (lastEntry != null) {
          this.updateCurrentMetric('LCP', lastEntry.startTime)
        }
      })
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] })
      this.observers.push(lcpObserver)

      // First Input Delay
      const fidObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.updateCurrentMetric('FID', (entry as PerformanceEventTiming & { processingStart?: number }).processingStart ? (entry as PerformanceEventTiming & { processingStart: number }).processingStart - entry.startTime : 0)
        }
      })
      fidObserver.observe({ entryTypes: ['first-input'] })
      this.observers.push(fidObserver)

      // Cumulative Layout Shift
      let clsValue = 0
      const clsObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const layoutShiftEntry = entry as PerformanceEntry & { hadRecentInput?: boolean; value?: number }
          if (layoutShiftEntry.hadRecentInput === false && (layoutShiftEntry.value ?? 0) > 0) {
            clsValue += layoutShiftEntry.value
          }
        }
        this.updateCurrentMetric('CLS', clsValue)
      })
      clsObserver.observe({ entryTypes: ['layout-shift'] })
      this.observers.push(clsObserver)
    } catch (error) {
      console.warn('Web Vitals observer initialization failed:', error)
    }
  }

  private observeResourceTiming() {
    try {
      const resourceObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        const resourceTimes = entries.map(entry => ({
          name: entry.name,
          duration: entry.duration,
          size: (entry as PerformanceResourceTiming).transferSize || 0
        }))
        this.updateCurrentMetric('resourceLoadTimes', resourceTimes)
      })
      resourceObserver.observe({ entryTypes: ['resource'] })
      this.observers.push(resourceObserver)
    } catch (error) {
      console.warn('Resource timing observer initialization failed:', error)
    }
  }

  private observeMemory() {
    try {
      const memoryObserver = new PerformanceObserver(() => {
        const memory = (performance as unknown as { memory?: { usedJSHeapSize: number; totalJSHeapSize: number } }).memory
        if (memory) {
          this.updateCurrentMetric('memoryUsage', memory.usedJSHeapSize)
          this.updateCurrentMetric('jsHeapSize', memory.totalJSHeapSize)
        }
      })
      memoryObserver.observe({ entryTypes: ['measure'] })
      this.observers.push(memoryObserver)
    } catch (error) {
      console.warn('Memory observer initialization failed:', error)
    }
  }

  private updateCurrentMetric(key: keyof RoutePerformanceMetrics, value: unknown) {
    if (this.metrics.length === 0) return

    const currentMetric = this.metrics[this.metrics.length - 1]
    ;(currentMetric as unknown as Record<string, unknown>)[key] = value
  }

  startRouteMonitoring(route: string, navigationType: string) {
    if (!this.isSupported) return

    // 如果采样率不满，则跳过
    if (Math.random() > this.config.sampleRate) return

    const startTime = performance.now()

    const metric: RoutePerformanceMetrics = {
      routeLoadTime: 0,
      componentLoadTime: 0,
      renderTime: 0,
      interactiveTime: 0,
      resourceLoadTimes: [],
      errorCount: 0,
      retryCount: 0,
      route,
      navigationType,
      timestamp: Date.now(),
      userAgent: navigator.userAgent,
      sessionId: this.sessionId
    }

    this.metrics.push(metric)

    // 清理旧的指标
    if (this.metrics.length > this.config.maxStoredMetrics) {
      this.metrics = this.metrics.slice(-this.config.maxStoredMetrics)
    }

    // 设置性能标记
    performance.mark(`route-start-${route}`)

    return {
      endComponentLoad: () => {
        const componentTime = performance.now() - startTime
        this.updateCurrentMetric('componentLoadTime', componentTime)
        performance.mark(`component-loaded-${route}`)
      },

      endRender: () => {
        const renderTime = performance.now() - startTime
        this.updateCurrentMetric('renderTime', renderTime)
        performance.mark(`render-complete-${route}`)
      },

      endInteractive: () => {
        const interactiveTime = performance.now() - startTime
        this.updateCurrentMetric('interactiveTime', interactiveTime)
        this.updateCurrentMetric('routeLoadTime', interactiveTime)
        performance.mark(`route-interactive-${route}`)

        // 创建性能测量
        try {
          performance.measure(
            `route-total-${route}`,
            `route-start-${route}`,
            `route-interactive-${route}`
          )
        } catch {
          // 忽略测量错误
        }
      }
    }
  }

  recordError(route: string, _error: Error) {
    const metric = this.metrics.find(m => m.route === route)
    if (metric) {
      metric.errorCount++
    }
  }

  recordRetry(route: string) {
    const metric = this.metrics.find(m => m.route === route)
    if (metric) {
      metric.retryCount++
    }
  }

  getMetrics(route?: string): RoutePerformanceMetrics[] {
    if (route != null && route !== '') {
      return this.metrics.filter(m => m.route === route)
    }
    return [...this.metrics]
  }

  getAggregatedMetrics(route?: string) {
    const metrics = this.getMetrics(route)
    if (metrics.length === 0) return null

    const aggregated = {
      avgLoadTime: 0,
      avgComponentLoadTime: 0,
      avgRenderTime: 0,
      avgInteractiveTime: 0,
      avgFCP: 0,
      avgLCP: 0,
      avgFID: 0,
      avgCLS: 0,
      totalErrors: 0,
      totalRetries: 0,
      sampleCount: metrics.length,
      routes: [...new Set(metrics.map(m => m.route))]
    }

    const sums = metrics.reduce((acc, metric) => {
      acc.routeLoadTime += metric.routeLoadTime
      acc.componentLoadTime += metric.componentLoadTime
      acc.renderTime += metric.renderTime
      acc.interactiveTime += metric.interactiveTime
      acc.FCP += metric.FCP ?? 0
      acc.LCP += metric.LCP ?? 0
      acc.FID += metric.FID ?? 0
      acc.CLS += metric.CLS ?? 0
      acc.errorCount += metric.errorCount
      acc.retryCount += metric.retryCount
      return acc
    }, {
      routeLoadTime: 0,
      componentLoadTime: 0,
      renderTime: 0,
      interactiveTime: 0,
      FCP: 0,
      LCP: 0,
      FID: 0,
      CLS: 0,
      errorCount: 0,
      retryCount: 0
    })

    const count = metrics.length
    aggregated.avgLoadTime = sums.routeLoadTime / count
    aggregated.avgComponentLoadTime = sums.componentLoadTime / count
    aggregated.avgRenderTime = sums.renderTime / count
    aggregated.avgInteractiveTime = sums.interactiveTime / count
    aggregated.avgFCP = sums.FCP / count
    aggregated.avgLCP = sums.LCP / count
    aggregated.avgFID = sums.FID / count
    aggregated.avgCLS = sums.CLS / count
    aggregated.totalErrors = sums.errorCount
    aggregated.totalRetries = sums.retryCount

    return aggregated
  }

  private startAutoReporting() {
    if (!this.config.enableAutoReporting) return

    this.reportTimer = setInterval(() => {
      this.reportMetrics()
    }, this.config.reportInterval)
  }

  private async reportMetrics() {
    if (this.metrics.length === 0) return

    try {
      const reportData = {
        sessionId: this.sessionId,
        metrics: this.metrics,
        aggregated: this.getAggregatedMetrics(),
        timestamp: Date.now()
      }

      // 发送到监控服务
      await fetch('/api/monitoring/route-performance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(reportData)
      })

      // Route metrics reported
    } catch (error) {
      console.warn('性能指标上报失败:', error)
    }
  }

  clearMetrics() {
    this.metrics = []
  }

  destroy() {
    // 清理观察者
    this.observers.forEach(observer => {
      observer.disconnect()
    })
    this.observers = []

    // 清理定时器
    if (this.reportTimer) {
      clearInterval(this.reportTimer)
      this.reportTimer = null
    }

    this.clearMetrics()
  }
}

// Hook for using the performance monitor
export const useRoutePerformanceMonitor = (config?: Partial<RoutePerformanceConfig>) => {
  const location = useLocation()
  const navigationType = useNavigationType()
  const monitorRef = useRef<RoutePerformanceMonitor>()
  const monitoringRef = useRef<{
    endComponentLoad: () => void;
    endRender: () => void;
    endInteractive: () => void;
  } | null>(null)

  // Initialize monitor
  if (!monitorRef.current) {
    monitorRef.current = new RoutePerformanceMonitor(config)
  }

  const monitor = monitorRef.current

  // Start monitoring when route changes
  useEffect(() => {
    if (monitor == null) return

    const route = location.pathname
    const navType = navigationType === 'POP' ? 'back' :
                     navigationType === 'PUSH' ? 'navigate' : 'replace'

    const monitoring = monitor.startRouteMonitoring(route, navType)
    monitoringRef.current = monitoring ?? null

    // Record when route becomes interactive
    const timer = setTimeout(() => {
      if (monitoring != null) {
        monitoring.endInteractive()
      }
    }, 100)

    return () => {
      clearTimeout(timer)
    }
  }, [location.pathname, navigationType, monitor])

  // Cleanup
  useEffect(() => {
    return () => {
      if (monitor != null) {
        monitor.destroy()
      }
    }
  }, [monitor])

  const recordError = useCallback((error: Error) => {
    if (monitor != null) {
      monitor.recordError(location.pathname, error)
    }
  }, [monitor, location.pathname])

  const recordRetry = useCallback(() => {
    if (monitor != null) {
      monitor.recordRetry(location.pathname)
    }
  }, [monitor, location.pathname])

  const getMetrics = useCallback((route?: string) => {
    return monitor != null ? monitor.getMetrics(route) : []
  }, [monitor])

  const getAggregatedMetrics = useCallback((route?: string) => {
    return monitor != null ? monitor.getAggregatedMetrics(route) : null
  }, [monitor])

  return {
    recordError,
    recordRetry,
    getMetrics,
    getAggregatedMetrics,
    monitor
  }
}

// Development tools
export const usePerformanceDebug = () => {
  const { getMetrics, getAggregatedMetrics } = useRoutePerformanceMonitor()

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      // 暴露到全局对象用于调试
      (window as unknown as { __ROUTE_PERFORMANCE__?: {
        getMetrics: () => RoutePerformanceMetrics[];
        getAggregatedMetrics: () => ReturnType<RoutePerformanceMonitor['getAggregatedMetrics']>;
        exportData: () => {
          metrics: RoutePerformanceMetrics[];
          aggregated: ReturnType<RoutePerformanceMonitor['getAggregatedMetrics']>;
          timestamp: number
        }
      } }).__ROUTE_PERFORMANCE__ = {
        getMetrics,
        getAggregatedMetrics,
        exportData: () => ({
          metrics: getMetrics(),
          aggregated: getAggregatedMetrics(),
          timestamp: Date.now()
        })
      }
    }
  }, [getMetrics, getAggregatedMetrics])
}

export default RoutePerformanceMonitor
