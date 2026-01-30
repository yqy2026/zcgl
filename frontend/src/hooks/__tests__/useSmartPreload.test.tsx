/**
 * useSmartPreload Hook 测试
 * 测试智能预加载功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useLocation: vi.fn(() => ({ pathname: '/dashboard' })),
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  createLogger: vi.fn(() => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  })),
}));

// Mock dynamic imports
vi.mock('../pages/Dashboard/DashboardPage', () => ({
  default: vi.fn(),
}));

vi.mock('../pages/Assets/AssetListPage', () => ({
  default: vi.fn(),
}));

describe('useSmartPreload - 基础功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该能够导入 Hook', async () => {
    const module = await import('../useSmartPreload');
    expect(module).toBeDefined();
    expect(module.useSmartPreload).toBeDefined();
  });

  it('应该导出 withPreload HOC', async () => {
    const module = await import('../useSmartPreload');
    expect(module.withPreload).toBeDefined();
    expect(typeof module.withPreload).toBe('function');
  });

  it('应该导出 usePreloadDirective', async () => {
    const module = await import('../useSmartPreload');
    expect(module.usePreloadDirective).toBeDefined();
    expect(typeof module.usePreloadDirective).toBe('function');
  });

  it('应该导出 usePreloadDebug', async () => {
    const module = await import('../useSmartPreload');
    expect(module.usePreloadDebug).toBeDefined();
    expect(typeof module.usePreloadDebug).toBe('function');
  });

  it('应该导出 SmartPreloadManager 类', async () => {
    const module = await import('../useSmartPreload');
    expect(module.default).toBeDefined();
  });
});

describe('useSmartPreload - Hook 返回值测试', () => {
  it('应该返回 preloadRoute 函数', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(), { wrapper });

    expect(result.current.preloadRoute).toBeDefined();
    expect(typeof result.current.preloadRoute).toBe('function');
  });

  it('应该返回 getStats 函数', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(), { wrapper });

    expect(result.current.getStats).toBeDefined();
    expect(typeof result.current.getStats).toBe('function');
  });

  it('应该返回 clearCache 函数', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(), { wrapper });

    expect(result.current.clearCache).toBeDefined();
    expect(typeof result.current.clearCache).toBe('function');
  });

  it('应该返回 config 对象', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(), { wrapper });

    expect(result.current.config).toBeDefined();
    expect(result.current.config.threshold).toBeDefined();
    expect(result.current.config.maxConcurrent).toBeDefined();
  });
});

describe('useSmartPreload - 配置测试', () => {
  it('应该使用默认配置', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(), { wrapper });

    expect(result.current.config.threshold).toBe(200);
    expect(result.current.config.maxConcurrent).toBe(3);
  });

  it('应该支持自定义配置', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const customConfig = {
      threshold: 500,
      maxConcurrent: 5,
    };

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(customConfig), { wrapper });

    expect(result.current.config.threshold).toBe(500);
    expect(result.current.config.maxConcurrent).toBe(5);
  });
});

describe('useSmartPreload - 统计功能测试', () => {
  it('getStats 应该返回缓存统计', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(), { wrapper });

    const stats = result.current.getStats();

    if (stats !== null) {
      expect(stats).toHaveProperty('cachedRoutes');
      expect(stats).toHaveProperty('activePreloads');
      expect(stats).toHaveProperty('visitedRoutes');
      expect(stats).toHaveProperty('interactionCount');
    }
  });
});

describe('useSmartPreload - 缓存操作测试', () => {
  it('clearCache 应该清空缓存', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(), { wrapper });

    act(() => {
      result.current.clearCache();
    });

    const stats = result.current.getStats();
    if (stats !== null) {
      expect(stats.cachedRoutes).toBe(0);
    }
  });
});

describe('useSmartPreload - 预加载路由测试', () => {
  it('preloadRoute 应该能被调用', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(), { wrapper });

    expect(() => {
      act(() => {
        result.current.preloadRoute('/dashboard');
      });
    }).not.toThrow();
  });

  it('preloadRoute 应该处理未知路由', async () => {
    const { useSmartPreload } = await import('../useSmartPreload');

    const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;
    const { result } = renderHook(() => useSmartPreload(), { wrapper });

    expect(() => {
      act(() => {
        result.current.preloadRoute('/unknown-route');
      });
    }).not.toThrow();
  });
});

describe('SmartPreloadManager - 类测试', () => {
  it('应该能够实例化', async () => {
    const SmartPreloadManager = (await import('../useSmartPreload')).default;

    const manager = new SmartPreloadManager();
    expect(manager).toBeDefined();
  });

  it('应该支持自定义配置实例化', async () => {
    const SmartPreloadManager = (await import('../useSmartPreload')).default;

    const manager = new SmartPreloadManager({
      threshold: 300,
      maxConcurrent: 4,
    });
    expect(manager).toBeDefined();
  });

  it('应该有 getCacheStats 方法', async () => {
    const SmartPreloadManager = (await import('../useSmartPreload')).default;

    const manager = new SmartPreloadManager();
    expect(manager.getCacheStats).toBeDefined();
    expect(typeof manager.getCacheStats).toBe('function');
  });

  it('应该有 clearCache 方法', async () => {
    const SmartPreloadManager = (await import('../useSmartPreload')).default;

    const manager = new SmartPreloadManager();
    expect(manager.clearCache).toBeDefined();
    expect(typeof manager.clearCache).toBe('function');
  });

  it('应该有 destroy 方法', async () => {
    const SmartPreloadManager = (await import('../useSmartPreload')).default;

    const manager = new SmartPreloadManager();
    expect(manager.destroy).toBeDefined();
    expect(typeof manager.destroy).toBe('function');
  });

  it('应该有 updateCurrentRoute 方法', async () => {
    const SmartPreloadManager = (await import('../useSmartPreload')).default;

    const manager = new SmartPreloadManager();
    expect(manager.updateCurrentRoute).toBeDefined();
    expect(typeof manager.updateCurrentRoute).toBe('function');
  });

  it('应该有 preloadRoute 方法', async () => {
    const SmartPreloadManager = (await import('../useSmartPreload')).default;

    const manager = new SmartPreloadManager();
    expect(manager.preloadRoute).toBeDefined();
    expect(typeof manager.preloadRoute).toBe('function');
  });
});
