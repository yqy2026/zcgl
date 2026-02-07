/**
 * RouteBuilder 组件测试
 * 覆盖路由构建与重定向逻辑
 */

import { describe, it, expect } from 'vitest';
import React from 'react';
import { screen } from '@/test/utils/test-helpers';
import type { ReactNode } from 'react';

import RouteBuilder, { AssetRoutes, SystemRoutes } from '../RouteBuilder';
import { PERMISSIONS } from '@/hooks/usePermission';

interface RouteMockProps {
  path?: string;
  element?: ReactNode;
  children?: ReactNode;
}

vi.mock('../ProtectedRoute', () => ({
  default: ({
    path,
    title,
    permissions,
  }: {
    path?: string;
    title?: string;
    permissions?: unknown;
  }) => (
    <div
      data-testid="protected-route"
      data-path={path}
      data-title={title}
      data-permissions={permissions ? JSON.stringify(permissions) : 'none'}
    >
      Protected Route
    </div>
  ),
}));

vi.mock('../LazyRoute', () => ({
  default: ({
    path,
    preload,
    permissions,
  }: {
    path?: string;
    preload?: () => void;
    permissions?: unknown;
  }) => (
    <div
      data-testid="lazy-route"
      data-path={path}
      data-has-preload={!!preload}
      data-permissions={permissions ? JSON.stringify(permissions) : 'none'}
    >
      Lazy Route
    </div>
  ),
}));

vi.mock('react-router-dom', () => ({
  Navigate: ({ to, replace }: { to: string; replace?: boolean }) => (
    <div data-testid="navigate" data-to={to} data-replace={replace} />
  ),
  Route: ({ path, element, children }: RouteMockProps) => (
    <div
      data-testid="route"
      data-path={path}
      data-has-children={!!children}
      data-has-element={!!element}
    >
      {children ?? element}
    </div>
  ),
}));

describe('RouteBuilder', () => {
  it('buildRoute uses ProtectedRoute for non-lazy routes', () => {
    const TestComponent = () => <div>Dashboard</div>;

    const element = RouteBuilder.buildRoute({
      path: '/dashboard',
      title: '工作台',
      component: TestComponent,
    });

    renderWithProviders(element);

    const protectedRoute = screen.getByTestId('protected-route');
    expect(protectedRoute).toHaveAttribute('data-path', '/dashboard');
  });

  it('buildRoute uses LazyRoute for lazy routes', () => {
    const TestComponent = React.lazy(async () => ({
      default: () => <div>Lazy Page</div>,
    }));

    const element = RouteBuilder.buildRoute({
      path: '/lazy',
      title: '懒加载页面',
      component: TestComponent,
      lazy: true,
    });

    renderWithProviders(element);

    expect(screen.getByTestId('lazy-route')).toHaveAttribute('data-path', '/lazy');
  });

  it('buildRoute uses Route when element is provided', () => {
    const element = RouteBuilder.buildRoute({
      path: '/custom',
      title: '自定义',
      element: <div data-testid="custom-element">Custom</div>,
    });

    renderWithProviders(element);

    expect(screen.getByTestId('route')).toHaveAttribute('data-has-element', 'true');
    expect(screen.getByTestId('custom-element')).toBeInTheDocument();
  });

  it('buildRoute creates container route when only children provided', () => {
    const ChildComponent = () => <div>Child</div>;

    const element = RouteBuilder.buildRoute({
      path: '/parent',
      title: '父级',
      children: [
        {
          path: '/child',
          title: '子级',
          component: ChildComponent,
        },
      ],
    });

    renderWithProviders(element);

    expect(screen.getByTestId('route')).toHaveAttribute('data-has-children', 'true');
    expect(screen.getByTestId('protected-route')).toHaveAttribute('data-path', '/child');
  });

  it('buildRoute redirects when no component and no children', () => {
    const element = RouteBuilder.buildRoute({
      path: '/orphan',
      title: '孤立',
    });

    renderWithProviders(element);

    expect(screen.getByTestId('navigate')).toHaveAttribute('data-to', '/');
  });

  it('buildRoutes renders multiple routes', () => {
    const ComponentA = () => <div>A</div>;
    const ComponentB = () => <div>B</div>;

    const elements = RouteBuilder.buildRoutes([
      { path: '/a', title: 'A', component: ComponentA },
      { path: '/b', title: 'B', component: ComponentB },
    ]);

    renderWithProviders(<>{elements}</>);

    expect(screen.getAllByTestId('protected-route')).toHaveLength(2);
  });

  it('createRedirect produces navigate element', () => {
    renderWithProviders(RouteBuilder.createRedirect('/old', '/new', true));

    expect(screen.getByTestId('navigate')).toHaveAttribute('data-to', '/new');
  });

  it('createProtectedRoute passes permissions', () => {
    const TestComponent = () => <div>Protected</div>;

    renderWithProviders(
      RouteBuilder.createProtectedRoute('/protected', TestComponent, 'ASSET_VIEW', '资产查看')
    );

    expect(screen.getByTestId('protected-route')).toHaveAttribute(
      'data-permissions',
      JSON.stringify([PERMISSIONS.ASSET_VIEW])
    );
  });

  it('createLazyRoute uses LazyRoute with permissions', () => {
    const TestComponent = React.lazy(async () => ({
      default: () => <div>Lazy</div>,
    }));

    renderWithProviders(
      RouteBuilder.createLazyRoute('/lazy', TestComponent, {
        title: '懒加载页面',
        permissions: [PERMISSIONS.ASSET_VIEW],
      })
    );

    expect(screen.getByTestId('lazy-route')).toHaveAttribute(
      'data-permissions',
      JSON.stringify([PERMISSIONS.ASSET_VIEW])
    );
  });

  it('AssetRoutes/SystemRoutes produce protected routes', () => {
    const TestComponent = () => <div>Page</div>;

    renderWithProviders(
      <>
        {AssetRoutes.list(TestComponent)}
        {SystemRoutes.roles(TestComponent)}
      </>
    );

    const protectedRoutes = screen.getAllByTestId('protected-route');
    expect(protectedRoutes.length).toBeGreaterThanOrEqual(2);
  });
});
