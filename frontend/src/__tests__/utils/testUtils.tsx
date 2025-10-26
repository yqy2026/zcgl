import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'

// 创建测试用的QueryClient
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
})

// 测试渲染函数
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ConfigProvider locale={zhCN}>
          {children}
        </ConfigProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
)

// 自定义渲染函数
const customRender = (ui: React.ReactElement, options?: RenderOptions) =>
  render(ui, { wrapper: AllTheProviders, ...options })

// 重新导出testing-library的所有工具
export * from '@testing-library/react'
export { customRender as renderWithProviders }

// 创建模拟文件
export const createMockFile = (name: string, type: string, content: string = '') => {
  const file = new File([content], name, { type })
  return file
}

// 模拟文件读取器
export const mockFileReader = () => {
  const mock = {
    readAsDataURL: jest.fn(),
    readAsText: jest.fn(),
    readAsArrayBuffer: jest.fn(),
    result: null,
    onload: null,
    onerror: null,
  }

  // 模拟FileReader构造函数
  global.FileReader = jest.fn(() => mock) as any

  return mock
}