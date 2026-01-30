/**
 * CacheManager 单元测试
 * 测试 API 缓存管理器的核心功能
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

// =============================================================================
// Mock CACHE config
// =============================================================================

vi.mock('../api/config', () => ({
  CACHE: {
    DEFAULT_TTL: 5 * 60 * 1000, // 5 minutes
  },
}));

// =============================================================================
// Test Suite
// =============================================================================

describe('ApiCacheManager', () => {
  let ApiCacheManager: typeof import('../cacheManager').ApiCacheManager;
  let cacheManager: import('../cacheManager').ApiCacheManager;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.clearAllMocks();

    // 重新导入以获取新实例
    vi.resetModules();
    const module = await import('../cacheManager');
    ApiCacheManager = module.ApiCacheManager;

    // 创建新实例用于测试
    const managerClass = ApiCacheManager as unknown as { instance: typeof cacheManager | null };
    managerClass.instance = null;
    cacheManager = ApiCacheManager.getInstance();
  });

  afterEach(() => {
    vi.useRealTimers();
    cacheManager.clear();
  });

  // =============================================================================
  // getInstance 测试
  // =============================================================================

  describe('getInstance', () => {
    it('should return singleton instance', () => {
      const instance1 = ApiCacheManager.getInstance();
      const instance2 = ApiCacheManager.getInstance();

      expect(instance1).toBe(instance2);
    });
  });

  // =============================================================================
  // set/get 测试
  // =============================================================================

  describe('set and get', () => {
    it('should store and retrieve data', () => {
      const testData = { id: 1, name: 'test' };

      cacheManager.set('/api/test', testData);
      const result = cacheManager.get<typeof testData>('/api/test');

      expect(result).toEqual(testData);
    });

    it('should store data with custom TTL', () => {
      const testData = { value: 'custom ttl' };

      cacheManager.set('/api/custom', testData, { ttl: 1000 });
      const result = cacheManager.get('/api/custom');

      expect(result).toEqual(testData);
    });

    it('should store data with params', () => {
      const testData1 = { page: 1 };
      const testData2 = { page: 2 };

      cacheManager.set('/api/list', testData1, {}, { page: 1 });
      cacheManager.set('/api/list', testData2, {}, { page: 2 });

      expect(cacheManager.get('/api/list', { page: 1 })).toEqual(testData1);
      expect(cacheManager.get('/api/list', { page: 2 })).toEqual(testData2);
    });

    it('should return null for non-existent key', () => {
      const result = cacheManager.get('/api/nonexistent');

      expect(result).toBeNull();
    });

    it('should return null for expired cache', () => {
      cacheManager.set('/api/expiring', { data: 'test' }, { ttl: 1000 });

      // 前进 1001ms
      vi.advanceTimersByTime(1001);

      const result = cacheManager.get('/api/expiring');

      expect(result).toBeNull();
    });

    it('should store data with tags', () => {
      cacheManager.set('/api/tagged', { data: 'tagged' }, { tags: ['assets', 'list'] });

      const result = cacheManager.get('/api/tagged');

      expect(result).toEqual({ data: 'tagged' });
    });
  });

  // =============================================================================
  // has 测试
  // =============================================================================

  describe('has', () => {
    it('should return true for existing cache', () => {
      cacheManager.set('/api/exists', { data: 'test' });

      expect(cacheManager.has('/api/exists')).toBe(true);
    });

    it('should return false for non-existent cache', () => {
      expect(cacheManager.has('/api/nonexistent')).toBe(false);
    });

    it('should return false for expired cache', () => {
      cacheManager.set('/api/expiring', { data: 'test' }, { ttl: 1000 });

      vi.advanceTimersByTime(1001);

      expect(cacheManager.has('/api/expiring')).toBe(false);
    });

    it('should check cache with params', () => {
      cacheManager.set('/api/list', { data: 'test' }, {}, { id: 1 });

      expect(cacheManager.has('/api/list', { id: 1 })).toBe(true);
      expect(cacheManager.has('/api/list', { id: 2 })).toBe(false);
    });
  });

  // =============================================================================
  // delete 测试
  // =============================================================================

  describe('delete', () => {
    it('should delete cache by key', () => {
      cacheManager.set('/api/delete', { data: 'test' });

      const deleted = cacheManager.delete('/api/delete');

      expect(deleted).toBe(true);
      expect(cacheManager.has('/api/delete')).toBe(false);
    });

    it('should return false when deleting non-existent key', () => {
      const deleted = cacheManager.delete('/api/nonexistent');

      expect(deleted).toBe(false);
    });

    it('should delete cache with params', () => {
      cacheManager.set('/api/list', { data: 'test' }, {}, { id: 1 });

      cacheManager.delete('/api/list', { id: 1 });

      expect(cacheManager.has('/api/list', { id: 1 })).toBe(false);
    });
  });

  // =============================================================================
  // deleteByTag 测试
  // =============================================================================

  describe('deleteByTag', () => {
    it('should delete all cache with specified tag', () => {
      cacheManager.set('/api/assets/1', { id: 1 }, { tags: ['assets'] });
      cacheManager.set('/api/assets/2', { id: 2 }, { tags: ['assets'] });
      cacheManager.set('/api/projects/1', { id: 1 }, { tags: ['projects'] });

      cacheManager.deleteByTag('assets');

      expect(cacheManager.has('/api/assets/1')).toBe(false);
      expect(cacheManager.has('/api/assets/2')).toBe(false);
      expect(cacheManager.has('/api/projects/1')).toBe(true);
    });

    it('should handle non-existent tag gracefully', () => {
      expect(() => cacheManager.deleteByTag('nonexistent')).not.toThrow();
    });
  });

  // =============================================================================
  // deleteByPattern 测试
  // =============================================================================

  describe('deleteByPattern', () => {
    it('should delete cache matching pattern', () => {
      cacheManager.set('/api/assets/1', { id: 1 });
      cacheManager.set('/api/assets/2', { id: 2 });
      cacheManager.set('/api/projects/1', { id: 1 });

      cacheManager.deleteByPattern(/\/api\/assets\//);

      expect(cacheManager.has('/api/assets/1')).toBe(false);
      expect(cacheManager.has('/api/assets/2')).toBe(false);
      expect(cacheManager.has('/api/projects/1')).toBe(true);
    });

    it('should handle no matches gracefully', () => {
      cacheManager.set('/api/test', { data: 'test' });

      expect(() => cacheManager.deleteByPattern(/\/nonexistent\//)).not.toThrow();
      expect(cacheManager.has('/api/test')).toBe(true);
    });
  });

  // =============================================================================
  // clear 测试
  // =============================================================================

  describe('clear', () => {
    it('should clear all cache', () => {
      cacheManager.set('/api/1', { data: 1 });
      cacheManager.set('/api/2', { data: 2 });
      cacheManager.set('/api/3', { data: 3 }, { tags: ['test'] });

      cacheManager.clear();

      expect(cacheManager.has('/api/1')).toBe(false);
      expect(cacheManager.has('/api/2')).toBe(false);
      expect(cacheManager.has('/api/3')).toBe(false);
    });
  });

  // =============================================================================
  // getStats 测试
  // =============================================================================

  describe('getStats', () => {
    it('should return correct statistics', () => {
      cacheManager.set('/api/1', { data: 'test1' }, { tags: ['tag1'] });
      cacheManager.set('/api/2', { data: 'test2' }, { tags: ['tag2'] });

      const stats = cacheManager.getStats();

      expect(stats.totalItems).toBe(2);
      expect(stats.tags).toBe(2);
      expect(stats.totalSize).toBeGreaterThan(0);
    });

    it('should return zero for empty cache', () => {
      const stats = cacheManager.getStats();

      expect(stats.totalItems).toBe(0);
      expect(stats.tags).toBe(0);
      expect(stats.totalSize).toBe(0);
    });
  });

  // =============================================================================
  // 自动清理测试
  // =============================================================================

  describe('automatic cleanup', () => {
    it('should cleanup expired items periodically', () => {
      cacheManager.set('/api/short', { data: 'short' }, { ttl: 30000 });
      cacheManager.set('/api/long', { data: 'long' }, { ttl: 120000 });

      expect(cacheManager.has('/api/short')).toBe(true);
      expect(cacheManager.has('/api/long')).toBe(true);

      // 前进 60 秒（触发清理）
      vi.advanceTimersByTime(60000);

      // short TTL 已过期
      expect(cacheManager.has('/api/short')).toBe(false);
      expect(cacheManager.has('/api/long')).toBe(true);
    });
  });

  // =============================================================================
  // warmup 测试
  // =============================================================================

  describe('warmup', () => {
    it('should accept warmup urls without error', async () => {
      await expect(
        cacheManager.warmup([{ url: '/api/test', params: { id: 1 } }])
      ).resolves.toBeUndefined();
    });
  });
});

// =============================================================================
// cached 装饰器测试
// =============================================================================

describe('cached decorator', () => {
  beforeEach(async () => {
    vi.resetModules();
  });

  it('should cache method results', async () => {
    const { cached, cacheManager } = await import('../cacheManager');

    class TestService {
      callCount = 0;

      @cached({ ttl: 60000 })
      async getData() {
        this.callCount++;
        return { data: 'test' };
      }
    }

    const service = new TestService();

    await service.getData();
    await service.getData();

    expect(service.callCount).toBe(1);

    cacheManager.clear();
  });

  it('should bypass cache when force is true', async () => {
    const { cached, cacheManager } = await import('../cacheManager');

    class TestService {
      callCount = 0;

      @cached({ force: true })
      async getData() {
        this.callCount++;
        return { data: 'test' };
      }
    }

    const service = new TestService();

    await service.getData();
    await service.getData();

    expect(service.callCount).toBe(2);

    cacheManager.clear();
  });
});

// =============================================================================
// invalidateCache 装饰器测试
// =============================================================================

describe('invalidateCache decorator', () => {
  it('should invalidate cache after method execution', async () => {
    const { cached, invalidateCache, cacheManager } = await import('../cacheManager');

    class TestService {
      @cached({ tags: ['items'] })
      async getItems() {
        return [{ id: 1 }];
      }

      @invalidateCache(['items'])
      async createItem() {
        return { id: 2 };
      }
    }

    const service = new TestService();

    // 先缓存数据
    await service.getItems();
    expect(cacheManager.getStats().totalItems).toBeGreaterThan(0);

    // 创建后应该清除缓存
    await service.createItem();

    cacheManager.clear();
  });
});
