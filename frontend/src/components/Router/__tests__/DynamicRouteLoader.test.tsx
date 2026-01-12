/**
 * DynamicRouteLoader 组件测试
 * 测试动态路由加载器的核心功能
 */

import { describe, it, expect } from 'vitest'
import React from 'react'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'

describe('DynamicRouteLoader - 基础功能测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../DynamicRouteLoader')
    expect(module).toBeDefined()
    expect(module.DynamicRouteProvider).toBeDefined()
    expect(module.useDynamicRoute).toBeDefined()
  })

  it('DynamicRouteProvider应该正确渲染', async () => {
    const { DynamicRouteProvider } = await import('../DynamicRouteLoader')

    render(
      <DynamicRouteProvider>
        <div data-testid="test-child">Test Child</div>
      </DynamicRouteProvider>
    )

    expect(screen.getByTestId('test-child')).toHaveTextContent('Test Child')
  })
})

describe('DynamicRouteRenderer - 路由渲染测试', () => {
  it('应该在Router和Provider内正确渲染', async () => {
    const { DynamicRouteProvider, DynamicRouteRenderer } = await import('../DynamicRouteLoader')

    render(
      <BrowserRouter>
        <DynamicRouteProvider>
          <DynamicRouteRenderer />
        </DynamicRouteProvider>
      </BrowserRouter>
    )

    // 应该渲染成功（包含默认的dashboard路由）
    expect(screen.getByText(/Loading/i)).toBeTruthy()
  })
})

describe('路由Hook测试', () => {
  it('useDynamicRoute应该在Provider内工作', async () => {
    const { DynamicRouteProvider, useDynamicRoute } = await import('../DynamicRouteLoader')

    const TestComponent = () => {
      const context = useDynamicRoute()
      return (
        <div data-testid="route-count">
          Routes: {context.routes.size}
        </div>
      )
    }

    render(
      <DynamicRouteProvider>
        <TestComponent />
      </DynamicRouteProvider>
    )

    expect(screen.getByTestId('route-count')).toBeTruthy()
  })

  it('useDynamicRoute应该在Provider外抛出错误', async () => {
    const { useDynamicRoute } = await import('../DynamicRouteLoader')

    const TestComponent = () => {
      try {
        useDynamicRoute()
        return <div>No Error</div>
      } catch (error) {
        return <div data-testid="error-message">{(error as Error).message}</div>
      }
    }

    render(<TestComponent />)
    expect(screen.getByTestId('error-message')).toHaveTextContent('useDynamicRoute must be used')
  })
})

describe('RouteModuleLoader - 模块加载测试', () => {
  it('应该在Provider内提供模块加载功能', async () => {
    const { DynamicRouteProvider, RouteModuleLoader } = await import('../DynamicRouteLoader')

    const TestComponent = () => {
      const { loading, loadedModules } = RouteModuleLoader()
      return (
        <div>
          <div data-testid="loading">{loading ? 'true' : 'false'}</div>
          <div data-testid="loaded-count">{loadedModules.length}</div>
        </div>
      )
    }

    render(
      <DynamicRouteProvider>
        <TestComponent />
      </DynamicRouteProvider>
    )

    expect(screen.getByTestId('loading')).toHaveTextContent('false')
    expect(screen.getByTestId('loaded-count')).toHaveTextContent('0')
  })
})

describe('usePermissionBasedRoutes - 权限路由测试', () => {
  it('应该在Provider内提供权限路由加载功能', async () => {
    const { DynamicRouteProvider, usePermissionBasedRoutes } = await import('../DynamicRouteLoader')

    const TestComponent = () => {
      const { availableRoutes } = usePermissionBasedRoutes()
      return (
        <div data-testid="available-routes">
          Available Routes: {availableRoutes.length}
        </div>
      )
    }

    render(
      <DynamicRouteProvider>
        <TestComponent />
      </DynamicRouteProvider>
    )

    expect(screen.getByTestId('available-routes')).toBeTruthy()
  })
})
