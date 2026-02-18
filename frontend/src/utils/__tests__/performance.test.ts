import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

type PerformanceModule = typeof import('../performance');
type EntryMap = Record<string, PerformanceEntry[]>;

const loadPerformanceModule = async (): Promise<PerformanceModule> => {
  vi.resetModules();
  return import('../performance');
};

const stubPerformanceObserver = (entriesByType: EntryMap = {}, throwingTypes: string[] = []) => {
  class PerformanceObserverMock {
    private callback: PerformanceObserverCallback;

    constructor(callback: PerformanceObserverCallback) {
      this.callback = callback;
    }

    observe = vi.fn((options: PerformanceObserverInit) => {
      const entryType = options.entryTypes?.[0];
      if (entryType == null) {
        return;
      }
      if (throwingTypes.includes(entryType)) {
        throw new Error(`observe failed for ${entryType}`);
      }
      const entries = entriesByType[entryType] ?? [];
      this.callback(
        {
          getEntries: () => entries,
        } as PerformanceObserverEntryList,
        this as unknown as PerformanceObserver
      );
    });

    disconnect = vi.fn();
  }

  vi.stubGlobal(
    'PerformanceObserver',
    PerformanceObserverMock as unknown as typeof PerformanceObserver
  );
};

describe('performance utils', () => {
  beforeEach(() => {
    stubPerformanceObserver();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    delete (globalThis as typeof globalThis & { requestIdleCallback?: unknown })
      .requestIdleCallback;
  });

  it('preloadManager deduplicates high-priority preload and marks module as preloaded', async () => {
    const { preloadManager } = await loadPerformanceModule();
    const importFn = vi.fn(async () => ({ name: 'module-a' }));

    const first = preloadManager.preload(importFn, 'module-a', 'high');
    const second = preloadManager.preload(importFn, 'module-a', 'high');

    expect(first).toBe(second);
    await expect(first).resolves.toEqual({ name: 'module-a' });

    expect(importFn).toHaveBeenCalledTimes(1);
    expect(preloadManager.isPreloaded('module-a')).toBe(true);
    expect(preloadManager.getPreloadedModules()).toContain('module-a');
  });

  it('preloadManager supports low-priority scheduling via requestIdleCallback and fallback retry after failure', async () => {
    const idleSpy = vi.fn((callback: () => void) => {
      callback();
      return 1;
    });
    (
      globalThis as typeof globalThis & { requestIdleCallback: typeof idleSpy }
    ).requestIdleCallback = idleSpy;

    const { preloadManager } = await loadPerformanceModule();
    const importFn = vi
      .fn<() => Promise<string>>()
      .mockRejectedValueOnce(new Error('load failed'))
      .mockResolvedValueOnce('ok');

    await expect(preloadManager.preload(importFn, 'module-b', 'low')).rejects.toThrow(
      'load failed'
    );
    expect(preloadManager.isPreloaded('module-b')).toBe(false);

    await expect(preloadManager.preload(importFn, 'module-b', 'low')).resolves.toBe('ok');
    expect(idleSpy).toHaveBeenCalled();
    expect(importFn).toHaveBeenCalledTimes(2);
    expect(preloadManager.isPreloaded('module-b')).toBe(true);
  });

  it('preloadManager falls back to setTimeout when requestIdleCallback is unavailable', async () => {
    vi.useFakeTimers();
    const { preloadManager } = await loadPerformanceModule();
    const importFn = vi.fn<() => Promise<string>>().mockResolvedValue('timeout-ok');

    const promise = preloadManager.preload(importFn, 'module-c', 'low');
    await vi.runAllTimersAsync();

    await expect(promise).resolves.toBe('timeout-ok');
    expect(importFn).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('createLazyComponent adds performance marks and measures for chunk loading', async () => {
    const markSpy = vi.spyOn(performance, 'mark').mockImplementation(() => {});
    const measureSpy = vi.spyOn(performance, 'measure').mockImplementation(() => {});
    vi.resetModules();
    vi.doMock('react', async () => {
      const actual = await vi.importActual<typeof import('react')>('react');
      return {
        ...actual,
        lazy: (loader: () => Promise<unknown>) => loader,
      };
    });
    const { createLazyComponent } = await import('../performance');
    const lazyLoader = createLazyComponent(
      async () => ({
        default: (() => null) as unknown as import('react').ComponentType<Record<string, unknown>>,
      }),
      'dashboard'
    ) as unknown as () => Promise<unknown>;

    await lazyLoader();
    vi.doUnmock('react');

    expect(markSpy).toHaveBeenCalledWith('lazy-load-start-dashboard');
    expect(markSpy).toHaveBeenCalledWith('lazy-load-end-dashboard');
    expect(measureSpy).toHaveBeenCalledWith(
      'lazy-load-dashboard',
      'lazy-load-start-dashboard',
      'lazy-load-end-dashboard'
    );
  });

  it('ResourcePreloader caches image/script/style resources', async () => {
    let imageCreated = 0;
    class ImageMock {
      onload: null | (() => void) = null;
      onerror: null | (() => void) = null;
      private _src = '';
      constructor() {
        imageCreated++;
      }
      set src(value: string) {
        this._src = value;
        this.onload?.();
      }
      get src() {
        return this._src;
      }
    }
    vi.stubGlobal('Image', ImageMock as unknown as typeof Image);

    const appendSpy = vi.spyOn(document.head, 'appendChild');
    const { ResourcePreloader } = await loadPerformanceModule();
    const preloader = ResourcePreloader.getInstance();

    await preloader.preloadImage('/logo.png');
    await preloader.preloadImage('/logo.png');
    expect(imageCreated).toBe(1);

    const scriptPromise = preloader.preloadScript('/app.js');
    const scriptLink = appendSpy.mock.calls[0]?.[0] as HTMLLinkElement;
    scriptLink.onload?.(new Event('load'));
    await scriptPromise;
    await preloader.preloadScript('/app.js');

    const stylePromise = preloader.preloadStyle('/app.css');
    const styleLink = appendSpy.mock.calls[1]?.[0] as HTMLLinkElement;
    styleLink.onload?.(new Event('load'));
    await stylePromise;
    await preloader.preloadStyle('/app.css');

    expect(appendSpy).toHaveBeenCalledTimes(2);
  });

  it('MemoryManager executes cleanup tasks and reports memory pressure', async () => {
    const { MemoryManager } = await loadPerformanceModule();
    const manager = MemoryManager.getInstance();
    const taskA = vi.fn();
    const taskB = vi.fn(() => {
      throw new Error('cleanup failed');
    });

    manager.addCleanupTask(taskA);
    manager.addCleanupTask(taskB);
    manager.cleanup();
    manager.cleanup();

    expect(taskA).toHaveBeenCalledTimes(1);
    expect(taskB).toHaveBeenCalledTimes(1);

    const originalMemory = (performance as { memory?: unknown }).memory;
    Object.defineProperty(performance, 'memory', {
      configurable: true,
      value: {
        usedJSHeapSize: 90,
        totalJSHeapSize: 100,
        jsHeapSizeLimit: 100,
      },
    });

    const usage = manager.getMemoryUsage();
    expect(usage).toMatchObject({
      used: 90,
      total: 100,
      limit: 100,
      usagePercentage: 90,
    });
    expect(manager.checkMemoryPressure()).toBe(true);

    Object.defineProperty(performance, 'memory', {
      configurable: true,
      value: originalMemory,
    });
  });

  it('collects web vitals, resource categories, long task and user timing metrics', async () => {
    stubPerformanceObserver({
      'first-contentful-paint': [
        {
          name: 'fcp-entry',
          entryType: 'paint',
          startTime: 2000,
          duration: 0,
          toJSON: () => ({}),
        } as PerformanceEntry,
      ],
      'largest-contentful-paint': [
        {
          name: 'lcp-entry',
          entryType: 'largest-contentful-paint',
          startTime: 2600,
          duration: 0,
          toJSON: () => ({}),
        } as PerformanceEntry,
      ],
      'first-input': [
        {
          name: 'first-input',
          entryType: 'first-input',
          startTime: 50,
          processingStart: 170,
          duration: 0,
          toJSON: () => ({}),
        } as PerformanceEventTiming as PerformanceEntry,
      ],
      'layout-shift': [
        {
          name: 'layout-shift-a',
          entryType: 'layout-shift',
          startTime: 0,
          duration: 0,
          hadRecentInput: false,
          value: 0.2,
          toJSON: () => ({}),
        } as PerformanceEntry,
        {
          name: 'layout-shift-b',
          entryType: 'layout-shift',
          startTime: 0,
          duration: 0,
          hadRecentInput: true,
          value: 0.3,
          toJSON: () => ({}),
        } as PerformanceEntry,
        {
          name: 'layout-shift-invalid',
          entryType: 'layout-shift',
          startTime: 0,
          duration: 0,
          toJSON: () => ({}),
        } as PerformanceEntry,
      ],
      resource: [
        {
          name: '/assets/app.js',
          entryType: 'resource',
          startTime: 0,
          responseEnd: 1200,
          duration: 1200,
          toJSON: () => ({}),
        } as PerformanceResourceTiming as PerformanceEntry,
        {
          name: '/assets/app.css',
          entryType: 'resource',
          startTime: 0,
          responseEnd: 100,
          duration: 100,
          toJSON: () => ({}),
        } as PerformanceResourceTiming as PerformanceEntry,
        {
          name: '/assets/logo.png',
          entryType: 'resource',
          startTime: 0,
          responseEnd: 50,
          duration: 50,
          toJSON: () => ({}),
        } as PerformanceResourceTiming as PerformanceEntry,
        {
          name: '/api/v1/assets',
          entryType: 'resource',
          startTime: 0,
          responseEnd: 500,
          duration: 500,
          toJSON: () => ({}),
        } as PerformanceResourceTiming as PerformanceEntry,
        {
          name: '/static/font.woff2',
          entryType: 'resource',
          startTime: 0,
          duration: 0,
          toJSON: () => ({}),
        } as PerformanceEntry,
      ],
      longtask: [
        {
          name: 'long-task',
          entryType: 'longtask',
          startTime: 0,
          duration: 180,
          toJSON: () => ({}),
        } as PerformanceEntry,
      ],
      measure: [
        {
          name: 'heavy-operation',
          entryType: 'measure',
          startTime: 0,
          duration: 150,
          toJSON: () => ({}),
        } as PerformanceEntry,
      ],
    });

    const { performanceMonitor } = await loadPerformanceModule();
    const metrics = performanceMonitor.getMetrics();

    expect(metrics.fcp).toBe(2000);
    expect(metrics.lcp).toBe(2600);
    expect(metrics.fid).toBe(120);
    expect(metrics.cls).toBeCloseTo(0.2);
    expect(metrics['resource-script']).toBe(1200);
    expect(metrics['resource-style']).toBe(100);
    expect(metrics['resource-image']).toBe(50);
    expect(metrics['resource-api']).toBe(500);
    expect(metrics['resource-other']).toBe(0);
    expect(metrics['long-tasks']).toBe(1);
    expect(metrics['user-timing-heavy-operation']).toBe(150);
  });

  it('handles missing observer support and observe failures gracefully', async () => {
    delete (globalThis as typeof globalThis & { PerformanceObserver?: unknown })
      .PerformanceObserver;
    const withoutObserverModule = await loadPerformanceModule();
    expect(withoutObserverModule.performanceMonitor.getMetrics()).toEqual({});

    stubPerformanceObserver({}, [
      'first-contentful-paint',
      'largest-contentful-paint',
      'first-input',
      'layout-shift',
      'resource',
      'longtask',
      'measure',
    ]);
    const withThrowingObserverModule = await loadPerformanceModule();
    expect(withThrowingObserverModule.performanceMonitor.getMetrics()).toEqual({});
  });

  it('supports disconnect and reports null memory usage when memory API is unavailable', async () => {
    const { MemoryManager, performanceMonitor } = await loadPerformanceModule();
    const disconnectSpy = vi.fn();
    (
      performanceMonitor as unknown as {
        observer?: { disconnect: () => void };
      }
    ).observer = {
      disconnect: disconnectSpy,
    };

    performanceMonitor.disconnect();
    expect(disconnectSpy).toHaveBeenCalledTimes(1);

    const originalMemory = (performance as { memory?: unknown }).memory;
    Object.defineProperty(performance, 'memory', {
      configurable: true,
      value: undefined,
    });

    const manager = MemoryManager.getInstance();
    expect(manager.getMemoryUsage()).toBeNull();
    expect(manager.checkMemoryPressure()).toBe(false);

    Object.defineProperty(performance, 'memory', {
      configurable: true,
      value: originalMemory,
    });
  });

  it('mark/measure/report helpers proxy browser performance APIs', async () => {
    const markSpy = vi.spyOn(performance, 'mark').mockImplementation(() => {});
    const measureSpy = vi.spyOn(performance, 'measure').mockImplementation(() => {});
    const navigationEntry = { name: 'navigation' } as PerformanceNavigationTiming;
    const resources = Array.from({ length: 25 }, (_, i) => ({
      name: `res-${i}`,
    })) as unknown as PerformanceResourceTiming[];
    vi.spyOn(performance, 'getEntriesByType').mockImplementation(type => {
      if (type === 'navigation') return [navigationEntry];
      if (type === 'resource') return resources;
      return [];
    });

    const originalMemory = (performance as { memory?: unknown }).memory;
    Object.defineProperty(performance, 'memory', {
      configurable: true,
      value: {
        usedJSHeapSize: 10,
        totalJSHeapSize: 20,
        jsHeapSizeLimit: 40,
      },
    });

    const { getPerformanceReport, markPerformance, measurePerformance } =
      await loadPerformanceModule();

    markPerformance('start');
    measurePerformance('metric', 'start', 'end');
    const report = getPerformanceReport();

    expect(markSpy).toHaveBeenCalledWith('start');
    expect(measureSpy).toHaveBeenCalledWith('metric', 'start', 'end');
    expect(report.navigation).toBe(navigationEntry);
    expect(report.resources).toHaveLength(20);
    expect(report.resources[0]?.name).toBe('res-5');
    expect(report.resources[19]?.name).toBe('res-24');
    expect(report.memory).toEqual({
      usedJSHeapSize: 10,
      totalJSHeapSize: 20,
      jsHeapSizeLimit: 40,
    });

    Object.defineProperty(performance, 'memory', {
      configurable: true,
      value: originalMemory,
    });
  });
});
