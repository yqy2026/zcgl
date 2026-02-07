import { useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';
import { isDevelopmentMode } from '@/utils/runtimeEnv';

interface RoutePerformanceMetrics {
  FCP?: number;
  LCP?: number;
  FID?: number;
  CLS?: number;
  routeLoadTime: number;
  componentLoadTime: number;
  renderTime: number;
  interactiveTime: number;
  memoryUsage?: number;
  jsHeapSize?: number;
  resourceLoadTimes: Array<{ name: string; duration: number; size: number }>;
  errorCount: number;
  retryCount: number;
  route: string;
  navigationType: string;
  timestamp: number;
  userAgent: string;
  sessionId: string;
}

interface RoutePerformanceConfig {
  enableWebVitals: boolean;
  enableMemoryTracking: boolean;
  enableNetworkTracking: boolean;
  sampleRate: number;
  maxStoredMetrics: number;
  reportInterval: number;
  enableAutoReporting: boolean;
}

type PerformanceWithMemory = Performance & {
  memory?: { usedJSHeapSize: number; totalJSHeapSize: number };
};

type PerformanceWindow = Window & {
  __ROUTE_PERFORMANCE__?: {
    getMetrics: () => RoutePerformanceMetrics[];
    getAggregatedMetrics: () => ReturnType<RoutePerformanceMonitor['getAggregatedMetrics']>;
    exportData: () => {
      metrics: RoutePerformanceMetrics[];
      aggregated: ReturnType<RoutePerformanceMonitor['getAggregatedMetrics']>;
      timestamp: number;
    };
  };
};

class RoutePerformanceMonitor {
  private config: RoutePerformanceConfig;
  private metrics: RoutePerformanceMetrics[];
  private observers: PerformanceObserver[];
  private sessionId: string;
  private reportTimer: NodeJS.Timeout | null = null;
  private isSupported: boolean;

  constructor(config: Partial<RoutePerformanceConfig> = {}) {
    this.config = {
      enableWebVitals: true,
      enableMemoryTracking: true,
      enableNetworkTracking: true,
      sampleRate: 1.0,
      maxStoredMetrics: 100,
      reportInterval: 30000,
      enableAutoReporting: true,
      ...config,
    };

    this.metrics = [];
    this.observers = [];
    this.sessionId = this.generateSessionId();
    this.isSupported = this.checkSupport();

    if (this.isSupported) {
      this.initializeObservers();
      this.startAutoReporting();
    }
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private checkSupport(): boolean {
    return window.performance != null && window.PerformanceObserver != null;
  }

  private initializeObservers() {
    if (!this.isSupported) return;

    if (this.config.enableWebVitals) {
      this.observeWebVitals();
    }

    if (this.config.enableNetworkTracking) {
      this.observeResourceTiming();
    }

    const perfWithMemory = performance as PerformanceWithMemory;
    if (this.config.enableMemoryTracking && perfWithMemory.memory) {
      this.observeMemory();
    }
  }

  private observeWebVitals() {
    try {
      const fcpObserver = new PerformanceObserver(list => {
        for (const entry of list.getEntries()) {
          if (entry.name === 'first-contentful-paint') {
            this.updateCurrentMetric('FCP', entry.startTime);
          }
        }
      });
      fcpObserver.observe({ entryTypes: ['paint'] });
      this.observers.push(fcpObserver);

      const lcpObserver = new PerformanceObserver(list => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        if (lastEntry != null) {
          this.updateCurrentMetric('LCP', lastEntry.startTime);
        }
      });
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
      this.observers.push(lcpObserver);

      const fidObserver = new PerformanceObserver(list => {
        for (const entry of list.getEntries()) {
          this.updateCurrentMetric(
            'FID',
            (entry as PerformanceEventTiming & { processingStart?: number }).processingStart
              ? (entry as PerformanceEventTiming & { processingStart: number }).processingStart -
                  entry.startTime
              : 0
          );
        }
      });
      fidObserver.observe({ entryTypes: ['first-input'] });
      this.observers.push(fidObserver);

      let clsValue = 0;
      const clsObserver = new PerformanceObserver(list => {
        for (const entry of list.getEntries()) {
          const layoutShiftEntry = entry as PerformanceEntry & {
            hadRecentInput?: boolean;
            value?: number;
          };
          if (layoutShiftEntry.hadRecentInput === false && (layoutShiftEntry.value ?? 0) > 0) {
            clsValue += layoutShiftEntry.value ?? 0;
          }
        }
        this.updateCurrentMetric('CLS', clsValue);
      });
      clsObserver.observe({ entryTypes: ['layout-shift'] });
      this.observers.push(clsObserver);
    } catch (error) {
      console.warn('Web Vitals observer initialization failed:', error);
    }
  }

  private observeResourceTiming() {
    try {
      const resourceObserver = new PerformanceObserver(list => {
        const entries = list.getEntries();
        const resourceTimes: RoutePerformanceMetrics['resourceLoadTimes'] = entries.map(entry => ({
          name: entry.name,
          duration: entry.duration,
          size: (entry as PerformanceResourceTiming).transferSize || 0,
        }));
        this.updateCurrentMetric('resourceLoadTimes', resourceTimes);
      });
      resourceObserver.observe({ entryTypes: ['resource'] });
      this.observers.push(resourceObserver);
    } catch (error) {
      console.warn('Resource timing observer initialization failed:', error);
    }
  }

  private observeMemory() {
    try {
      const memoryObserver = new PerformanceObserver(() => {
        const memory = (performance as PerformanceWithMemory).memory;
        if (memory) {
          this.updateCurrentMetric('memoryUsage', memory.usedJSHeapSize);
          this.updateCurrentMetric('jsHeapSize', memory.totalJSHeapSize);
        }
      });
      memoryObserver.observe({ entryTypes: ['measure'] });
      this.observers.push(memoryObserver);
    } catch (error) {
      console.warn('Memory observer initialization failed:', error);
    }
  }

  private updateCurrentMetric<K extends keyof RoutePerformanceMetrics>(
    key: K,
    value: RoutePerformanceMetrics[K]
  ) {
    if (this.metrics.length === 0) return;

    const currentMetric = this.metrics[this.metrics.length - 1];
    currentMetric[key] = value;
  }

  startRouteMonitoring(route: string, navigationType: string) {
    if (!this.isSupported) return;

    if (Math.random() > this.config.sampleRate) return;

    const startTime = performance.now();

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
      sessionId: this.sessionId,
    };

    this.metrics.push(metric);

    if (this.metrics.length > this.config.maxStoredMetrics) {
      this.metrics = this.metrics.slice(-this.config.maxStoredMetrics);
    }

    performance.mark(`route-start-${route}`);

    return {
      endComponentLoad: () => {
        const componentTime = performance.now() - startTime;
        this.updateCurrentMetric('componentLoadTime', componentTime);
        performance.mark(`component-loaded-${route}`);
      },

      endRender: () => {
        const renderTime = performance.now() - startTime;
        this.updateCurrentMetric('renderTime', renderTime);
        performance.mark(`render-complete-${route}`);
      },

      endInteractive: () => {
        const interactiveTime = performance.now() - startTime;
        this.updateCurrentMetric('interactiveTime', interactiveTime);
        this.updateCurrentMetric('routeLoadTime', interactiveTime);
        performance.mark(`route-interactive-${route}`);

        try {
          performance.measure(
            `route-total-${route}`,
            `route-start-${route}`,
            `route-interactive-${route}`
          );
        } catch {
          return;
        }
      },
    };
  }

  recordError(route: string, _error: Error) {
    const metric = this.metrics.find(m => m.route === route);
    if (metric) {
      metric.errorCount++;
    }
  }

  recordRetry(route: string) {
    const metric = this.metrics.find(m => m.route === route);
    if (metric) {
      metric.retryCount++;
    }
  }

  getMetrics(route?: string): RoutePerformanceMetrics[] {
    if (route != null && route !== '') {
      return this.metrics.filter(m => m.route === route);
    }
    return [...this.metrics];
  }

  getAggregatedMetrics(route?: string) {
    const metrics = this.getMetrics(route);
    if (metrics.length === 0) return null;

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
      routes: [...new Set(metrics.map(m => m.route))],
    };

    const sums = metrics.reduce(
      (acc, metric) => {
        acc.routeLoadTime += metric.routeLoadTime;
        acc.componentLoadTime += metric.componentLoadTime;
        acc.renderTime += metric.renderTime;
        acc.interactiveTime += metric.interactiveTime;
        acc.FCP += metric.FCP ?? 0;
        acc.LCP += metric.LCP ?? 0;
        acc.FID += metric.FID ?? 0;
        acc.CLS += metric.CLS ?? 0;
        acc.errorCount += metric.errorCount;
        acc.retryCount += metric.retryCount;
        return acc;
      },
      {
        routeLoadTime: 0,
        componentLoadTime: 0,
        renderTime: 0,
        interactiveTime: 0,
        FCP: 0,
        LCP: 0,
        FID: 0,
        CLS: 0,
        errorCount: 0,
        retryCount: 0,
      }
    );

    const count = metrics.length;
    aggregated.avgLoadTime = sums.routeLoadTime / count;
    aggregated.avgComponentLoadTime = sums.componentLoadTime / count;
    aggregated.avgRenderTime = sums.renderTime / count;
    aggregated.avgInteractiveTime = sums.interactiveTime / count;
    aggregated.avgFCP = sums.FCP / count;
    aggregated.avgLCP = sums.LCP / count;
    aggregated.avgFID = sums.FID / count;
    aggregated.avgCLS = sums.CLS / count;
    aggregated.totalErrors = sums.errorCount;
    aggregated.totalRetries = sums.retryCount;

    return aggregated;
  }

  private startAutoReporting() {
    if (!this.config.enableAutoReporting) return;

    this.reportTimer = setInterval(() => {
      this.reportMetrics();
    }, this.config.reportInterval);
  }

  private async reportMetrics() {
    if (this.metrics.length === 0) return;

    try {
      const reportData = {
        sessionId: this.sessionId,
        metrics: this.metrics,
        aggregated: this.getAggregatedMetrics(),
        timestamp: Date.now(),
      };

      await fetch('/api/monitoring/route-performance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(reportData),
      });
    } catch (error) {
      console.warn('性能指标上报失败:', error);
    }
  }

  clearMetrics() {
    this.metrics = [];
  }

  destroy() {
    this.observers.forEach(observer => {
      observer.disconnect();
    });
    this.observers = [];

    if (this.reportTimer) {
      clearInterval(this.reportTimer);
      this.reportTimer = null;
    }

    this.clearMetrics();
  }
}

export const useRoutePerformanceMonitor = (config?: Partial<RoutePerformanceConfig>) => {
  const location = useLocation();
  const navigationType = useNavigationType();
  const monitorRef = useRef<RoutePerformanceMonitor | null>(null);
  const monitoringRef = useRef<{
    endComponentLoad: () => void;
    endRender: () => void;
    endInteractive: () => void;
  } | null>(null);

  if (!monitorRef.current) {
    monitorRef.current = new RoutePerformanceMonitor(config);
  }

  const monitor = monitorRef.current;

  useEffect(() => {
    if (monitor == null) return;

    const route = location.pathname;
    const navType =
      navigationType === 'POP' ? 'back' : navigationType === 'PUSH' ? 'navigate' : 'replace';

    const monitoring = monitor.startRouteMonitoring(route, navType);
    monitoringRef.current = monitoring ?? null;

    const timer = setTimeout(() => {
      if (monitoring != null) {
        monitoring.endInteractive();
      }
    }, 100);

    return () => {
      clearTimeout(timer);
    };
  }, [location.pathname, navigationType, monitor]);

  useEffect(() => {
    return () => {
      if (monitor != null) {
        monitor.destroy();
      }
    };
  }, [monitor]);

  const recordError = useCallback(
    (error: Error) => {
      if (monitor != null) {
        monitor.recordError(location.pathname, error);
      }
    },
    [monitor, location.pathname]
  );

  const recordRetry = useCallback(() => {
    if (monitor != null) {
      monitor.recordRetry(location.pathname);
    }
  }, [monitor, location.pathname]);

  const getMetrics = useCallback(
    (route?: string) => {
      return monitor != null ? monitor.getMetrics(route) : [];
    },
    [monitor]
  );

  const getAggregatedMetrics = useCallback(
    (route?: string) => {
      return monitor != null ? monitor.getAggregatedMetrics(route) : null;
    },
    [monitor]
  );

  return {
    recordError,
    recordRetry,
    getMetrics,
    getAggregatedMetrics,
    monitor,
  };
};

export const usePerformanceDebug = () => {
  const { getMetrics, getAggregatedMetrics } = useRoutePerformanceMonitor();

  useEffect(() => {
    if (isDevelopmentMode()) {
      const performanceWindow = window as PerformanceWindow;
      performanceWindow.__ROUTE_PERFORMANCE__ = {
        getMetrics,
        getAggregatedMetrics,
        exportData: () => ({
          metrics: getMetrics(),
          aggregated: getAggregatedMetrics(),
          timestamp: Date.now(),
        }),
      };
    }
  }, [getMetrics, getAggregatedMetrics]);
};

export default RoutePerformanceMonitor;
