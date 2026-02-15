import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  BatchRequestOptimizer,
  DataCache,
  DataPreloader,
  batchOptimizer,
  createCachedRequest,
} from '../dataCache';

describe('DataCache', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00.000Z'));
  });

  afterEach(() => {
    batchOptimizer.clear();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('supports set/get/has and removes expired entries', () => {
    const cache = new DataCache({ ttl: 1000, maxSize: 10 });

    cache.set('asset-list', [{ id: 1 }], 100);

    expect(cache.has('asset-list')).toBe(true);
    expect(cache.get<Array<{ id: number }>>('asset-list')).toEqual([{ id: 1 }]);

    vi.advanceTimersByTime(101);

    expect(cache.has('asset-list')).toBe(false);
    expect(cache.get<Array<{ id: number }>>('asset-list')).toBeNull();
  });

  it('evicts oldest entry when maxSize is reached', () => {
    const cache = new DataCache({ maxSize: 2, ttl: 1000 });

    cache.set('a', 1);
    vi.advanceTimersByTime(1);
    cache.set('b', 2);
    vi.advanceTimersByTime(1);
    cache.set('c', 3);

    expect(cache.get<number>('a')).toBeNull();
    expect(cache.get<number>('b')).toBe(2);
    expect(cache.get<number>('c')).toBe(3);
  });

  it('cleans up expired entries and reports stats', () => {
    const cache = new DataCache({ ttl: 1000, maxSize: 10 });

    cache.set('active', 'v1', 5000);
    cache.set('expired', 'v2', 100);
    vi.advanceTimersByTime(150);

    const deleted = cache.cleanup();
    const stats = cache.getStats();

    expect(deleted).toBe(1);
    expect(stats.size).toBe(1);
    expect(stats.maxSize).toBe(10);
    expect(stats.entries[0]?.key).toBe('active');
    expect(stats.entries[0]?.expired).toBe(false);
  });

  it('supports delete and clear', () => {
    const cache = new DataCache({ ttl: 1000, maxSize: 10 });
    cache.set('k1', 'v1');
    cache.set('k2', 'v2');

    expect(cache.delete('k1')).toBe(true);
    expect(cache.get<string>('k1')).toBeNull();

    cache.clear();
    expect(cache.getStats().size).toBe(0);
  });
});

describe('BatchRequestOptimizer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('deduplicates in-flight requests with the same key', async () => {
    const optimizer = new BatchRequestOptimizer();
    const requestFn = vi.fn(async () => ({ ok: true }));

    const first = optimizer.batchRequest('assets', requestFn, { delay: 20 });
    const second = optimizer.batchRequest('assets', requestFn, { delay: 20 });

    await vi.advanceTimersByTimeAsync(21);
    const [r1, r2] = await Promise.all([first, second]);

    expect(r1).toEqual({ ok: true });
    expect(r2).toEqual({ ok: true });
    expect(requestFn).toHaveBeenCalledTimes(1);
  });

  it('uses custom batchKey for dedupe across different keys', async () => {
    const optimizer = new BatchRequestOptimizer();
    const requestFn = vi.fn(async () => 'done');

    const first = optimizer.batchRequest('a', requestFn, { batchKey: 'shared', delay: 1 });
    const second = optimizer.batchRequest('b', requestFn, { batchKey: 'shared', delay: 1 });

    await vi.advanceTimersByTimeAsync(2);
    const [r1, r2] = await Promise.all([first, second]);

    expect(r1).toBe('done');
    expect(r2).toBe('done');
    expect(requestFn).toHaveBeenCalledTimes(1);
  });
});

describe('DataPreloader', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('preloads immediately in priority mode', async () => {
    const preloader = new DataPreloader();
    const first = vi.fn(async () => 'a');
    const second = vi.fn(async () => 'b');

    preloader.addToPreload(first);
    preloader.addToPreload(second);

    await preloader.preload(true);

    expect(first).toHaveBeenCalledTimes(1);
    expect(second).toHaveBeenCalledTimes(1);
  });

  it('uses requestIdleCallback in non-priority mode when available', async () => {
    const preloader = new DataPreloader();
    const idleCallbackSpy = vi.fn((callback: IdleRequestCallback) => {
      callback({ didTimeout: false, timeRemaining: () => 16 } as IdleDeadline);
      return 1;
    });

    const globalWithIdle = globalThis as typeof globalThis & {
      requestIdleCallback?: (callback: IdleRequestCallback) => number;
    };
    globalWithIdle.requestIdleCallback = idleCallbackSpy;

    const task = vi.fn(async () => 'ok');
    preloader.addToPreload(task);

    await preloader.preload(false);
    await Promise.resolve();

    expect(idleCallbackSpy).toHaveBeenCalledTimes(1);
    expect(task).toHaveBeenCalledTimes(1);

    delete globalWithIdle.requestIdleCallback;
  });

  it('falls back to setTimeout when requestIdleCallback is unavailable', async () => {
    vi.useFakeTimers();

    const preloader = new DataPreloader();
    const globalWithIdle = globalThis as typeof globalThis & {
      requestIdleCallback?: (callback: IdleRequestCallback) => number;
    };
    delete globalWithIdle.requestIdleCallback;

    const task = vi.fn(async () => 'ok');
    preloader.addToPreload(task);

    await preloader.preload(false);
    expect(task).toHaveBeenCalledTimes(0);

    await vi.advanceTimersByTimeAsync(1000);
    expect(task).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it('handles preload errors without throwing', async () => {
    const preloader = new DataPreloader();
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const task = vi.fn(async () => {
      throw new Error('load failed');
    });
    preloader.addToPreload(task);

    await expect(preloader.preload(true)).resolves.toBeUndefined();
    expect(warnSpy).toHaveBeenCalledWith('Data preloading failed:', expect.any(Error));
  });
});

describe('createCachedRequest', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    batchOptimizer.clear();
  });

  afterEach(() => {
    batchOptimizer.clear();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('returns cached value on repeated calls without params', async () => {
    const cache = new DataCache({ ttl: 1000, maxSize: 10 });
    const requestFn = vi.fn(async () => ({ total: 2 }));
    const getAssets = createCachedRequest('assets', requestFn, cache, 1000);

    const first = getAssets();
    await vi.advanceTimersByTimeAsync(51);
    await first;

    const second = await getAssets();

    expect(second).toEqual({ total: 2 });
    expect(requestFn).toHaveBeenCalledTimes(1);
  });

  it('deduplicates concurrent calls with same params via batchOptimizer', async () => {
    const cache = new DataCache({ ttl: 1000, maxSize: 10 });
    const requestFn = vi.fn(async () => ({ id: 1 }));
    const getByFilter = createCachedRequest('asset-filter', requestFn, cache, 1000);

    const p1 = getByFilter({ status: 'active' });
    const p2 = getByFilter({ status: 'active' });

    await vi.advanceTimersByTimeAsync(51);
    const [r1, r2] = await Promise.all([p1, p2]);

    expect(r1).toEqual({ id: 1 });
    expect(r2).toEqual({ id: 1 });
    expect(requestFn).toHaveBeenCalledTimes(1);
  });
});
