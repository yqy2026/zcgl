/**
 * Ownership Mock 工厂函数
 * 用于生成类型安全的测试数据
 */

import type { Ownership, OwnershipFormData } from '@/types/ownership';

/**
 * 默认 Ownership 对象
 */
const defaultOwnership: Ownership = {
  id: 'test-ownership-1',
  name: '测试权属方',
  code: 'TEST001',
  short_name: '测试',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

/**
 * 创建 Mock Ownership 对象
 */
export function createMockOwnership(overrides?: Partial<Ownership>): Ownership {
  return { ...defaultOwnership, ...overrides };
}

/**
 * 创建多个 Mock Ownership 对象
 */
export function createMockOwnerships(
  count: number,
  overrides?: Partial<Ownership> | ((index: number) => Partial<Ownership>)
): Ownership[] {
  return Array.from({ length: count }, (_, index) => {
    const override = typeof overrides === 'function' ? overrides(index) : overrides;
    return createMockOwnership({
      id: `test-ownership-${index + 1}`,
      name: `测试权属方 ${index + 1}`,
      code: `TEST${String(index + 1).padStart(3, '0')}`,
      ...override,
    });
  });
}

/**
 * 创建 Ownership 表单数据
 */
export function createMockOwnershipFormData(
  overrides?: Partial<OwnershipFormData>
): OwnershipFormData {
  return {
    name: '测试权属方',
    code: 'TEST001',
    short_name: '测试',
    ...overrides,
  };
}

/**
 * 创建带关联项目的 Ownership
 */
export function createOwnershipWithProjects(
  projectCount: number,
  overrides?: Partial<Ownership>
): Ownership {
  return createMockOwnership({
    project_count: projectCount,
    related_projects: Array.from({ length: projectCount }, (_, i) => ({
      id: `project-${i + 1}`,
      name: `关联项目 ${i + 1}`,
      code: `PRJ${String(i + 1).padStart(3, '0')}`,
      relation_type: '管理',
    })),
    ...overrides,
  });
}
