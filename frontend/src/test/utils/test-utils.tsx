/**
 * 测试工具函数库
 * 提供常用的测试辅助函数
 */

import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

// =============================================================================
// Test QueryClient
// =============================================================================

/**
 * 创建测试用 QueryClient
 * 配置适合测试环境的选项
 */
export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {
        // 忽略测试中的错误日志
      },
    },
  });

// =============================================================================
// Custom Render Function
// =============================================================================

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient;
  route?: string;
}

/**
 * 带有 Provider 的渲染函数
 * 自动包装 QueryClientProvider 和 BrowserRouter
 */
export const renderWithProviders = (
  ui: ReactElement,
  { queryClient = createTestQueryClient(), route = '/', ...renderOptions }: CustomRenderOptions = {}
) => {
  // 设置路由
  window.history.pushState({}, 'Test page', route);

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// =============================================================================
// Mock Data Generators
// =============================================================================

/**
 * 生成模拟资产数据
 */
export const generateMockAssets = (count: number = 10) => {
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `测试资产 ${i + 1}`,
    code: `ASSET-${String(i + 1).padStart(4, '0')}`,
    area: Math.round(Math.random() * 5000 + 500),
    location: `测试地址 ${i + 1}`,
    status: ['active', 'inactive', 'maintenance'][i % 3],
    asset_type: ['building', 'land', 'facility'][i % 3],
    created_at: new Date().toISOString(),
  }));
};

/**
 * 生成模拟合同数据
 */
export const generateMockContracts = (count: number = 10) => {
  return Array.from({ length: count }, (_, i) => {
    const id = i + 1;
    return {
      id,
      contract_no: `HT-2024-${String(id).padStart(3, '0')}`,
      contract_name: `测试合同 ${id}`,
      contract_type: 'lease',
      status: ['active', 'expired', 'draft'][i % 3],
      start_date: '2024-01-01',
      end_date: '2024-12-31',
      total_rent: 10000 + i * 1000,
      paid_amount: 5000 + i * 500,
      overdue_amount: 1000 + i * 100,
      tenant_name: `测试租户 ${id}`,
      tenant_phone: `1380013800${i % 10}`,
      created_at: new Date().toISOString(),
    };
  });
};

/**
 * 生成模拟权属数据
 */
export const generateMockOwnerships = (count: number = 10) => {
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    asset_id: Math.floor(Math.random() * 100) + 1,
    organization_id: Math.floor(Math.random() * 50) + 1,
    organization_name: `测试单位 ${i + 1}`,
    ownership_ratio: Math.round(100 / count),
    start_date: '2024-01-01',
    is_active: true,
  }));
};

/**
 * 生成模拟组织机构数据
 */
export const generateMockOrganizations = (count: number = 10) => {
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `测试单位 ${i + 1}`,
    code: `ORG-${String(i + 1).padStart(4, '0')}`,
    type: ['company', 'government', 'institution'][i % 3],
    is_active: true,
  }));
};

// =============================================================================
// Wait Utilities
// =============================================================================

/**
 * 等待加载完成
 */
export const waitForLoadingToFinish = () => {
  return new Promise(resolve => setTimeout(resolve, 0));
};

/**
 * 等待指定时间（毫秒）
 */
export const wait = (ms: number) => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

// =============================================================================
// Re-export Testing Library Utilities
// =============================================================================

export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
