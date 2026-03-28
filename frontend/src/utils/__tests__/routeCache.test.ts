import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import routeCache, {
  RoutePerformanceMonitor,
  routePerformanceMonitor,
  stopRouteCacheCleanup,
  useRouteCache,
  useRouteCacheState,
} from '../routeCache';

const formatStderrWrites = (calls: unknown[][]) => calls.map(call => String(call[0] ?? '')).join(' ');

describe('routeCache', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00.000Z'));
    routeCache.clear();
    stopRouteCacheCleanup();
  });

  afterEach(() => {
    routeCache.clear();
    stopRouteCacheCleanup();
    routePerformanceMonitor.clear();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('stores and returns cached route component with metrics', () => {
    const cache = useRouteCache();
    const AssetPage = () => null;

    cache.set('asset-list', AssetPage, 1000);
    const cached = cache.get('asset-list');

    expect(cached?.component).toBe(AssetPage);
    expect(cached?.hitCount).toBe(1);

    const metrics = cache.getMetrics();
    expect(metrics.size).toBe(1);
    expect(metrics.totalHits).toBe(1);
    expect(metrics.totalMisses).toBe(0);
    expect(metrics.hitRate).toBe(1);
  });

  it('returns null for expired entry and increments miss count', () => {
    const cache = useRouteCache();
    const DashboardPage = () => null;

    cache.set('dashboard', DashboardPage, 100);
    vi.advanceTimersByTime(101);

    expect(cache.get('dashboard')).toBeNull();

    const metrics = cache.getMetrics();
    expect(metrics.size).toBe(0);
    expect(metrics.totalMisses).toBe(1);
    expect(metrics.hitRate).toBe(0);
  });

  it('supports delete, clear and cleanup', () => {
    const cache = useRouteCache();
    const PageA = () => null;
    const PageB = () => null;

    cache.set('a', PageA, 1000);
    cache.set('b', PageB, 50);

    expect(cache.delete('a')).toBe(true);
    expect(cache.get('a')).toBeNull();

    vi.advanceTimersByTime(51);
    expect(cache.cleanup()).toBe(1);

    cache.clear();
    expect(cache.getMetrics().size).toBe(0);
  });

  it('preloads route once and reuses cache on repeated calls', async () => {
    const state = useRouteCacheState();
    const ContractPage = () => null;
    const loader = vi.fn(async () => ContractPage);

    const first = await state.preloadRoute('contract', loader);
    const second = await state.preloadRoute('contract', loader);

    expect(first).toBe(ContractPage);
    expect(second).toBe(ContractPage);
    expect(loader).toHaveBeenCalledTimes(1);

    const metrics = state.getMetrics();
    expect(metrics.size).toBe(1);
    expect(metrics.totalHits).toBe(1);
  });

  it('rethrows preload errors', async () => {
    const state = useRouteCacheState();
    const loader = vi.fn(async () => {
      throw new Error('preload failed');
    });
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      await expect(state.preloadRoute('broken', loader)).rejects.toThrow('preload failed');
      expect(loader).toHaveBeenCalledTimes(1);
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining('[ERROR] [RouteCache] Failed to preload route: broken'),
        expect.objectContaining({
          error: 'preload failed',
        })
      );
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain(
        'Failed to preload route: broken'
      );
    } finally {
      consoleErrorSpy.mockRestore();
      stderrWriteSpy.mockRestore();
    }
  });

  it('starts cleanup timer once and stops it explicitly', () => {
    stopRouteCacheCleanup();
    const intervalSpy = vi.spyOn(globalThis, 'setInterval');
    const clearSpy = vi.spyOn(globalThis, 'clearInterval');

    useRouteCache();
    useRouteCache();
    stopRouteCacheCleanup();

    expect(intervalSpy).toHaveBeenCalledTimes(1);
    expect(clearSpy).toHaveBeenCalledTimes(1);
  });
});

describe('RoutePerformanceMonitor', () => {
  it('records load metrics and calculates error rate', () => {
    const monitor = new RoutePerformanceMonitor();

    monitor.recordLoadTime('assets', 100);
    monitor.recordLoadTime('assets', 300);
    monitor.recordError('assets');
    monitor.recordError('errors-only');

    const metrics = monitor.getMetrics();

    expect(metrics.assets?.hitCount).toBe(2);
    expect(metrics.assets?.averageLoadTime).toBe(175);
    expect(metrics.assets?.errorCount).toBe(1);
    expect(metrics.assets?.errorRate).toBe(0.5);

    expect(metrics['errors-only']?.errorCount).toBe(1);
    expect(metrics['errors-only']?.errorRate).toBe(0);

    monitor.clear();
    expect(monitor.getMetrics()).toEqual({});
  });
});
