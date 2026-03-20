/**
 * 组织架构查询与工具模块
 *
 * @description 从 organizationService.ts 提取的查询/搜索/统计/工具函数。
 *              所有函数均为纯只读操作或纯计算逻辑，不涉及写入操作。
 *              外部消费者请继续通过 organizationService 访问（该文件由 hub 内部导入）。
 * @author Claude Code
 */

import {
  Organization,
  OrganizationTree,
  OrganizationHistory,
  OrganizationStatistics,
  OrganizationPath,
  OrganizationSearchCriteria,
} from '@/types/organization';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { createLogger } from '@/utils/logger';

const logger = createLogger('OrganizationQuery');

// ==================== 内部工具 ====================

// 树节点接口
export interface TreeNode {
  key: string;
  value: string;
  title: string;
  children?: TreeNode[];
}

/**
 * 从后端响应中提取列表数据（处理多种返回格式）
 */
export function extractList<T>(data: unknown): T[] {
  if (Array.isArray(data)) {
    return data as T[];
  }

  if (data != null && typeof data === 'object') {
    const record = data as Record<string, unknown>;
    const items = record.items;
    if (Array.isArray(items)) {
      return items as T[];
    }

    const nested = record.data;
    if (Array.isArray(nested)) {
      return nested as T[];
    }
  }

  return [];
}

// ==================== 组织树形结构查询 ====================

const BASE_URL = '/organizations';

/**
 * 获取组织树形结构
 */
export async function fetchOrganizationTree(parentId?: string): Promise<OrganizationTree[]> {
  try {
    const params =
      parentId !== null && parentId !== undefined && parentId !== ''
        ? { parent_id: parentId }
        : {};
    const result = await apiClient.get<OrganizationTree[]>(`${BASE_URL}/tree`, {
      params,
      cache: true,
      retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      smartExtract: true,
    });

    if (!result.success) {
      throw new Error(`获取组织树失败: ${result.error}`);
    }

    return result.data!;
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    console.error('获取组织树失败:', enhancedError.message);
    return [];
  }
}

/**
 * 获取组织的子组织
 */
export async function fetchOrganizationChildren(
  id: string,
  recursive: boolean = false
): Promise<Organization[]> {
  try {
    const result = await apiClient.get<Organization[]>(`${BASE_URL}/${id}/children`, {
      params: { recursive },
      cache: true,
      retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      smartExtract: true,
    });

    if (!result.success) {
      throw new Error(`获取子组织失败: ${result.error}`);
    }

    return result.data!;
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    throw new Error(enhancedError.message);
  }
}

/**
 * 获取组织到根节点的路径
 */
export async function fetchOrganizationPath(id: string): Promise<OrganizationPath> {
  try {
    const result = await apiClient.get<Organization[]>(`${BASE_URL}/${id}/path`, {
      cache: true,
      retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      smartExtract: true,
    });

    if (!result.success) {
      throw new Error(`获取组织路径失败: ${result.error}`);
    }

    const organizations = result.data!;
    const pathString = organizations.map((org: Organization) => org.name).join(' > ');
    return { organizations, path_string: pathString };
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    throw new Error(enhancedError.message);
  }
}

// ==================== 搜索功能 ====================

/**
 * 搜索组织
 */
export async function searchOrganizations(
  keyword: string,
  params?: { page?: number; page_size?: number }
): Promise<Organization[]> {
  try {
    const result = await apiClient.get<Organization[]>(`${BASE_URL}/search`, {
      params: {
        keyword,
        ...params,
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
      },
      cache: true,
      retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      smartExtract: true,
    });

    if (!result.success) {
      throw new Error(`搜索组织失败: ${result.error}`);
    }

    return extractList<Organization>(result.data);
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    throw new Error(enhancedError.message);
  }
}

/**
 * 高级搜索组织
 */
export async function detailedSearchOrganizations(
  searchRequest: OrganizationSearchCriteria
): Promise<Organization[]> {
  try {
    const result = await apiClient.post<Organization[]>(
      `${BASE_URL}/advanced-search`,
      searchRequest,
      {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      }
    );

    if (!result.success) {
      throw new Error(`高级搜索组织失败: ${result.error}`);
    }

    return extractList<Organization>(result.data);
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    throw new Error(enhancedError.message);
  }
}

// ==================== 统计和分析 ====================

/**
 * 获取组织统计信息
 */
export async function fetchStatistics(): Promise<OrganizationStatistics> {
  try {
    const result = await apiClient.get<OrganizationStatistics>(`${BASE_URL}/statistics`, {
      cache: true,
      retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      smartExtract: true,
    });

    if (!result.success) {
      throw new Error(`获取组织统计失败: ${result.error}`);
    }

    return result.data!;
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    throw new Error(enhancedError.message);
  }
}

/**
 * 获取组织变更历史
 */
export async function fetchOrganizationHistory(
  id: string,
  params?: { page?: number; page_size?: number }
): Promise<OrganizationHistory[]> {
  try {
    const result = await apiClient.get<OrganizationHistory[]>(`${BASE_URL}/${id}/history`, {
      params: {
        ...params,
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
      },
      cache: true,
      retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      smartExtract: true,
    });

    if (!result.success) {
      throw new Error(`获取组织历史失败: ${result.error}`);
    }

    return extractList<OrganizationHistory>(result.data);
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    throw new Error(enhancedError.message);
  }
}

// ==================== 纯工具方法（无 API 调用） ====================

/**
 * 向树节点添加子节点（递归）
 */
function addChildToTreeNode(
  treeData: TreeNode[],
  parentId: string,
  childNode: TreeNode
): boolean {
  for (const node of treeData) {
    if (node.key === parentId) {
      node.children = node.children ?? [];
      node.children.push(childNode);
      return true;
    }
    if (node.children && addChildToTreeNode(node.children, parentId, childNode)) {
      return true;
    }
  }
  return false;
}

/**
 * 构建组织树形数据
 */
export function buildOrganizationTreeData(organizations: Organization[]): TreeNode[] {
  const treeData: TreeNode[] = [];
  const organizationMap = new Map<string, Organization>();

  // 创建组织映射
  organizations.forEach(org => {
    organizationMap.set(org.id, org);
  });

  // 构建树形结构
  organizations.forEach(org => {
    const treeNode = {
      key: org.id,
      value: org.id,
      title: org.name,
      children: [] as TreeNode[],
    };

    if (org.parent_id === null || org.parent_id === undefined || org.parent_id === '') {
      treeData.push(treeNode);
    } else {
      const parent = organizationMap.get(org.parent_id);
      if (parent) {
        // 找到父节点并添加子节点
        addChildToTreeNode(treeData, org.parent_id, treeNode);
      }
    }
  });

  return treeData;
}

/**
 * 获取组织层级路径
 */
export function getOrganizationLevelPath(
  organization: Organization,
  allOrganizations: Organization[]
): string[] {
  const path: string[] = [];
  let current: Organization | null = organization;

  while (current) {
    path.unshift(current.name);
    if (
      current.parent_id !== null &&
      current.parent_id !== undefined &&
      current.parent_id !== ''
    ) {
      const parentOrg = allOrganizations.find(org => org.id === current!.parent_id);
      current = parentOrg || null;
    } else {
      break;
    }
  }

  return path;
}

/**
 * 检查是否可以移动组织（避免循环引用）
 */
export function canMoveOrganization(
  organizationId: string,
  targetParentId: string,
  allOrganizations: Organization[]
): boolean {
  if (organizationId === targetParentId) {
    return false;
  }

  // 检查目标父组织是否是当前组织的子组织
  const isDescendant = (parentId: string, childId: string): boolean => {
    const children = allOrganizations.filter(org => org.parent_id === parentId);
    for (const child of children) {
      if (child.id === childId || isDescendant(child.id, childId)) {
        return true;
      }
    }
    return false;
  };

  return !isDescendant(organizationId, targetParentId);
}

/**
 * 格式化组织显示名称
 */
export function formatOrganizationDisplayName(organization: Organization): string {
  return organization.name;
}

/**
 * 获取组织层级深度
 */
export function getOrganizationDepth(
  organization: Organization,
  allOrganizations: Organization[]
): number {
  let depth = 1;
  let current: Organization | null = organization;

  while (
    current !== null &&
    current !== undefined &&
    current.parent_id !== null &&
    current.parent_id !== undefined &&
    current.parent_id !== ''
  ) {
    depth++;
    const parentOrg = allOrganizations.find(org => org.id === current!.parent_id);
    current = parentOrg || null;
  }

  return depth;
}

/**
 * 获取组织的所有子组织ID（递归）
 */
export function getAllChildOrganizationIds(
  organizationId: string,
  allOrganizations: Organization[]
): string[] {
  const childIds: string[] = [];
  const children = allOrganizations.filter(org => org.parent_id === organizationId);

  for (const child of children) {
    childIds.push(child.id);
    const grandChildren = getAllChildOrganizationIds(child.id, allOrganizations);
    childIds.push(...grandChildren);
  }

  return childIds;
}

// ==================== 带 API 调用的查询方法 ====================

/**
 * 验证组织编码唯一性
 *
 * @param getOrganizations - 获取组织列表的函数（由调用者注入，避免循环依赖）
 */
export async function validateOrganizationCode(
  code: string,
  excludeId: string | undefined,
  getOrganizations: (params?: { page?: number; page_size?: number }) => Promise<Organization[]>
): Promise<{ exists: boolean }> {
  try {
    const organizations = await getOrganizations({ page_size: 1000 });
    const existingOrg = organizations.find(org => org.code === code && org.id !== excludeId);
    return { exists: !!existingOrg };
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    logger.warn('验证组织编码失败', { error: enhancedError.message });
    return { exists: false };
  }
}

/**
 * 获取根级组织列表
 *
 * @param getOrganizations - 获取组织列表的函数（由调用者注入，避免循环依赖）
 */
export async function getRootOrganizations(
  getOrganizations: (params?: { page?: number; page_size?: number }) => Promise<Organization[]>
): Promise<Organization[]> {
  try {
    const organizations = await getOrganizations();
    return organizations.filter(
      org => org.parent_id === null || org.parent_id === undefined || org.parent_id === ''
    );
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    logger.warn('获取根级组织失败', { error: enhancedError.message });
    return [];
  }
}

/**
 * 根据名称查找组织
 *
 * @param getOrganizations - 获取组织列表的函数（由调用者注入，避免循环依赖）
 */
export async function findOrganizationByName(
  name: string,
  getOrganizations: (params?: { page?: number; page_size?: number }) => Promise<Organization[]>
): Promise<Organization | null> {
  try {
    const organizations = await getOrganizations({ page_size: 1000 });
    return organizations.find(org => org.name === name) || null;
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    logger.warn('根据名称查找组织失败', { error: enhancedError.message });
    return null;
  }
}
