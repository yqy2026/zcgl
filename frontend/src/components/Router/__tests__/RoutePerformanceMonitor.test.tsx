import React from 'react'
import { render, screen } from '../../../__tests__/utils/testUtils'
import { render, screen } from '../../../__tests__/utils/testUtils'
import { BrowserRouter } from 'react-router-dom'
import RoutePerformanceMonitor from '../RoutePerformanceMonitor'
import { RouteMetrics } from '@/types/route'

// Mock dependencies
jest.mock('@/utils/routeCache', () => ({
  useRouteCache: () => ({
    get: jest.fn(),
    set: jest.fn(),
    getMetrics: jest.fn(() => ({
      hitRate: 0.8,
      totalRequests: 100,
      cacheHits: 80
    }))
  })
}))

jest.mock('@/services/config', () => ({
  apiClient: {
    post: jest.fn(() => Promise.resolve({ success: true }))
  }
}))

// Mock Performance API
const mockPerformance = {
  mark: jest.fn(),
  measure: jest.fn(),
  getEntriesByName: jest.fn(() => []),
  clearMarks: jest.fn(),
  clearMeasures: jest.fn()
}

Object.defineProperty(global, 'performance', {
  value: mockPerformance,
  writable: true
})

// Mock PerformanceObserver
const mockPerformanceObserver = {
  observe: jest.fn(),
  disconnect: jest.fn()
}

global.PerformanceObserver = jest.fn((callback) => {
  setTimeout(() => {
    // 模拟性能指标回调
    callback({
      getEntries: () => [
        {
          name: 'navigation',
          entryType: 'navigation',
          startTime: 0,
          fetchStart: 100,
          domainLookupStart: 200,
          domainLookupEnd: 300,
          connectStart: 300,
          connectEnd: 400,
          requestStart: 500,
          responseStart: 600,
          responseEnd: 800,
          domInteractive: 900,
          domComplete: 1000,
          loadEventStart: 1100,
          loadEventEnd: 1200,
          transferSize: 50000,
          encodedBodySize: 45000,
          decodedBodySize: 48000
        },
        {
          name: 'first-contentful-paint',
          entryType: 'paint',
          startTime: 950,
          duration: 0
        },
        {
          name: 'largest-contentful-paint',
          entryType: 'largest-contentful-paint',
          startTime: 1200,
          size: 50000
        },
        {
          name: 'first-input',
          entryType: 'first-input',
          startTime: 1300,
          processingStart: 1350,
          processingEnd: 1400,
          duration: 100
        },
        {
          name: 'layout-shift',
          entryType: 'layout-shift',
          startTime: 1500,
          value: 0.1,
          hadRecentInput: false
        }
      ]
    })
  }, 0)

  return mockPerformanceObserver
}) as any

describe('RoutePerformanceMonitor', () => {
  let mockOnMetricsUpdate: jest.Mock

  beforeEach(() => {
    mockOnMetricsUpdate = jest.fn()

    // 清除所有mock
    jest.clearAllMocks()

    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: {
        href: 'http://localhost:3000/assets/list',
        pathname: '/assets/list'
      },
      writable: true
    })

    // Mock performance.memory
    Object.defineProperty(performance, 'memory', {
      value: {
        usedJSHeapSize: 1024 * 1024, // 1MB
        totalJSHeapSize: 2 * 1024 * 1024, // 2MB
        jsHeapSizeLimit: 4 * 1024 * 1024 // 4MB
      },
      writable: true
    })
  })

  const renderWithRouter = (component: React.ReactElement) => {
    return render(
      <BrowserRouter>
        {component}
      </BrowserRouter>
    )
  }

  describe('基本功能测试', () => {
    test('应该正确渲染性能监控器', () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 应该显示性能监控状态
      expect(screen.getByTestId('route-performance-monitor')).toBeInTheDocument()
    })

    test('应该支持禁用状态', () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={false}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 禁用时不应该渲染监控内容
      expect(screen.queryByTestId('route-performance-monitor')).not.toBeInTheDocument()
    })

    test('应该接受自定义配置', () => {
      const customConfig = {
        sampleRate: 0.1,
        maxBufferLength: 50,
        reportInterval: 5000
      }

      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          config={customConfig}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 验证配置被正确应用
      expect(screen.getByTestId('route-performance-monitor')).toBeInTheDocument()
    })
  })

  describe('核心Web指标监控测试', () => {
    test('应该监控FCP（首次内容绘制）', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            fcp: expect.objectContaining({
              value: expect.any(Number),
              rating: expect.any(String)
            })
          })
        )
      })
    })

    test('应该监控LCP（最大内容绘制）', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            lcp: expect.objectContaining({
              value: expect.any(Number),
              rating: expect.any(String)
            })
          })
        )
      })
    })

    test('应该监控FID（首次输入延迟）', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 模拟用户输入
      act(() => {
        fireEvent.click(document.body)
      })

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            fid: expect.objectContaining({
              value: expect.any(Number),
              rating: expect.any(String)
            })
          })
        )
      })
    })

    test('应该监控CLS（累积布局偏移）', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            cls: expect.objectContaining({
              value: expect.any(Number),
              rating: expect.any(String)
            })
          })
        )
      })
    })

    test('应该计算性能评分', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        const metricsCall = mockOnMetricsUpdate.mock.calls[0][0]
        expect(metricsCall).toHaveProperty('performanceScore')
        expect(metricsCall.performanceScore).toBeGreaterThanOrEqual(0)
        expect(metricsCall.performanceScore).toBeLessThanOrEqual(100)
      })
    })
  })

  describe('路由特定指标测试', () => {
    test('应该监控路由加载时间', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            routeLoadTime: expect.any(Number),
            componentLoadTime: expect.any(Number),
            renderTime: expect.any(Number)
          })
        )
      })
    })

    test('应该记录路由路径', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            routePath: '/assets/list'
          })
        )
      })
    })

    test('应该监控交互时间', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 模拟交互
      act(() => {
        fireEvent.click(document.body)
      })

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            interactiveTime: expect.any(Number)
          })
        )
      })
    })
  })

  describe('内存使用监控测试', () => {
    test('应该监控JS堆大小', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            memoryUsage: expect.objectContaining({
              usedJSHeapSize: 1024 * 1024,
              totalJSHeapSize: 2 * 1024 * 1024,
              jsHeapSizeLimit: 4 * 1024 * 1024
            })
          })
        )
      })
    })

    test('应该检测内存泄漏', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 模拟内存增长
      Object.defineProperty(performance, 'memory', {
        value: {
          usedJSHeapSize: 3 * 1024 * 1024, // 3MB (增长)
          totalJSHeapSize: 4 * 1024 * 1024,
          jsHeapSizeLimit: 4 * 1024 * 1024
        },
        writable: true
      })

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            memoryLeak: expect.objectContaining({
              detected: expect.any(Boolean),
              growthRate: expect.any(Number)
            })
          })
        )
      })
    })
  })

  describe('网络性能监控测试', () => {
    test('应该监控网络连接时间', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            networkMetrics: expect.objectContaining({
              domainLookupTime: expect.any(Number),
              connectTime: expect.any(Number),
              requestTime: expect.any(Number),
              responseTime: expect.any(Number)
            })
          })
        )
      })
    })

    test('应该监控传输大小', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            transferSize: expect.any(Number),
            encodedBodySize: expect.any(Number),
            decodedBodySize: expect.any(Number)
          })
        )
      })
    })
  })

  describe('错误监控测试', () => {
    test('应该记录错误数量', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 模拟错误
      act(() => {
        const error = new Error('Test error')
        window.dispatchEvent(new ErrorEvent('error', { error }))
      })

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            errorCount: expect.any(Number)
          })
        )
      })
    })

    test('应该记录重试次数', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            retryCount: expect.any(Number)
          })
        )
      })
    })
  })

  describe('缓存性能测试', () => {
    test('应该监控缓存命中率', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            cacheMetrics: expect.objectContaining({
              hitRate: 0.8,
              totalRequests: 100,
              cacheHits: 80
            })
          })
        )
      })
    })

    test('应该计算缓存效率', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        const metricsCall = mockOnMetricsUpdate.mock.calls[0][0]
        expect(metricsCall).toHaveProperty('cacheEfficiency')
        expect(metricsCall.cacheEfficiency).toBeGreaterThanOrEqual(0)
        expect(metricsCall.cacheEfficiency).toBeLessThanOrEqual(1)
      })
    })
  })

  describe('数据上报测试', () => {
    test('应该定期上报性能数据', async () => {
      const mockPost = require('@/services/config').apiClient.post

      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          reportInterval={1000} // 1秒上报间隔
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 等待首次上报
      await waitFor(
        () => {
          expect(mockPost).toHaveBeenCalledWith(
            '/api/v1/monitoring/performance-report',
            expect.objectContaining({
              metrics: expect.any(Object),
              timestamp: expect.any(String)
            })
          )
        },
        { timeout: 2000 }
      )
    })

    test('应该批量上报数据', async () => {
      const mockPost = require('@/services/config').apiClient.post

      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          batchSize={5}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockPost).toHaveBeenCalledWith(
          '/api/v1/monitoring/performance-report',
          expect.objectContaining({
            metrics: expect.any(Array)
          })
        )
      })
    })

    test('应该处理上报失败', async () => {
      const mockPost = require('@/services/config').apiClient.post
      mockPost.mockRejectedValue(new Error('Network error'))

      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation()

      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('Failed to report performance metrics'),
          expect.any(Error)
        )
      })

      consoleSpy.mockRestore()
    })
  })

  describe('用户体验指标测试', () => {
    test('应该计算用户体验评分', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        const metricsCall = mockOnMetricsUpdate.mock.calls[0][0]
        expect(metricsCall).toHaveProperty('uxScore')
        expect(metricsCall.uxScore).toBeGreaterThanOrEqual(0)
        expect(metricsCall.uxScore).toBeLessThanOrEqual(100)
      })
    })

    test('应该检测长任务', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 模拟长任务
      act(() => {
        const start = performance.now()
        while (performance.now() - start < 60) {
          // 模拟60ms的长任务
        }
      })

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            longTasks: expect.arrayContaining([
              expect.objectContaining({
                duration: expect.any(Number),
                startTime: expect.any(Number)
              })
            ])
          })
        )
      })
    })
  })

  describe('采样率控制测试', () => {
    test('应该根据采样率控制监控频率', () => {
      Math.random = jest.fn(() => 0.05) // 5% 随机数

      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          sampleRate={0.1} // 10% 采样率
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 5% < 10%，应该启用监控
      expect(screen.getByTestId('route-performance-monitor')).toBeInTheDocument()
    })

    test('应该在采样率之外禁用监控', () => {
      Math.random = jest.fn(() => 0.15) // 15% 随机数

      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          sampleRate={0.1} // 10% 采样率
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 15% > 10%，应该禁用监控
      expect(screen.queryByTestId('route-performance-monitor')).not.toBeInTheDocument()
    })
  })

  describe('性能基准测试', () => {
    test('应该与性能基准进行比较', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        expect(mockOnMetricsUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            performanceBenchmark: expect.objectContaining({
              fcpBenchmark: { good: 1800, needsImprovement: 3000 },
              lcpBenchmark: { good: 2500, needsImprovement: 4000 },
              fidBenchmark: { good: 100, needsImprovement: 300 },
              clsBenchmark: { good: 0.1, needsImprovement: 0.25 }
            })
          })
        )
      })
    })

    test('应该标记性能等级', async () => {
      renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      await waitFor(() => {
        const metricsCall = mockOnMetricsUpdate.mock.calls[0][0]
        expect(metricsCall).toHaveProperty('performanceGrade')
        expect(['good', 'needsImprovement', 'poor']).toContain(metricsCall.performanceGrade)
      })
    })
  })

  describe('清理和销毁测试', () => {
    test('应该在组件卸载时清理资源', () => {
      const { unmount } = renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      // 验证性能观察器已创建
      expect(global.PerformanceObserver).toHaveBeenCalled()

      // 卸载组件
      unmount()

      // 验证清理函数被调用
      expect(mockPerformanceObserver.disconnect).toHaveBeenCalled()
    })

    test('应该清理性能标记和测量', () => {
      const { unmount } = renderWithRouter(
        <RoutePerformanceMonitor
          enabled={true}
          onMetricsUpdate={mockOnMetricsUpdate}
        />
      )

      unmount()

      expect(mockPerformance.clearMarks).toHaveBeenCalled()
      expect(mockPerformance.clearMeasures).toHaveBeenCalled()
    })
  })
})