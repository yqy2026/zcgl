/**
 * ProtectedRoute 组件测试
 * 覆盖权限守卫与错误边界渲染
 */

import { describe, it, expect } from 'vitest';
import { screen } from '@/test/utils/test-helpers';
import type { ReactNode } from 'react';

import ProtectedRoute from '../ProtectedRoute';

interface PermissionMock {
  resource: string;
  action: string;
}

interface PermissionGuardMockProps {
  children: ReactNode;
  fallback?: ReactNode;
  mode?: string;
  permissions?: PermissionMock[];
}

vi.mock('react-router-dom', () => ({
  Route: ({ element }: { element?: ReactNode }) => (
    <div data-testid="route">{element}</div>
  ),
}));

vi.mock('@/components/ErrorHandling', () => ({
  SystemErrorBoundary: ({ children }: { children: ReactNode }) => (
    <div data-testid="error-boundary">{children}</div>
  ),
}));

vi.mock('@/components/System/PermissionGuard', () => ({
  PermissionGuard: ({ children, fallback, mode, permissions }: PermissionGuardMockProps) => (
    <div
      data-testid="permission-guard"
      data-mode={mode || 'any'}
      data-permissions={permissions ? JSON.stringify(permissions) : 'none'}
    >
      {fallback ?? children}
    </div>
  ),
}));

describe('ProtectedRoute', () => {
  it('renders component inside error boundary by default', () => {
    const TestComponent = () => <div data-testid="content">Protected Content</div>;

    renderWithProviders(
      <ProtectedRoute
        path="/test"
        title="测试路由"
        component={TestComponent}
      />
    );

    expect(screen.getByTestId('route')).toBeInTheDocument();
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('content')).toBeInTheDocument();
    expect(screen.queryByTestId('permission-guard')).toBeNull();
  });

  it('wraps with PermissionGuard when permissions provided', () => {
    const TestComponent = () => <div data-testid="content">Protected Content</div>;
    const permissions = [{ resource: 'asset', action: 'view' }];

    renderWithProviders(
      <ProtectedRoute
        path="/test"
        title="测试路由"
        component={TestComponent}
        permissions={permissions}
      />
    );

    const guard = screen.getByTestId('permission-guard');
    expect(guard).toHaveAttribute('data-permissions', JSON.stringify(permissions));
    expect(screen.getByTestId('content')).toBeInTheDocument();
  });

  it('renders fallback when permission guard denies', () => {
    const TestComponent = () => <div>Protected Content</div>;

    renderWithProviders(
      <ProtectedRoute
        path="/test"
        title="测试路由"
        component={TestComponent}
        permissions={[{ resource: 'asset', action: 'edit' }]}
        fallback={<div data-testid="fallback">Access Denied</div>}
      />
    );

    expect(screen.getByTestId('fallback')).toBeInTheDocument();
  });

  it('skips error boundary when disabled', () => {
    const TestComponent = () => <div data-testid="content">Content</div>;

    renderWithProviders(
      <ProtectedRoute
        path="/test"
        title="测试路由"
        component={TestComponent}
        errorBoundary={false}
      />
    );

    expect(screen.queryByTestId('error-boundary')).toBeNull();
    expect(screen.getByTestId('content')).toBeInTheDocument();
  });

  it('treats empty permissions as public route', () => {
    const TestComponent = () => <div data-testid="content">Public Content</div>;

    renderWithProviders(
      <ProtectedRoute
        path="/public"
        title="公共路由"
        component={TestComponent}
        permissions={[]}
      />
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
    expect(screen.queryByTestId('permission-guard')).toBeNull();
  });
});
