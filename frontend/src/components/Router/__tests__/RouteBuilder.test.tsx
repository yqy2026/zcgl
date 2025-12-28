/**
 * RouteBuilder 组件测试
 * 测试路由构建器的功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock all dependencies before importing
vi.mock('../ProtectedRoute', () => ({
  default: vi.fn(({ path, component, permissions, errorBoundary, fallback, ...props }) => {
    return React.createElement('div', {
      'data-testid': 'protected-route',
      'data-path': path,
      'data-permissions': permissions ? JSON.stringify(permissions) : 'none',
    }, 'Protected Route')
  }),
}))

vi.mock('../LazyRoute', () => ({
  default: vi.fn(({ path, component, preload, ...props }) => {
    return React.createElement('div', {
      'data-testid': 'lazy-route',
      'data-path': path,
    }, 'Lazy Route')
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    Navigate: ({ to, replace }: { to: string; replace?: boolean }) => 
      React.createElement('div', { 'data-testid': 'navigate', 'data-to': to }, `Navigate to ${to}`),
  }
})

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
      children: [
        {
          path: '/list',
          component: ChildComponent,
        },
      ],
    }

    const element = RouteBuilder.buildRoute(config)
    
    expect(element).toBeTruthy()
  })
})
