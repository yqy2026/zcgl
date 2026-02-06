/**
 * 测试工具函数库
 * 提供React Testing Library的增强功能和自定义工具
 */

import React, { ReactElement, ReactNode } from 'react';
import {
  render,
  RenderOptions,
  renderHook,
  waitFor,
  waitForElementToBeRemoved,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import userEvent from '@testing-library/user-event';

// =============================================================================
// 类型定义
// =============================================================================

interface ProvidersProps {
  children: ReactNode;
  queryClient?: QueryClient;
  theme?: 'light' | 'dark';
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient;
  theme?: 'light' | 'dark';
  route?: string;
}

// =============================================================================
// 创建测试用QueryClient
// =============================================================================

/**
 * 创建测试专用的QueryClient实例
 *
 * 特点：
 * - 禁用自动重试，加快测试速度
 * - 设置默认缓存时间为0，避免测试间数据污染
 */
export const createTestQueryClient = (): QueryClient => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
        refetchOnWindowFocus: false,
        refetchOnMount: false,
        refetchOnReconnect: false,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: (): void => {}, // 静默日志，避免测试输出混乱
      warn: (): void => {}, // 静默警告，避免测试输出混乱
      error: (): void => {}, // 静默错误日志，避免测试输出混乱
    },
  });
};

// =============================================================================
// Provider包装器
// =============================================================================

/**
 * AllInOneProvider - 统一的Provider包装器
 *
 * 包含：
 * - BrowserRouter (路由支持)
 * - QueryClientProvider (React Query支持)
 * - ConfigProvider (Ant Design主题和国际化)
 */
const AllInOneProvider = ({ children, queryClient, theme = 'light' }: ProvidersProps) => {
  const testQueryClient = queryClient || createTestQueryClient();

  return (
    <QueryClientProvider client={testQueryClient}>
      <BrowserRouter>
        <ConfigProvider
          locale={zhCN}
          theme={{
            algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
            token: {
              colorPrimary: '#1890ff',
            },
          }}
        >
          {children}
        </ConfigProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// =============================================================================
// 自定义render函数
// =============================================================================

/**
 * renderWithProviders - 增强的render函数
 *
 * 自动包装所有必需的Provider，简化测试代码
 *
 * @example
 * ```tsx
 * // 基础使用
 * renderWithProviders(<MyComponent />)
 *
 * // 自定义QueryClient
 * const queryClient = createTestQueryClient()
 * renderWithProviders(<MyComponent />, { queryClient })
 *
 * // 使用深色主题
 * renderWithProviders(<MyComponent />, { theme: 'dark' })
 *
 * // 传递其他RTL选项
 * renderWithProviders(<MyComponent />, { route: '/assets/123' })
 * ```
 */
export const renderWithProviders = (
  ui: ReactElement,
  { queryClient, theme = 'light', route, ...renderOptions }: CustomRenderOptions = {}
) => {
  // 如果指定了路由，设置window.location
  if (route) {
    window.history.pushState({}, 'Test page', route);
  }

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <AllInOneProvider queryClient={queryClient} theme={theme}>
        {children}
      </AllInOneProvider>
    );
  }

  return {
    user: userEvent.setup(),
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
};

// 重新导出所有RTL工具，方便使用
export { render, waitFor, waitForElementToBeRemoved };

// =============================================================================
// 自定义renderHook函数
// =============================================================================

/**
 * renderHookWithProviders - 增强的renderHook函数
 *
 * 用于测试自定义Hooks，自动包装Provider
 *
 * @example
 * ```tsx
 * const { result } = renderHookWithProviders(() => useAssets())
 * await waitFor(() => expect(result.current.isSuccess).toBe(true))
 * ```
 */
export const renderHookWithProviders = <TProps, TResult>(
  callback: (props: TProps) => TResult,
  options?: Omit<CustomRenderOptions, 'wrapper'>
) => {
  const { queryClient, theme = 'light', ...renderOptions } = options || {};

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <AllInOneProvider queryClient={queryClient} theme={theme}>
        {children}
      </AllInOneProvider>
    );
  }

  return renderHook(callback, { wrapper: Wrapper, ...renderOptions });
};

// 重新导出renderHook
export { renderHook };

// =============================================================================
// 自定义匹配器
// =============================================================================

/**
 * 扩展expect，添加自定义匹配器
 */

/**
 * toHaveValidAPIResponse - 验证API响应格式
 *
 * @example
 * ```ts
 * const response = await api.get('/assets')
 * expect(response).toHaveValidAPIResponse()
 * ```
 */
expect.extend({
  toHaveValidAPIResponse(received: unknown) {
    const pass =
      typeof received === 'object' &&
      received !== null &&
      'success' in received &&
      typeof received.success === 'boolean' &&
      'data' in received;

    return {
      pass,
      message: () =>
        pass ? '期望不是有效API响应' : `期望是有效API响应，但收到 ${JSON.stringify(received)}`,
    };
  },
});

/**
 * toBeValidAsset - 验证资产对象格式
 *
 * @example
 * ```ts
 * expect(asset).toBeValidAsset()
 * ```
 */
expect.extend({
  toBeValidAsset(received: unknown) {
    const pass =
      typeof received === 'object' &&
      received !== null &&
      'id' in received &&
      'propertyName' in received &&
      'ownershipStatus' in received;

    return {
      pass,
      message: () => (pass ? '期望不是有效资产对象' : `期望是有效资产对象，但缺少必需字段`),
    };
  },
});

// =============================================================================
// 测试辅助函数
// =============================================================================

/**
 * waitForLoadingToFinish - 等待加载状态结束
 *
 * @example
 * ```tsx
 * renderWithProviders(<AssetList />)
 * await waitForLoadingToFinish()
 * expect(screen.getByText('资产列表')).toBeInTheDocument()
 * ```
 */
export const waitForLoadingToFinish = () =>
  waitFor(() => {
    const loaders = document.querySelectorAll('[role="status"]');
    loaders.forEach(loader => {
      if (loader.textContent === '加载中...' || loader.textContent === 'Loading...') {
        throw new Error('Still loading');
      }
    });
  });

/**
 * mockConsole - 临时mock console方法
 *
 * 用于测试时屏蔽某些console输出
 *
 * @example
 * ```tsx
 * it('should not log errors', () => {
 *   const restore = mockConsole('error')
 *   // ... 执行会产生error的代码
 *   restore()
 * })
 * ```
 */
export const mockConsole = (method: 'log' | 'error' | 'warn' = 'log') => {
  const spy = vi.spyOn(console, method).mockImplementation(() => {});

  return () => {
    spy.mockRestore();
  };
};

/**
 * createMockRouter - 创建mock路由对象
 *
 * @example
 * ```tsx
 * const router = createMockRouter()
 * renderWithProviders(<MyComponent />, { route: '/assets/123' })
 * expect(router.pathname).toBe('/assets/123')
 * ```
 */
export const createMockRouter = () => ({
  pathname: window.location.pathname,
  search: window.location.search,
  hash: window.location.hash,
  state: null,
  push: vi.fn(),
  replace: vi.fn(),
  go: vi.fn(),
  goBack: vi.fn(),
  goForward: vi.fn(),
});

/**
 * createMockUser - 创建mock用户对象
 *
 * @example
 * ```tsx
 * const user = createMockUser({ role_name: 'admin', roles: ['admin'] })
 * ```
 */
export const createMockUser = (overrides: Partial<API.User> = {}) => ({
  id: 'test-user-001',
  username: 'testuser',
  email: 'test@example.com',
  fullName: '测试用户',
  roles: ['user'],
  permissions: [],
  organization: {
    id: 'org-001',
    name: '测试组织',
  },
  ...overrides,
});

// =============================================================================
// 导出所有工具
// =============================================================================

// 重新导出React Testing Library核心功能
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';

// 默认导出
export default {
  renderWithProviders,
  renderHookWithProviders,
  createTestQueryClient,
  waitForLoadingToFinish,
  mockConsole,
  createMockRouter,
  createMockUser,
};
