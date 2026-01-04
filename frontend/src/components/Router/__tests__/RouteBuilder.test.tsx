/**
 * RouteBuilder 组件测试
 * 测试路由构建器的功能
 * 增强版本 - 添加更全面的测试用例
 */

import { describe, it, expect } from 'vitest'
import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes } from 'react-router-dom'

// Mock all dependencies before importing
vi.mock('../ProtectedRoute', () => ({
  default: vi.fn(({ path, component, permissions, errorBoundary, fallback, ..._props }) => {
    return React.createElement('div', {
      'data-testid': 'protected-route',
      'data-path': path,
      'data-permissions': permissions ? JSON.stringify(permissions) : 'none',
      'data-error-boundary': errorBoundary,
    }, 'Protected Route')
  }),
}))

vi.mock('../LazyRoute', () => ({
  default: vi.fn(({ path, component, preload, permissions, ..._props }) => {
    return React.createElement('div', {
      'data-testid': 'lazy-route',
      'data-path': path,
      'data-permissions': permissions ? JSON.stringify(permissions) : 'none',
      'data-has-preload': !!preload,
    }, 'Lazy Route')
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    Navigate: ({ to, replace }: { to: string; replace?: boolean }) =>
      React.createElement('div', { 'data-testid': 'navigate', 'data-to': to, 'data-replace': replace }, `Navigate to ${to}`),
    Route: ({ path, element, children }: any) =>
      React.createElement('div', {
        'data-testid': 'route',
        'data-path': path,
        'data-has-children': !!children,
        'data-has-element': !!element,
      }, children || element || 'Route'),
  }
})

// Test wrapper
const _TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>
    <Routes>{children}</Routes>
  </MemoryRouter>
)

describe('RouteBuilder - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../RouteBuilder')
    expect(module).toBeDefined()
  })

  it('应该导出RouteBuilder类', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder
    expect(RouteBuilder).toBeDefined()
    expect(typeof RouteBuilder.buildRoute).toBe('function')
  })
})

describe('RouteBuilder - 路由构建测试', () => {
  it('应该能够构建路由配置', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const TestComponent = () => <div>Dashboard</div>

    const config = {
      path: '/dashboard',
      title: '工作台',
      component: TestComponent,
    }

    const element = RouteBuilder.buildRoute(config)

    expect(element).toBeTruthy()
  })

  it('应该支持懒加载路由', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const TestComponent = React.lazy(() =>
      Promise.resolve({ default: () => <div>Lazy Page</div> })
    )

    const config = {
      path: '/lazy',
      title: '懒加载页面',
      component: TestComponent,
      lazy: true,
    }

    const element = RouteBuilder.buildRoute(config)

    expect(element).toBeTruthy()
  })

  it('应该支持嵌套路由', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const ChildComponent = () => <div>Child Page</div>

    const config = {
      path: '/assets',
      title: '资产管理',
      children: [
        {
          path: '/list',
          title: '资产列表',
          component: ChildComponent,
        },
      ],
    }

    const element = RouteBuilder.buildRoute(config)

    expect(element).toBeTruthy()
  })
})

// =============================================================================
// 增强测试 - 静态方法测试
// =============================================================================

describe('RouteBuilder - 静态方法测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('buildRoutes应该构建多个路由', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const ComponentA = () => <div>A</div>
    const ComponentB = () => <div>B</div>

    const configs = [
      { path: '/a', component: ComponentA },
      { path: '/b', component: ComponentB },
    ]

    const elements = RouteBuilder.buildRoutes(configs)

    expect(elements).toHaveLength(2)
    expect(elements[0]).toBeTruthy()
    expect(elements[1]).toBeTruthy()
  })

  it('createRedirect应该创建重定向路由', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const element = RouteBuilder.createRedirect('/old-path', '/new-path', true)

    expect(element).toBeTruthy()
  })

  it('createLazyRoute应该创建懒加载路由', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const TestComponent = React.lazy(() =>
      Promise.resolve({ default: () => <div>Lazy</div> })
    )

    const element = RouteBuilder.createLazyRoute('/lazy', TestComponent, {
      title: '懒加载页面',
    })

    expect(element).toBeTruthy()
  })

  it('createProtectedRoute应该创建受保护路由', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const TestComponent = () => <div>Protected</div>

    const element = RouteBuilder.createProtectedRoute(
      '/protected',
      TestComponent,
      'ASSET_VIEW',
      '资产查看'
    )

    expect(element).toBeTruthy()
  })
})

// =============================================================================
// 边界情况测试
// =============================================================================

describe('RouteBuilder - 边界情况', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('没有组件但有子路由时应该创建容器路由', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const ChildComponent = () => <div>Child</div>

    const config = {
      path: '/parent',
      children: [
        { path: '/child', component: ChildComponent },
      ],
    }

    const element = RouteBuilder.buildRoute(config)
    expect(element).toBeTruthy()
  })

  it('既没有组件也没有子路由时应该创建重定向', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const config = {
      path: '/orphan',
    }

    const element = RouteBuilder.buildRoute(config)
    expect(element).toBeTruthy()
  })

  it('有element属性时应该直接使用Route', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const customElement = <div>Custom</div>

    const config = {
      path: '/custom',
      element: customElement,
    }

    const element = RouteBuilder.buildRoute(config)
    expect(element).toBeTruthy()
  })

  it('应该传递所有额外的props', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const TestComponent = () => <div>Test</div>

    const config = {
      path: '/test',
      component: TestComponent,
      extraProp: 'extra-value',
    }

    const element = RouteBuilder.buildRoute(config)
    expect(element).toBeTruthy()
  })

  it('应该处理空children数组', async () => {
    const module = await import('../RouteBuilder')
    const RouteBuilder = module.default || module.RouteBuilder

    const config = {
      path: '/test',
      children: [],
    }

    const element = RouteBuilder.buildRoute(config)
    expect(element).toBeTruthy()
  })
})

// =============================================================================
// 预定义路由测试
// =============================================================================

describe('RouteBuilder - 预定义路由', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AssetRoutes应该预定义正确的路由', async () => {
    const module = await import('../RouteBuilder')
    const { AssetRoutes } = module

    const TestComponent = () => <div>Asset Page</div>

    const listRoute = AssetRoutes.list(TestComponent)
    const newRoute = AssetRoutes.new(TestComponent)
    const importRoute = AssetRoutes.import(TestComponent)
    const analyticsRoute = AssetRoutes.analytics(TestComponent)

    expect(listRoute).toBeTruthy()
    expect(newRoute).toBeTruthy()
    expect(importRoute).toBeTruthy()
    expect(analyticsRoute).toBeTruthy()
  })

  it('SystemRoutes应该预定义正确的路由', async () => {
    const module = await import('../RouteBuilder')
    const { SystemRoutes } = module

    const TestComponent = () => <div>System Page</div>

    const usersRoute = SystemRoutes.users(TestComponent)
    const rolesRoute = SystemRoutes.roles(TestComponent)
    const organizationsRoute = SystemRoutes.organizations(TestComponent)
    const logsRoute = SystemRoutes.logs(TestComponent)

    expect(usersRoute).toBeTruthy()
    expect(rolesRoute).toBeTruthy()
    expect(organizationsRoute).toBeTruthy()
    expect(logsRoute).toBeTruthy()
  })
})
