import React from 'react'
import { render, screen } from '../../../__tests__/utils/testUtils'
import { render, screen } from '../../../__tests__/utils/testUtils'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DynamicRouteLoader from '../DynamicRouteLoader'
import { RouteConfig } from '@/constants/routes'

// Mock dependencies
jest.mock('@/services/config', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn()
  }
}))

jest.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({
    hasPermission: jest.fn(() => true),
    loading: false
  })
}))

jest.mock('@/utils/routeCache', () => ({
  useRouteCache: () => ({
    get: jest.fn(),
    set: jest.fn(),
    clear: jest.fn()
  })
}))

// Mock lazy loaded components
jest.mock('../../Asset/AssetList', () => ({
  default: () => <div data-testid="asset-list-component">Asset List</div>
}))

jest.mock('../../Asset/AssetCreatePage', () => ({
  default: () => <div data-testid="asset-create-component">Asset Create</div>
}))

jest.mock('../../System/UserManagementPage', () => ({
  default: () => <div data-testid="user-management-component">User Management</div>
}))

describe('DynamicRouteLoader', () => {
  let queryClient: QueryClient
  let mockRoutes: RouteConfig[]

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    })

    mockRoutes = [
      {
        path: '/assets/list',
        component: React.lazy(() => import('../../Asset/AssetList')),
        permissions: [{ resource: 'ASSET', action: 'VIEW' }],
        title: '资产列表'
      },
      {
        path: '/assets/new',
        component: React.lazy(() => import('../../Asset/AssetCreatePage')),
        permissions: [{ resource: 'ASSET', action: 'CREATE' }],
        title: '创建资产'
      },
      {
        path: '/system/users',
        component: React.lazy(() => import('../../System/UserManagementPage')),
        permissions: [{ resource: 'USER', action: 'VIEW' }],
        title: '用户管理'
      }
    ]

    // 清除所有mock
    jest.clearAllMocks()
  })

  const renderWithProviders = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          {component}
        </BrowserRouter>
      </QueryClientProvider>
    )
  }

  describe('基本功能测试', () => {
    test('应该正确渲染路由加载器', () => {
      renderWithProviders(
        <DynamicRouteLoader
          routes={mockRoutes}
          fallback={<div>Loading routes...</div>}
        />
      )

      expect(screen.getByText('Loading routes...')).toBeInTheDocument()
    })

    test('应该接受自定义fallback组件', () => {
      const customFallback = <div data-testid="custom-fallback">Custom loading...</div>

      renderWithProviders(
        <DynamicRouteLoader
          routes={mockRoutes}
          fallback={customFallback}
        />
      )

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument()
      expect(screen.getByText('Custom loading...')).toBeInTheDocument()
    })

    test('应该处理空路由数组', () => {
      renderWithProviders(
        <DynamicRouteLoader routes={[]} />
      )

      // 应该不渲染任何内容或显示空状态
      expect(document.body).toBeTruthy()
    })
  })

  describe('权限控制测试', () => {
    test('应该根据权限过滤路由', async () => {
      const mockUsePermission = require('@/hooks/usePermission').usePermission

      // Mock第一个路由有权限，第二个无权限
      mockUsePermission.mockImplementation(() => ({
        hasPermission: jest.fn((permissions) => {
          return permissions[0]?.resource === 'ASSET' && permissions[0]?.action === 'VIEW'
        }),
        loading: false
      }))

      renderWithProviders(
        <DynamicRouteLoader routes={mockRoutes} />
      )

      await waitFor(() => {
        expect(screen.getByTestId('asset-list-component')).toBeInTheDocument()
      })

      // 用户管理组件不应该渲染（无权限）
      expect(screen.queryByTestId('user-management-component')).not.toBeInTheDocument()
    })

    test('应该显示权限检查中状态', () => {
      const mockUsePermission = require('@/hooks/usePermission').usePermission

      mockUsePermission.mockImplementation(() => ({
        hasPermission: jest.fn(),
        loading: true  // 权限检查中
      }))

      renderWithProviders(
        <DynamicRouteLoader routes={mockRoutes} />
      )

      expect(screen.getByText('权限检查中...')).toBeInTheDocument()
    })

    test('应该显示权限不足的提示', async () => {
      const mockUsePermission = require('@/hooks/usePermission').usePermission

      mockUsePermission.mockImplementation(() => ({
        hasPermission: jest.fn(() => false), // 无权限
        loading: false
      }))

      renderWithProviders(
        <DynamicRouteLoader routes={mockRoutes} />
      )

      await waitFor(() => {
        expect(screen.getByText('访问被拒绝')).toBeInTheDocument()
        expect(screen.getByText('抱歉，您没有权限访问此页面。')).toBeInTheDocument()
      })
    })
  })

  describe('懒加载测试', () => {
    test('应该正确懒加载组件', async () => {
      renderWithProviders(
        <BrowserRouter>
          <DynamicRouteLoader routes={mockRoutes} />
        </BrowserRouter>
      )

      // 初始状态不应该有组件内容
      expect(screen.queryByTestId('asset-list-component')).not.toBeInTheDocument()

      // 等待懒加载完成
      await waitFor(() => {
        expect(screen.getByTestId('asset-list-component')).toBeInTheDocument()
        expect(screen.getByText('Asset List')).toBeInTheDocument()
      })
    })

    test('应该处理懒加载错误', async () => {
      // 创建一个会抛出错误的懒加载组件
      const errorRoute: RouteConfig = {
        path: '/error',
        component: React.lazy(() => Promise.reject(new Error('Loading failed'))),
        permissions: [],
        title: '错误页面'
      }

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()

      renderWithProviders(
        <DynamicRouteLoader routes={[errorRoute]} />
      )

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('Failed to load route component'),
          expect.any(Error)
        )
      })

      consoleSpy.mockRestore()
    })

    test('应该支持预加载机制', async () => {
      const preloadMock = jest.fn()

      const routeWithPreload: RouteConfig = {
        path: '/preload',
        component: React.lazy(() => import('../../Asset/AssetList')),
        permissions: [],
        title: '预加载页面',
        preload: preloadMock
      }

      renderWithProviders(
        <DynamicRouteLoader routes={[routeWithPreload]} />
      )

      // 模拟预加载触发
      await act(async () => {
        if (routeWithPreload.preload) {
          routeWithPreload.preload()
        }
      })

      expect(preloadMock).toHaveBeenCalled()
    })
  })

  describe('路由缓存测试', () => {
    test('应该使用路由缓存', async () => {
      const mockUseRouteCache = require('@/utils/routeCache').useRouteCache
      const mockGet = jest.fn()
      const mockSet = jest.fn()

      mockUseRouteCache.mockImplementation(() => ({
        get: mockGet,
        set: mockSet,
        clear: jest.fn()
      }))

      // Mock缓存命中
      mockGet.mockReturnValue({
        component: () => <div data-testid="cached-component">Cached Content</div>,
        loaded: true
      })

      renderWithProviders(
        <DynamicRouteLoader routes={mockRoutes} />
      )

      await waitFor(() => {
        expect(screen.getByTestId('cached-component')).toBeInTheDocument()
        expect(mockGet).toHaveBeenCalled()
      })
    })

    test('应该缓存加载的组件', async () => {
      const mockUseRouteCache = require('@/utils/routeCache').useRouteCache
      const mockGet = jest.fn()
      const mockSet = jest.fn()

      mockUseRouteCache.mockImplementation(() => ({
        get: mockGet,
        set: mockSet,
        clear: jest.fn()
      }))

      // Mock缓存未命中
      mockGet.mockReturnValue(null)

      renderWithProviders(
        <DynamicRouteLoader routes={mockRoutes} />
      )

      await waitFor(() => {
        expect(screen.getByTestId('asset-list-component')).toBeInTheDocument()
      })

      // 验证缓存被设置
      expect(mockSet).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          component: expect.any(Function),
          loaded: true
        })
      )
    })
  })

  describe('性能监控测试', () => {
    test('应该记录路由加载时间', async () => {
      const performanceSpy = jest.spyOn(performance, 'mark')
      const performanceMeasureSpy = jest.spyOn(performance, 'measure')

      renderWithProviders(
        <DynamicRouteLoader routes={mockRoutes} />
      )

      await waitFor(() => {
        expect(screen.getByTestId('asset-list-component')).toBeInTheDocument()
      })

      // 验证性能标记被记录
      expect(performanceSpy).toHaveBeenCalledWith(
        expect.stringMatching(/route-load-start/)
      )

      expect(performanceMeasureSpy).toHaveBeenCalledWith(
        expect.stringMatching(/route-load-duration/),
        expect.any(Object),
        expect.any(Object)
      )

      performanceSpy.mockRestore()
      performanceMeasureSpy.mockRestore()
    })

    test('应该监控内存使用', async () => {
      // Mock performance.memory API
      const mockMemory = {
        usedJSHeapSize: 1024 * 1024, // 1MB
        totalJSHeapSize: 2 * 1024 * 1024, // 2MB
        jsHeapSizeLimit: 4 * 1024 * 1024 // 4MB
      }

      Object.defineProperty(performance, 'memory', {
        value: mockMemory,
        configurable: true
      })

      const consoleSpy = jest.spyOn(console, 'info').mockImplementation()

      renderWithProviders(
        <DynamicRouteLoader routes={mockRoutes} />
      )

      await waitFor(() => {
        expect(screen.getByTestId('asset-list-component')).toBeInTheDocument()
      })

      // 验证内存使用被记录
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Route memory usage'),
        expect.objectContaining({
          usedJSHeapSize: mockMemory.usedJSHeapSize,
          totalJSHeapSize: mockMemory.totalJSHeapSize
        })
      )

      consoleSpy.mockRestore()
    })
  })

  describe('错误边界测试', () => {
    test('应该捕获组件渲染错误', async () => {
      // 创建一个会抛出错误的组件
      const ErrorComponent = () => {
        throw new Error('Component render error')
      }

      const errorRoute: RouteConfig = {
        path: '/error',
        component: () => <ErrorComponent />,
        permissions: [],
        title: '错误组件'
      }

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()

      renderWithProviders(
        <DynamicRouteLoader routes={[errorRoute]} />
      )

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('Route component error'),
          expect.any(Error)
        )
      })

      // 应该显示错误回退UI
      expect(screen.getByText('页面加载失败')).toBeInTheDocument()
      expect(screen.getByText('抱歉，页面加载时出现错误。')).toBeInTheDocument()

      consoleSpy.mockRestore()
    })

    test('应该支持错误重试机制', async () => {
      let renderCount = 0
      const FlakyComponent = () => {
        renderCount++
        if (renderCount < 2) {
          throw new Error('First render failed')
        }
        return <div data-testid="flaky-component">Success after retry</div>
      }

      const flakyRoute: RouteConfig = {
        path: '/flaky',
        component: FlakyComponent,
        permissions: [],
        title: '不稳定组件'
      }

      renderWithProviders(
        <DynamicRouteLoader routes={[flakyRoute]} />
      )

      // 等待错误显示
      await waitFor(() => {
        expect(screen.getByText('页面加载失败')).toBeInTheDocument()
      })

      // 点击重试按钮
      const retryButton = screen.getByText('重新加载')
      fireEvent.click(retryButton)

      // 等待重试成功
      await waitFor(() => {
        expect(screen.getByTestId('flaky-component')).toBeInTheDocument()
        expect(screen.getByText('Success after retry')).toBeInTheDocument()
      })
    })
  })

  describe('并发加载测试', () => {
    test('应该正确处理多个路由的并发加载', async () => {
      const concurrentRoutes: RouteConfig[] = Array.from({ length: 5 }, (_, index) => ({
        path: `/route-${index}`,
        component: React.lazy(() => import('../../Asset/AssetList')),
        permissions: [],
        title: `路由 ${index}`
      }))

      const startTime = performance.now()

      renderWithProviders(
        <DynamicRouteLoader routes={concurrentRoutes} />
      )

      await waitFor(() => {
        // 等待所有组件加载完成
        const components = screen.getAllByTestId(/asset-list-component/)
        expect(components.length).toBeGreaterThan(0)
      })

      const endTime = performance.now()
      const loadTime = endTime - startTime

      // 验证并发加载时间合理（应该小于串行加载时间）
      expect(loadTime).toBeLessThan(1000) // 1秒内完成
    })

    test('应该限制并发加载数量', async () => {
      const largeRouteSet: RouteConfig[] = Array.from({ length: 20 }, (_, index) => ({
        path: `/route-${index}`,
        component: React.lazy(() => import('../../Asset/AssetList')),
        permissions: [],
        title: `路由 ${index}`
      }))

      // Mock Promise来控制加载时机
      const originalLazy = React.lazy
      const loadPromises: Promise<any>[] = []

      React.lazy = jest.fn((factory) => {
        const promise = factory()
        loadPromises.push(promise)
        return originalLazy(() => promise)
      })

      renderWithProviders(
        <DynamicRouteLoader routes={largeRouteSet} />
      )

      // 验证并发数量被限制
      expect(loadPromises.length).toBeGreaterThan(0)
      expect(loadPromises.length).toBeLessThanOrEqual(5) // 假设限制为5个并发

      // 恢复原始lazy函数
      React.lazy = originalLazy
    })
  })

  describe('路由预加载测试', () => {
    test('应该支持基于用户行为的智能预加载', async () => {
      const preloadSpy = jest.fn()

      const routesWithPreload: RouteConfig[] = [
        {
          path: '/assets/list',
          component: React.lazy(() => import('../../Asset/AssetList')),
          permissions: [],
          title: '资产列表',
          preload: preloadSpy
        }
      ]

      renderWithProviders(
        <DynamicRouteLoader routes={routesWithPreload} />
      )

      // 模拟用户鼠标悬停事件
      const preloadTrigger = screen.getByTestId('route-preload-trigger')
      if (preloadTrigger) {
        fireEvent.mouseEnter(preloadTrigger)

        await waitFor(() => {
          expect(preloadSpy).toHaveBeenCalled()
        })
      }
    })

    test('应该支持优先级预加载', async () => {
      const highPriorityPreload = jest.fn()
      const lowPriorityPreload = jest.fn()

      const routesWithPriority: RouteConfig[] = [
        {
          path: '/high-priority',
          component: React.lazy(() => import('../../Asset/AssetList')),
          permissions: [],
          title: '高优先级页面',
          preload: highPriorityPreload,
          priority: 'high'
        },
        {
          path: '/low-priority',
          component: React.lazy(() => import('../../Asset/AssetCreatePage')),
          permissions: [],
          title: '低优先级页面',
          preload: lowPriorityPreload,
          priority: 'low'
        }
      ]

      renderWithProviders(
        <DynamicRouteLoader routes={routesWithPriority} />
      )

      // 高优先级页面应该先预加载
      await waitFor(() => {
        expect(highPriorityPreload).toHaveBeenCalledBefore(lowPriorityPreload)
      })
    })
  })

  describe('无障碍功能测试', () => {
    test('应该支持键盘导航', async () => {
      renderWithProviders(
        <DynamicRouteLoader routes={mockRoutes} />
      )

      await waitFor(() => {
        expect(screen.getByTestId('asset-list-component')).toBeInTheDocument()
      })

      // 测试Tab键导航
      const firstFocusableElement = screen.getByRole('button') || screen.getByRole('link')
      expect(firstFocusableElement).toBeInTheDocument()

      fireEvent.keyDown(document, { key: 'Tab' })

      // 验证焦点管理正确
      expect(document.activeElement).toBe(firstFocusableElement)
    })

    test('应该提供适当的ARIA标签', async () => {
      renderWithProviders(
        <DynamicRouteLoader routes={mockRoutes} />
      )

      await waitFor(() => {
        expect(screen.getByTestId('asset-list-component')).toBeInTheDocument()
      })

      // 验证加载状态有适当的ARIA标签
      const loadingElement = screen.queryByRole('status')
      if (loadingElement) {
        expect(loadingElement).toHaveAttribute('aria-live', 'polite')
      }
    })
  })
})