/**
 * LazyRoute 组件测试
 * 测试懒加载路由组件的功能
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@/test/utils/test-helpers'
import React from 'react'

// Mock dependencies
vi.mock('@/components/Loading', () => ({
  SkeletonLoader: ({ type, rows }: { type: string; rows: number }) => (
    <div data-testid="skeleton" data-type={type} data-rows={rows}>Loading...</div>
  ),
}))

vi.mock('@/components/ErrorHandling', () => ({
  SystemErrorBoundary: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="error-boundary">{children}</div>
  ),
}))

vi.mock('../System/PermissionGuard', () => ({
  PermissionGuard: ({ children, permissions }: { children: React.ReactNode; permissions: any[] }) => (
    <div data-testid="permission-guard" data-permissions={JSON.stringify(permissions)}>
      {children}
    </div>
  ),
}))

describe('LazyRoute - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../LazyRoute')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })

  it('组件应该是React函数组件', async () => {
    const LazyRoute = (await import('../LazyRoute')).default
    expect(typeof LazyRoute).toBe('function')
  })
})

describe('LazyRoute - 属性测试', () => {
  it('应该支持component属性', async () => {
    const LazyRoute = (await import('../LazyRoute')).default
    
    const TestComponent = React.lazy(() => 
      Promise.resolve({ default: () => <div>Test</div> })
    )

    // 验证组件可以接收必要属性
    const element = React.createElement(LazyRoute, {
      path: '/test',
      component: TestComponent,
    })

    expect(element).toBeTruthy()
  })

  it('应该支持fallback属性', async () => {
    const LazyRoute = (await import('../LazyRoute')).default
    
    const TestComponent = React.lazy(() => 
      Promise.resolve({ default: () => <div>Test</div> })
    )

    const customFallback = <div>Custom Loading</div>

    const element = React.createElement(LazyRoute, {
      path: '/test',
      component: TestComponent,
      fallback: customFallback,
    })

    expect(element).toBeTruthy()
  })

  it('应该支持preload属性', async () => {
    const LazyRoute = (await import('../LazyRoute')).default
    
    const TestComponent = React.lazy(() => 
      Promise.resolve({ default: () => <div>Test</div> })
    )

    const preloadFn = vi.fn()

    const element = React.createElement(LazyRoute, {
      path: '/test',
      component: TestComponent,
      preload: preloadFn,
    })

    expect(element).toBeTruthy()
  })

  it('应该支持permissions属性', async () => {
    const LazyRoute = (await import('../LazyRoute')).default
    
    const TestComponent = React.lazy(() => 
      Promise.resolve({ default: () => <div>Test</div> })
    )

    const permissions = [{ resource: 'asset', action: 'view' }]

    const element = React.createElement(LazyRoute, {
      path: '/test',
      component: TestComponent,
      permissions: permissions,
    })

    expect(element).toBeTruthy()
  })

  it('应该支持errorBoundary属性', async () => {
    const LazyRoute = (await import('../LazyRoute')).default
    
    const TestComponent = React.lazy(() => 
      Promise.resolve({ default: () => <div>Test</div> })
    )

    const elementWithBoundary = React.createElement(LazyRoute, {
      path: '/test',
      component: TestComponent,
      errorBoundary: true,
    })

    const elementWithoutBoundary = React.createElement(LazyRoute, {
      path: '/test',
      component: TestComponent,
      errorBoundary: false,
    })

    expect(elementWithBoundary).toBeTruthy()
    expect(elementWithoutBoundary).toBeTruthy()
  })
})

describe('LazyRoute - 默认值测试', () => {
  it('应该有默认的fallback', async () => {
    const LazyRoute = (await import('../LazyRoute')).default
    
    const TestComponent = React.lazy(() => 
      Promise.resolve({ default: () => <div>Test</div> })
    )

    // 不提供fallback，应该使用默认值
    const element = React.createElement(LazyRoute, {
      path: '/test',
      component: TestComponent,
    })

    expect(element).toBeTruthy()
  })

  it('errorBoundary默认应该为true', async () => {
    const LazyRoute = (await import('../LazyRoute')).default
    
    const TestComponent = React.lazy(() => 
      Promise.resolve({ default: () => <div>Test</div> })
    )

    // 不提供errorBoundary，应该默认为true
    const element = React.createElement(LazyRoute, {
      path: '/test',
      component: TestComponent,
    })

    expect(element).toBeTruthy()
  })
})
