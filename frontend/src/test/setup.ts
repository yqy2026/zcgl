/**
 * Vitest全局测试设置文件
 * 配置测试环境和全局mock
 */

import '@testing-library/jest-dom'
import { vi } from 'vitest'

// =============================================================================
// 环境变量Mock
// =============================================================================

vi.stubGlobal('import.meta', {
  env: {
    VITE_API_BASE_URL: '/api',
    VITE_API_TIMEOUT: '30000',
    NODE_ENV: 'test',
  },
})

// =============================================================================
// 浏览器API Mock
// =============================================================================

// Mock window.matchMedia (用于响应式组件测试)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver (用于图表和布局组件)
class ResizeObserverMock {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock)

// Mock IntersectionObserver (用于懒加载组件)
class IntersectionObserverMock {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

vi.stubGlobal('IntersectionObserver', IntersectionObserverMock)

// =============================================================================
// Ant Design Mock
// =============================================================================

// Mock Ant Design message组件
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd')
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
    notification: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
    modal: {
      confirm: vi.fn(),
      info: vi.fn(),
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
    },
  }
})
