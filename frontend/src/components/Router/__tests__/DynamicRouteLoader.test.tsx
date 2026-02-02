/**
 * DynamicRouteLoader 组件测试
 * 测试动态路由加载器的核心功能
 */

import { describe, it, expect } from 'vitest';
import React from 'react';
import { screen } from '@/test/utils/test-helpers';
import { BrowserRouter } from 'react-router-dom';
import {
  DynamicRouteProvider,
  DynamicRouteRenderer,
  useDynamicRoute,
  RouteModuleLoader,
  usePermissionBasedRoutes,
} from '../DynamicRouteLoader';

vi.mock('@/pages/Dashboard/DashboardPage', () => ({
  default: () => <div>Dashboard Page</div>,
}));

describe('DynamicRouteLoader - 基础功能测试', () => {
  it('应该能够导入组件', () => {
    expect(DynamicRouteProvider).toBeDefined();
    expect(useDynamicRoute).toBeDefined();
  });

  it('DynamicRouteProvider应该正确渲染', () => {
    renderWithProviders(
      <DynamicRouteProvider>
        <div data-testid="test-child">Test Child</div>
      </DynamicRouteProvider>
    );

    expect(screen.getByTestId('test-child')).toHaveTextContent('Test Child');
  });
});

describe('DynamicRouteRenderer - 路由渲染测试', () => {
  it('应该在Router和Provider内正确渲染', async () => {
    renderWithProviders(
      <BrowserRouter>
        <DynamicRouteProvider>
          <DynamicRouteRenderer />
        </DynamicRouteProvider>
      </BrowserRouter>
    );

    const dashboard = await screen.findByText('Dashboard Page');
    expect(dashboard).toBeTruthy();
  });
});

describe('路由Hook测试', () => {
  it('useDynamicRoute应该在Provider内工作', () => {
    const TestComponent = () => {
      const context = useDynamicRoute();
      return <div data-testid="route-count">Routes: {context.routes.size}</div>;
    };

    renderWithProviders(
      <DynamicRouteProvider>
        <TestComponent />
      </DynamicRouteProvider>
    );

    expect(screen.getByTestId('route-count')).toBeTruthy();
  });

  it('useDynamicRoute应该在Provider外抛出错误', () => {
    const TestComponent = () => {
      try {
        useDynamicRoute();
        return <div>No Error</div>;
      } catch (error) {
        return <div data-testid="error-message">{(error as Error).message}</div>;
      }
    };

    renderWithProviders(<TestComponent />);
    expect(screen.getByTestId('error-message')).toHaveTextContent('useDynamicRoute must be used');
  });
});

describe('RouteModuleLoader - 模块加载测试', () => {
  it('应该在Provider内提供模块加载功能', () => {
    const TestComponent = () => {
      const { loading, loadedModules } = RouteModuleLoader();
      return (
        <div>
          <div data-testid="loading">{loading ? 'true' : 'false'}</div>
          <div data-testid="loaded-count">{loadedModules.length}</div>
        </div>
      );
    };

    renderWithProviders(
      <DynamicRouteProvider>
        <TestComponent />
      </DynamicRouteProvider>
    );

    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.getByTestId('loaded-count')).toHaveTextContent('0');
  });
});

describe('usePermissionBasedRoutes - 权限路由测试', () => {
  it('应该在Provider内提供权限路由加载功能', () => {
    const TestComponent = () => {
      const { availableRoutes } = usePermissionBasedRoutes();
      return <div data-testid="available-routes">Available Routes: {availableRoutes.length}</div>;
    };

    renderWithProviders(
      <DynamicRouteProvider>
        <TestComponent />
      </DynamicRouteProvider>
    );

    expect(screen.getByTestId('available-routes')).toBeTruthy();
  });
});
