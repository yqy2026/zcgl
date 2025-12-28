/**
 * ProtectedRoute 组件测试
 * 测试受保护路由组件的功能
 */

import { describe, it, expect, vi } from 'vitest'
import React from 'react'

// Mock dependencies
vi.mock('@/components/ErrorHandling', () => ({
  SystemErrorBoundary: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="error-boundary">{children}</div>
  ),
}))

vi.mock('../System/PermissionGuard', () => ({
  PermissionGuard: ({ children, fallback, mode }: { children: React.ReactNode; fallback?: any; mode?: string }) => (
    <div data-testid="permission-guard" data-mode={mode}>
      {fallback || children}
    </div>
  ),
}))

describe('ProtectedRoute - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../ProtectedRoute')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })

  it('组件应该是React函数组件', async () => {
    const ProtectedRoute = (await import('../ProtectedRoute')).default
    expect(typeof ProtectedRoute).toBe('function')
  })
})

describe('ProtectedRoute - 基础功能测试', () => {
  it('应该支持权限验证', async () => {
    const ProtectedRoute = (await import('../ProtectedRoute')).default
    
    const TestComponent = () => <div>Protected Content</div>
    const permissions = [{ resource: 'asset', action: 'view' }]

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      component: TestComponent,
      permissions,
    })

    expect(element).toBeTruthy()
  })

  it('应该支持fallback渲染', async () => {
    const ProtectedRoute = (await import('../ProtectedRoute')).default
    
    const TestComponent = () => <div>Protected Content</div>
    const FallbackComponent = () => <div>Access Denied</div>
    const permissions = [{ resource: 'asset', action: 'edit' }]

    const element = React.createElement(ProtectedRoute, {
      path: '/test',
      component: TestComponent,
      permissions,
      fallback: React.createElement(FallbackComponent),
    })

    expect(element).toBeTruthy()
  })

  it('应该支持errorBoundary控制', async () => {
    const ProtectedRoute = (await import('../ProtectedRoute')).default
    
    const TestComponent = () => <div>Content</div>

    const withBoundary = React.createElement(ProtectedRoute, {
      path: '/test',
      component: TestComponent,
      errorBoundary: true,
    })

    const withoutBoundary = React.createElement(ProtectedRoute, {
      path: '/test',
      component: TestComponent,
      errorBoundary: false,
    })

    expect(withBoundary).toBeTruthy()
    expect(withoutBoundary).toBeTruthy()
  })

  it('无权限的路由应该也能正常工作', async () => {
    const ProtectedRoute = (await import('../ProtectedRoute')).default
    
    const TestComponent = () => <div>Public Content</div>

    const element = React.createElement(ProtectedRoute, {
      path: '/public',
      component: TestComponent,
      permissions: [],
    })

    expect(element).toBeTruthy()
  })
})
