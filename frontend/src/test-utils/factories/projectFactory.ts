/**
 * Project Mock 工厂函数
 * 用于生成类型安全的测试数据
 */

import type { Project, ProjectCreate } from '@/types/project';

/**
 * 默认 Project 对象
 */
const defaultProject: Project = {
  id: 'test-project-1',
  name: '测试项目',
  code: 'PRJ001',
  short_name: '测试',
  description: '测试项目描述',
  is_active: true,
  data_status: '正常',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ownership_relations: [],
};

/**
 * 创建 Mock Project 对象
 */
export function createMockProject(overrides?: Partial<Project>): Project {
  return { ...defaultProject, ...overrides };
}

/**
 * 创建多个 Mock Project 对象
 */
export function createMockProjects(
  count: number,
  overrides?: Partial<Project> | ((index: number) => Partial<Project>)
): Project[] {
  return Array.from({ length: count }, (_, index) => {
    const override = typeof overrides === 'function' ? overrides(index) : overrides;
    return createMockProject({
      id: `test-project-${index + 1}`,
      name: `测试项目 ${index + 1}`,
      code: `PRJ${String(index + 1).padStart(3, '0')}`,
      ...override,
    });
  });
}

/**
 * 创建 Project 表单数据
 */
export function createMockProjectCreate(overrides?: Partial<ProjectCreate>): ProjectCreate {
  return {
    name: '测试项目',
    description: '测试项目描述',
    ownership_relations: [],
    ...overrides,
  };
}

/**
 * 创建带权属方关联的 Project
 */
export function createProjectWithOwnerships(
  ownershipCount: number,
  overrides?: Partial<Project>
): Project {
  return createMockProject({
    ownership_relations: Array.from({ length: ownershipCount }, (_, i) => ({
      id: `relation-${i + 1}`,
      ownership_id: `ownership-${i + 1}`,
      ownership_name: `权属方 ${i + 1}`,
      relation_type: '管理',
      is_active: true,
    })),
    ...overrides,
  });
}
