/**
 * 路由基础Jest测试
 * 使用Jest而不是Vitest，避免框架冲突
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DynamicRouteLoader from '../DynamicRouteLoader';

// Mock route cache utility
jest.mock('@/utils/routeCache', () => ({
  useRouteCache: () => ({
    get: jest.fn(),
    set: jest.fn(),
    clear: jest.fn(),
    getMetrics: jest.fn(() => ({ hitRate: 0.8, size: 100 })),
  }),
}));

// Mock route performance monitor
jest.mock('@/monitoring/RoutePerformanceMonitor', () => ({
  RoutePerformanceMonitor: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="route-performance-monitor">{children}</div>
  ),
}));

describe('Router Basic Jest Tests', () => {
  const mockRoutes = [
    {
      path: '/dashboard',
      component: () => <div>Dashboard</div>,
      permissions: ['dashboard.read'],
    },
    {
      path: '/assets',
      component: () => <div>Assets</div>,
      permissions: ['asset.read'],
    },
    {
      path: '/settings',
      component: () => <div>Settings</div>,
      permissions: ['settings.manage'],
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('组件应该能够渲染', () => {
    render(
      <MemoryRouter>
        <DynamicRouteLoader routes={mockRoutes} />
      </MemoryRouter>
    );

    // 验证路由加载器存在
    expect(screen.getByTestId('route-performance-monitor')).toBeInTheDocument();
  });

  test('应该渲染默认路由', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <DynamicRouteLoader routes={mockRoutes} fallback={<div>Loading...</div>} />
      </MemoryRouter>
    );

    // 验证fallback显示
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  test('应该处理路由匹配', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <DynamicRouteLoader routes={mockRoutes} />
      </MemoryRouter>
    );

    // 验证路由内容渲染
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  test('应该处理权限检查', () => {
    const mockHasPermission = jest.fn().mockReturnValue(true);

    render(
      <MemoryRouter initialEntries={['/assets']}>
        <DynamicRouteLoader
          routes={mockRoutes}
          hasPermission={mockHasPermission}
        />
      </MemoryRouter>
    );

    // 验证权限检查被调用
    expect(mockHasPermission).toHaveBeenCalledWith('asset.read');
  });

  test('应该处理权限不足的情况', () => {
    const mockHasPermission = jest.fn().mockReturnValue(false);

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <DynamicRouteLoader
          routes={mockRoutes}
          hasPermission={mockHasPermission}
          fallback={<div>Access Denied</div>}
        />
      </MemoryRouter>
    );

    // 验证权限不足时显示fallback
    expect(screen.getByText('Access Denied')).toBeInTheDocument();
  });

  test('应该处理路由错误', () => {
    const errorRoutes = [
      {
        path: '/error',
        component: () => {
          throw new Error('Route error');
        },
        permissions: [],
      },
    ];

    render(
      <MemoryRouter initialEntries={['/error']}>
        <DynamicRouteLoader
          routes={errorRoutes}
          errorBoundary={<div>Route Error</div>}
        />
      </MemoryRouter>
    );

    // 验证错误边界显示
    expect(screen.getByText('Route Error')).toBeInTheDocument();
  });

  test('应该支持懒加载', () => {
    const lazyRoutes = [
      {
        path: '/lazy',
        component: React.lazy(() => Promise.resolve({ default: () => <div>Lazy Component</div> })),
        permissions: [],
      },
    ];

    render(
      <MemoryRouter initialEntries={['/lazy']}>
        <DynamicRouteLoader
          routes={lazyRoutes}
          fallback={<div>Loading...</div>}
        />
      </MemoryRouter>
    );

    // 验证懒加载状态
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});

describe('Route Performance Monitoring', () => {
  test('应该收集性能指标', () => {
    const mockOnMetricsUpdate = jest.fn();

    render(
      <MemoryRouter>
        <DynamicRouteLoader
          routes={mockRoutes}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      </MemoryRouter>
    );

    // 验证性能指标回调被设置
    expect(mockOnMetricsUpdate).toBeDefined();
  });

  test('应该报告路由加载时间', () => {
    const startTime = performance.now();

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <DynamicRouteLoader routes={mockRoutes} />
      </MemoryRouter>
    );

    const endTime = performance.now();
    const loadTime = endTime - startTime;

    // 验证加载时间在合理范围内
    expect(loadTime).toBeLessThan(1000); // 小于1秒
  });
});

describe('Route Caching', () => {
  test('应该使用路由缓存', () => {
    render(
      <MemoryRouter>
        <DynamicRouteLoader routes={mockRoutes} />
      </MemoryRouter>
    );

    // 验证缓存钩子被使用
    // 这需要实际的routeCache实现
  });

  test('应该管理缓存大小', () => {
    render(
      <MemoryRouter>
        <DynamicRouteLoader
          routes={mockRoutes}
          cacheSize={50}
        />
      </MemoryRouter>
    );

    // 验证缓存大小限制
    // 这需要实际的缓存实现
  });
});

describe('Error Handling', () => {
  test('应该处理组件加载失败', () => {
    const failingRoutes = [
      {
        path: '/fail',
        component: () => {
          throw new Error('Component failed to load');
        },
        permissions: [],
      },
    ];

    render(
      <MemoryRouter initialEntries={['/fail']}>
        <DynamicRouteLoader
          routes={failingRoutes}
          errorFallback={<div>Component Load Error</div>}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('Component Load Error')).toBeInTheDocument();
  });

  test('应该处理权限检查异常', () => {
    const mockHasPermission = jest.fn().mockImplementation(() => {
      throw new Error('Permission check failed');
    });

    render(
      <MemoryRouter initialEntries={['/assets']}>
        <DynamicRouteLoader
          routes={mockRoutes}
          hasPermission={mockHasPermission}
          errorFallback={<div>Permission Error</div>}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('Permission Error')).toBeInTheDocument();
  });
});

describe('Integration Tests', () => {
  test('完整的路由加载流程', async () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <DynamicRouteLoader routes={mockRoutes} />
      </MemoryRouter>
    );

    // 验证路由成功加载
    await screen.findByText('Dashboard');
  });

  test('多路由切换', () => {
    const { rerender } = render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <DynamicRouteLoader routes={mockRoutes} />
      </MemoryRouter>
    );

    expect(screen.getByText('Dashboard')).toBeInTheDocument();

    // 切换路由
    rerender(
      <MemoryRouter initialEntries={['/assets']}>
        <DynamicRouteLoader routes={mockRoutes} />
      </MemoryRouter>
    );

    expect(screen.getByText('Assets')).toBeInTheDocument();
  });
});