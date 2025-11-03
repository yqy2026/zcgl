import '@testing-library/jest-dom'

// 测试超时时间已在jest.config.js中统一设置

// React Mocks - 确保React正确导入和初始化
import React from 'react'

// Mock import.meta for Jest compatibility
Object.defineProperty(global, 'import', {
  value: {
    meta: {
      env: {
        VITE_API_BASE_URL: '/api/v1',
        VITE_API_TIMEOUT: '30000',
        NODE_ENV: 'test'
      }
    }
  },
  writable: true
})

// Mock process.env for Jest compatibility
process.env = {
  ...process.env,
  VITE_API_BASE_URL: '/api/v1',
  VITE_API_TIMEOUT: '30000',
  NODE_ENV: 'test'
}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}))

// Mock fetch if needed
global.fetch = jest.fn()