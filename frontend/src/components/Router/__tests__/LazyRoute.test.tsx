/**
 * LazyRoute 组件测试
 * 覆盖懒加载渲染、fallback 与权限守卫
 */

import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';

import LazyRoute from '../LazyRoute';

interface PermissionMock {
  resource: string;
  action: string;
}

interface PermissionGuardMockProps {
  children: ReactNode;
  permissions?: PermissionMock[];
}

vi.mock('react-router-dom', () => ({
  Route: ({ element }: { element?: ReactNode }) => (
    <div data-testid="route">{element}</div>
  ),
}));

vi.mock('@/components/Loading', () => ({
  SkeletonLoader: ({ type, rows }: { type: string; rows: number }) => (
    <div data-testid="skeleton" data-type={type} data-rows={rows}>
      Loading...
    </div>
  ),
}));

vi.mock('@/components/ErrorHandling', () => ({
  SystemErrorBoundary: ({ children }: { children: ReactNode }) => (
    <div data-testid="error-boundary">{children}</div>
  ),
}));

vi.mock('@/components/System/PermissionGuard', () => ({
  PermissionGuard: ({ children, permissions }: PermissionGuardMockProps) => (
    <div
      data-testid="permission-guard"
      data-permissions={permissions ? JSON.stringify(permissions) : 'none'}
    >
      {children}
    </div>
  ),
}));

describe('LazyRoute', () => {
  it('renders default fallback for pending lazy component', () => {
    const PendingComponent = React.lazy(
      () =>
        new Promise<{ default: React.ComponentType<Record<string, unknown>> }>(() => {})
    );

    render(
      <LazyRoute
        path="/test"
        title="测试路由"
        component={PendingComponent}
      />
    );

    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    const PendingComponent = React.lazy(
      () =>
        new Promise<{ default: React.ComponentType<Record<string, unknown>> }>(() => {})
    );

    render(
      <LazyRoute
        path="/test"
        title="测试路由"
        component={PendingComponent}
        fallback={<div data-testid="custom-fallback">Custom Loading</div>}
      />
    );

    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.queryByTestId('skeleton')).toBeNull();
  });

  it('renders lazy component when resolved', async () => {
    const ResolvedComponent = React.lazy(async () => ({
      default: () => <div data-testid="lazy-content">Lazy Content</div>,
    }));

    render(
      <LazyRoute
        path="/test"
        title="测试路由"
        component={ResolvedComponent}
      />
    );

    expect(await screen.findByTestId('lazy-content')).toBeInTheDocument();
  });

  it('wraps with PermissionGuard when permissions provided', async () => {
    const ResolvedComponent = React.lazy(async () => ({
      default: () => <div data-testid="lazy-content">Lazy Content</div>,
    }));
    const permissions = [{ resource: 'asset', action: 'view' }];

    render(
      <LazyRoute
        path="/test"
        title="测试路由"
        component={ResolvedComponent}
        permissions={permissions}
      />
    );

    const guard = screen.getByTestId('permission-guard');
    expect(guard).toHaveAttribute('data-permissions', JSON.stringify(permissions));
    expect(await screen.findByTestId('lazy-content')).toBeInTheDocument();
  });

  it('skips error boundary when disabled', async () => {
    const ResolvedComponent = React.lazy(async () => ({
      default: () => <div data-testid="lazy-content">Lazy Content</div>,
    }));

    render(
      <LazyRoute
        path="/test"
        title="测试路由"
        component={ResolvedComponent}
        errorBoundary={false}
      />
    );

    expect(await screen.findByTestId('lazy-content')).toBeInTheDocument();
    expect(screen.queryByTestId('error-boundary')).toBeNull();
  });

  it('treats empty permissions as public route', async () => {
    const ResolvedComponent = React.lazy(async () => ({
      default: () => <div data-testid="lazy-content">Lazy Content</div>,
    }));

    render(
      <LazyRoute
        path="/test"
        title="测试路由"
        component={ResolvedComponent}
        permissions={[]}
      />
    );

    expect(await screen.findByTestId('lazy-content')).toBeInTheDocument();
    expect(screen.queryByTestId('permission-guard')).toBeNull();
  });
});
