/**
 * Vitest测试辅助函数库
 * 提供自定义渲染函数和测试数据生成器
 */

import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';

// =============================================================================
// 自定义渲染函数
// =============================================================================

/**
 * 包含所有必要Provider的自定义渲染函数
 * @param ui - 要渲染的React元素
 * @param options - 渲染选项
 * @returns 渲染结果
 */
export function renderWithProviders(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  function AllProviders({ children }: { children: React.ReactNode }): JSX.Element {
    return <ConfigProvider locale={zhCN}>{children}</ConfigProvider>;
  }

  return render(ui, { wrapper: AllProviders, ...options });
}

// 重新导出所有testing-library工具
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';

// =============================================================================
// 测试数据Mock
// =============================================================================

/**
 * Mock资产数据
 */
export const mockAsset = {
  id: '1',
  ownershipEntity: '测试权属人',
  propertyName: '测试物业',
  address: '测试地址123号',
  ownershipStatus: '已确权',
  propertyNature: '商业用途',
  usageStatus: '使用中',
  actualPropertyArea: 1000,
  rentableArea: 800,
  rentedArea: 600,
  occupancyRate: 75,
  certificatedUsage: '商业',
  actualUsage: '办公',
  tenantName: '测试租户',
  tenantType: '企业',
  leaseContractNumber: 'CT2024001',
  contractStartDate: '2024-01-01',
  contractEndDate: '2025-12-31',
  monthlyRent: 50000,
  deposit: 150000,
  businessModel: '自营',
  operationStatus: '正常运营',
  managerName: '张三',
  isLitigated: false,
  isSublease: false,
};

/**
 * Mock用户数据
 */
export const mockUser = {
  id: '1',
  username: 'admin',
  fullName: '管理员',
  email: 'admin@test.com',
  roles: ['admin'],
  organizationId: '1',
  isActive: true,
};

/**
 * Mock API响应
 */
export const mockApiResponse = {
  success: true,
  data: [mockAsset],
  pagination: {
    total: 1,
    page: 1,
    pageSize: 20,
  },
  message: '操作成功',
};

// =============================================================================
// 异步测试辅助函数
// =============================================================================

/**
 * 等待异步操作完成（用于微任务队列）
 */
export const waitForAsync = () => new Promise(resolve => setTimeout(resolve, 0));

/**
 * 等待指定时间
 * @param ms - 等待毫秒数
 */
export const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * 等待元素出现
 * @param fn - 返回元素的函数
 */
export const waitForElement = async (fn: () => HTMLElement | null) => {
  while (fn() === null) {
    await wait(50);
  }
  return fn();
};

// =============================================================================
// 表单测试辅助函数
// =============================================================================

/**
 * 填写表单字段
 * @param getByLabelText - 查询函数
 * @param fieldData - 字段名和值的映射
 */
export async function fillForm(
  getByLabelText: (text: string) => HTMLElement,
  fieldData: Record<string, string>
) {
  for (const [field, value] of Object.entries(fieldData)) {
    const input = getByLabelText(field) as HTMLInputElement;
    if (input) {
      input.value = value;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }
}

// =============================================================================
// Mock存储
// =============================================================================

/**
 * Mock localStorage
 */
export const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  get length() {
    return 0;
  },
  key: vi.fn(),
};

/**
 * Mock sessionStorage
 */
export const mockSessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  get length() {
    return 0;
  },
  key: vi.fn(),
};
