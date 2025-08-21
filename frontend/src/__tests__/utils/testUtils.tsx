import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'

// 创建测试用的QueryClient
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      cacheTime: 0,
    },
    mutations: {
      retry: false,
    },
  },
})

// 自定义渲染函数
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient
  initialEntries?: string[]
}

const AllTheProviders: React.FC<{ children: React.ReactNode; queryClient: QueryClient }> = ({ 
  children, 
  queryClient 
}) => {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN}>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  )
}

export const customRender = (
  ui: ReactElement,
  options: CustomRenderOptions = {}
) => {
  const { queryClient = createTestQueryClient(), ...renderOptions } = options

  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <AllTheProviders queryClient={queryClient}>
      {children}
    </AllTheProviders>
  )

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  }
}

// Mock数据生成器
export const createMockAsset = (overrides = {}) => ({
  id: 'test-asset-id',
  ownership_entity: '测试权属方',
  property_name: '测试物业',
  address: '测试地址',
  land_area: 1000,
  rentable_area: 800,
  rented_area: 600,
  property_nature: '经营类',
  ownership_status: '已确权',
  usage_status: '正常使用',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

export const createMockAssetList = (count = 5) => {
  return Array.from({ length: count }, (_, index) => 
    createMockAsset({
      id: `test-asset-${index + 1}`,
      property_name: `测试物业${index + 1}`,
    })
  )
}

// API响应模拟
export const createMockApiResponse = <T,>(data: T, status = 200) => ({
  data,
  status,
  statusText: 'OK',
})

export const createMockApiError = (message = 'API Error', status = 500) => {
  const error = new Error(message) as any
  error.response = {
    data: { message },
    status,
    statusText: 'Internal Server Error',
  }
  return error
}

// 异步等待工具
export const waitForAsync = () => new Promise(resolve => setTimeout(resolve, 0))

// 表单数据模拟
export const createMockFormData = (data: Record<string, any>) => {
  const formData = new FormData()
  Object.entries(data).forEach(([key, value]) => {
    formData.append(key, value)
  })
  return formData
}

// 文件模拟
export const createMockFile = (
  name = 'test.xlsx',
  size = 1024,
  type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
) => {
  const file = new File(['test content'], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

// 用户交互模拟
export const userInteractions = {
  type: async (element: HTMLElement, text: string) => {
    element.focus()
    ;(element as HTMLInputElement).value = text
    element.dispatchEvent(new Event('input', { bubbles: true }))
    element.dispatchEvent(new Event('change', { bubbles: true }))
  },

  click: async (element: HTMLElement) => {
    element.click()
  },

  select: async (selectElement: HTMLElement, optionText: string) => {
    selectElement.click()
    const option = document.querySelector(`[title="${optionText}"]`) as HTMLElement
    if (option) {
      option.click()
    }
  },
}

// 性能测试工具
export const measurePerformance = async (fn: () => Promise<void> | void) => {
  const start = performance.now()
  await fn()
  const end = performance.now()
  return end - start
}

// 可访问性检查
export const checkAccessibility = (container: HTMLElement) => {
  const issues: string[] = []
  
  // 检查图片alt属性
  const images = container.querySelectorAll('img')
  images.forEach((img, index) => {
    if (!img.alt) {
      issues.push(`Image ${index + 1} is missing alt attribute`)
    }
  })
  
  // 检查表单标签
  const inputs = container.querySelectorAll('input, textarea, select')
  inputs.forEach((input, index) => {
    const hasLabel = input.getAttribute('aria-label') ||
                    input.getAttribute('aria-labelledby') ||
                    container.querySelector(`label[for="${input.id}"]`)
    if (!hasLabel) {
      issues.push(`Form element ${index + 1} is missing label`)
    }
  })
  
  // 检查标题层级
  const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6')
  let previousLevel = 0
  headings.forEach((heading, index) => {
    const level = parseInt(heading.tagName.charAt(1))
    if (level > previousLevel + 1) {
      issues.push(`Heading ${index + 1} skips levels (h${previousLevel} to h${level})`)
    }
    previousLevel = level
  })
  
  return issues
}

// LocalStorage模拟
export const mockLocalStorage = () => {
  const store: Record<string, string> = {}
  
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key]
    }),
    clear: jest.fn(() => {
      Object.keys(store).forEach(key => delete store[key])
    }),
    get length() {
      return Object.keys(store).length
    },
    key: jest.fn((index: number) => Object.keys(store)[index] || null),
  }
}

// 重新导出常用的测试工具
export * from '@testing-library/react'
export { default as userEvent } from '@testing-library/user-event'