/**
 * Vitest全局测试设置文件
 * 配置测试环境和全局mock
 */

import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { renderWithProviders } from '@/test/utils/test-helpers';

type MswServer = {
  listen: (options?: { onUnhandledRequest?: 'warn' | 'error' | 'bypass' }) => void;
  resetHandlers: () => void;
  close: () => void;
};

let mswServer: MswServer | null = null;

// =============================================================================
// MSW 服务器设置
// =============================================================================

// 在所有测试之前启动MSW服务器
beforeAll(async () => {
  try {
    const { mswServer: resolvedServer } = await import('@/mocks/server');
    mswServer = resolvedServer;
    mswServer.listen({
      onUnhandledRequest: 'warn', // 对未处理的请求警告（不阻止测试）
    });
  } catch (error) {
    // 某些测试会 mock handlers 依赖模块，导致 MSW 入口不可用；降级为无 MSW 运行
    mswServer = null;
    console.warn('[test/setup] MSW server bootstrap skipped:', error);
  }
});

// 在每个测试之后重置handlers，确保测试隔离
afterEach(() => {
  mswServer?.resetHandlers();
  vi.useRealTimers();
});

// 在所有测试之后关闭MSW服务器
afterAll(() => {
  mswServer?.close();
});

// =============================================================================
// 环境变量Mock
// =============================================================================

vi.stubGlobal('import.meta', {
  env: {
    VITE_API_BASE_URL: '/api/v1',
    VITE_API_TIMEOUT: '30000',
    NODE_ENV: 'test',
  },
});

// 为历史测试文件提供统一渲染入口，避免遗漏导入导致的运行时失败
vi.stubGlobal('renderWithProviders', renderWithProviders);

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
});

// jsdom 对 pseudo-element 的 getComputedStyle 仅会向 stderr 打 not implemented 噪音。
// 测试里统一回退到宿主元素样式读取，避免把环境缺口误报成组件问题。
const originalGetComputedStyle = window.getComputedStyle.bind(window);
Object.defineProperty(window, 'getComputedStyle', {
  writable: true,
  value: ((element: Element, pseudoElement?: string | null) => {
    if (pseudoElement != null && pseudoElement !== '') {
      return originalGetComputedStyle(element);
    }
    return originalGetComputedStyle(element, pseudoElement);
  }) as typeof window.getComputedStyle,
});

// Mock ResizeObserver (用于图表和布局组件)
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock);

// Mock IntersectionObserver (用于懒加载组件)
class IntersectionObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

vi.stubGlobal('IntersectionObserver', IntersectionObserverMock);

// =============================================================================
// Sentry Mock (Optional Dependency)
//=============================================================================

// Mock @sentry/react (optional dependency for error monitoring)
class SentryBrowserTracingMock {}
class SentryReplayMock {}

vi.mock('@sentry/react', () => ({
  default: {
    init: vi.fn(),
    captureException: vi.fn(),
    captureMessage: vi.fn(),
    configureScope: vi.fn(),
    addBreadcrumb: vi.fn(),
    setUser: vi.fn(),
    setTag: vi.fn(),
    startTransaction: vi.fn(),
    finishTransaction: vi.fn(),
  },
  BrowserTracing: SentryBrowserTracingMock,
  Replay: SentryReplayMock,
  integrations: [],
}));

// =============================================================================
// Ant Design Mock
// =============================================================================

// Mock Ant Design message组件
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
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
  };
});
