/**
 * 组件测试模板
 * 用于快速创建新的组件测试
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

// 导入Mock配置
import {
  setupDefaultMocks,
  clearAllMocks,
  mockHasPermission
} from './mocks'

// 测试工具函数
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
})

// 测试包装器组件
const TestWrapper = ({ children }: {
  children: React.ReactNode
}) => {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

// 通用测试辅助函数
export const renderWithProviders = (
  ui: React.ReactElement,
  _options: { initialEntries?: string[] } = {}
) => {
  return render(ui, { wrapper: ({ children }) =>
    <TestWrapper>{children}</TestWrapper>
  })
}

// 模拟用户权限
// const mockUserPermissions = ['asset.read', 'asset.create', 'asset.update', 'asset.delete']

// 测试套件模板
export const createComponentTestSuite = (
  componentName: string,
  componentPath: string,
  requiredProps: Record<string, unknown> = {},
  _mockServices: Record<string, unknown> = {}
) => {
  // 动态导入组件
  let Component: React.ComponentType<any>
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    Component = require(componentPath).default
  } catch {
    throw new Error(`无法加载组件: ${componentPath}`)
  }

  describe(`${componentName} 组件测试`, () => {
    beforeEach(() => {
      clearAllMocks()
      setupDefaultMocks()
    })

    test('应该正确渲染组件', () => {
      renderWithProviders(<Component {...requiredProps} />)

      // 验证组件是否渲染
      expect(screen.getByTestId(componentName.toLowerCase())).toBeInTheDocument()
    })

    test('应该显示必需的props', () => {
      renderWithProviders(<Component {...requiredProps} />)

      // 验证必需的props是否正确显示
      Object.entries(requiredProps).forEach(([_key, value]) => {
        if (typeof value === 'string') {
          expect(screen.getByText(value)).toBeInTheDocument()
        }
      })
    })

    test('应该处理用户交互', async () => {
      const mockOnClick = jest.fn()
      const propsWithClick = { ...requiredProps, onClick: mockOnClick }

      renderWithProviders(<Component {...propsWithClick} />)

      // 查找可点击的元素
      const clickableElement = screen.getByRole('button') || screen.getByTestId('button')

      // 模拟点击
      fireEvent.click(clickableElement)

      // 验证回调被调用
      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    test('应该处理加载状态', () => {
      renderWithProviders(<Component {...requiredProps} />)

      // 验证加载状态
      expect(screen.getByTestId('loading') || screen.getByText('加载中...')).toBeInTheDocument()
    })

    test('应该处理错误状态', async () => {
      renderWithProviders(<Component {...requiredProps} />)

      // 等待错误显示
      await waitFor(() => {
        expect(screen.getByText('网络错误') || screen.getByTestId('error')).toBeInTheDocument()
      })
    })

    test('应该正确处理权限控制', () => {
      mockHasPermission.mockReturnValue(false)

      renderWithProviders(<Component {...requiredProps} requiredPermission="asset.create" />)

      // 验证无权限时的显示
      expect(screen.getByText('无权限访问') || screen.getByTestId('no-permission')).toBeInTheDocument()
    })

    test('应该响应式适配', () => {
      // Mock不同屏幕尺寸
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      })

      renderWithProviders(<Component {...requiredProps} />)

      // 验证响应式行为
      expect(screen.getByTestId('responsive-layout')).toBeInTheDocument()
    })

    test('应该正确处理表单提交', async () => {
      const mockOnSubmit = jest.fn()
      const formProps = { ...requiredProps, onSubmit: mockOnSubmit }

      renderWithProviders(<Component {...formProps} />)

      // 填写表单
      const input = screen.getByLabelText(/名称/i) || screen.getByPlaceholderText(/输入/i)
      fireEvent.change(input, { target: { value: '测试值' } })

      // 提交表单
      const submitButton = screen.getByRole('button', { name: /提交|保存/i })
      fireEvent.click(submitButton)

      // 验证提交
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(expect.objectContaining({
          name: '测试值'
        }))
      })
    })

    test('应该正确处理数据更新', async () => {
      const initialData = { id: '1', name: '初始名称' }
      const updatedData = { id: '1', name: '更新名称' }

      const { rerender } = renderWithProviders(
        <Component {...requiredProps} data={initialData} />
      )

      expect(screen.getByText('初始名称')).toBeInTheDocument()

      rerender(
        <TestWrapper>
          <Component {...requiredProps} data={updatedData} />
        </TestWrapper>
      )

      expect(screen.getByText('更新名称')).toBeInTheDocument()
    })

    test('应该正确处理键盘事件', () => {
      renderWithProviders(<Component {...requiredProps} />)

      const input = screen.getByRole('textbox') || screen.getByRole('combobox')

      // 测试Enter键
      fireEvent.keyDown(input, { key: 'Enter' })

      // 测试Escape键
      fireEvent.keyDown(input, { key: 'Escape' })

      // 验证键盘事件处理
      expect(screen.getByDisplayValue('')).toBeInTheDocument()
    })
  })
}

// 组件集成测试模板
export const createIntegrationTestSuite = (
  componentName: string,
  componentPath: string,
  requiredProps: Record<string, unknown> = {}
) => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const Component = require(componentPath).default

  describe(`${componentName} 集成测试`, () => {
    beforeEach(() => {
      clearAllMocks()
      setupDefaultMocks()
    })

    test('应该与路由系统集成', async () => {
      renderWithProviders(<Component {...requiredProps} />, {
        initialEntries: ['/test-route']
      })

      await waitFor(() => {
        expect(screen.getByTestId(componentName.toLowerCase())).toBeInTheDocument()
      })
    })

    test('应该与状态管理集成', async () => {
      // Mock状态管理
      const mockState = { data: 'test-data' }

      renderWithProviders(<Component {...requiredProps} state={mockState} />)

      await waitFor(() => {
        expect(screen.getByText('test-data')).toBeInTheDocument()
      })
    })

    test('应该与API服务集成', async () => {
      renderWithProviders(<Component {...requiredProps} />)

      await waitFor(() => {
        expect(screen.getByTestId(componentName.toLowerCase())).toBeInTheDocument()
      })
    })
  })
}

// 导出模板和工具函数
export {
  TestWrapper,
  createTestQueryClient,
}

export default {
  createComponentTestSuite,
  createIntegrationTestSuite,
  TestWrapper,
  renderWithProviders,
  createTestQueryClient,
}