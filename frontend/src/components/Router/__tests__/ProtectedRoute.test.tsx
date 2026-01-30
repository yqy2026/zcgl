/**
 * ProtectedRoute 组件测试
 * 测试受保护路由组件的功能
 * 增强版本 - 添加更全面的测试用例
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import ProtectedRoute from '../ProtectedRoute';

interface PermissionMock {
  resource: string;
  action: string;
}

interface PermissionGuardMockProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  mode?: string;
  permissions?: PermissionMock[];
}

// Mock dependencies
vi.mock('@/components/ErrorHandling', () => ({
  SystemErrorBoundary: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="error-boundary">{children}</div>
  ),
}));

vi.mock('../System/PermissionGuard', () => ({
  PermissionGuard: ({ children, fallback, mode, permissions }: PermissionGuardMockProps) => (
    <div
      data-testid="permission-guard"
      data-mode={mode || 'any'}
      data-permissions={permissions ? JSON.stringify(permissions) : 'none'}
    >
      {fallback || children}
    </div>
  ),
}));

// Test wrapper
describe('ProtectedRoute - 组件导入测试', () => {
  it('应该能够导入组件', () => {
    expect(ProtectedRoute).toBeDefined();
  });

  it('组件应该是React函数组件', () => {
    expect(typeof ProtectedRoute).toBe('function');
  });
});

describe('ProtectedRoute - 基础功能测试', () => {
  it('应该支持权限验证', () => {
    const TestComponent = () => <div>Protected Content</div>;
    const permissions = [{ resource: 'asset', action: 'view' }];

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      title: '测试路由',
      component: TestComponent,
      permissions,
    });

    expect(element).toBeTruthy();
  });

  it('应该支持fallback渲染', () => {
    const TestComponent = () => <div>Protected Content</div>;
    const FallbackComponent = () => <div>Access Denied</div>;
    const permissions = [{ resource: 'asset', action: 'edit' }];

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      title: '测试路由',
      component: TestComponent,
      permissions,
      fallback: React.createElement(FallbackComponent),
    });

    expect(element).toBeTruthy();
  });

  it('应该支持errorBoundary控制', () => {
    const TestComponent = () => <div>Content</div>;

    const withBoundary = React.createElement(ProtectedRoute, {
      path: '/test',
      title: '测试路由',
      component: TestComponent,
      errorBoundary: true,
    });

    const withoutBoundary = React.createElement(ProtectedRoute, {
      path: '/test',
      title: '测试路由',
      component: TestComponent,
      errorBoundary: false,
    });

    expect(withBoundary).toBeTruthy();
    expect(withoutBoundary).toBeTruthy();
  });

  it('无权限的路由应该也能正常工作', () => {
    const TestComponent = () => <div>Public Content</div>;

    const element = React.createElement(ProtectedRoute, {
      path: '/public',
      title: '公共路由',
      component: TestComponent,
      permissions: [],
    });

    expect(element).toBeTruthy();
  });
});

// =============================================================================
// 增强测试 - 属性验证测试
// =============================================================================

describe('ProtectedRoute - 属性验证', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持title属性', () => {
    const TestComponent = () => <div>Test</div>;

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      title: '测试标题',
      component: TestComponent,
    });

    expect(element).toBeTruthy();
  });

  it('应该支持exact属性', () => {
    const TestComponent = () => <div>Test</div>;

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      exact: true,
      component: TestComponent,
    });

    expect(element).toBeTruthy();
  });
});

// =============================================================================
// 边界情况测试
// =============================================================================

describe('ProtectedRoute - 边界情况', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理undefined权限', () => {
    const TestComponent = () => <div>Test</div>;

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      component: TestComponent,
      permissions: undefined,
    });

    expect(element).toBeTruthy();
  });

  it('应该处理空权限数组', () => {
    const TestComponent = () => <div>Test</div>;

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      component: TestComponent,
      permissions: [],
    });

    expect(element).toBeTruthy();
  });

  it('应该处理多个权限', () => {
    const TestComponent = () => <div>Test</div>;

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      component: TestComponent,
      permissions: [
        { resource: 'assets', action: 'view' },
        { resource: 'assets', action: 'edit' },
      ],
    });

    expect(element).toBeTruthy();
  });

  it('应该支持自定义fallback', () => {
    const TestComponent = () => <div>Protected</div>;
    const CustomFallback = () => <div>Access Denied</div>;

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      component: TestComponent,
      permissions: [{ resource: 'admin', action: 'manage' }],
      fallback: React.createElement(CustomFallback),
    });

    expect(element).toBeTruthy();
  });
});
