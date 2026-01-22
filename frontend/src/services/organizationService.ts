/**
 * 组织架构管理服务 - 统一响应处理版本
 *
 * @description 组织架构管理核心服务，提供组织树、搜索、批量操作等完整功能
 * @author Claude Code
 */

import {
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
  OrganizationTree,
  OrganizationHistory,
  OrganizationStatistics,
  OrganizationMoveRequest,
  OrganizationBatchRequest,
  OrganizationBatchResult,
  OrganizationMoveResult,
  OrganizationPath,
  OrganizationSearchCriteria,
} from '../types/organization';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '../utils/responseExtractor';
import { createLogger } from '../utils/logger';

const logger = createLogger('OrganizationService');

// 树节点接口
interface TreeNode {
  key: string;
  value: string;
  title: string;
  children?: TreeNode[];
}

class OrganizationService {
  private baseUrl = '/organizations';

  // ==================== 基础CRUD操作 ====================

  /**
   * 获取组织列表
   */
  async getOrganizations(params?: { skip?: number; limit?: number }): Promise<Organization[]> {
    try {
      const result = await apiClient.get<Organization[]>(this.baseUrl, {
        params: { ...params, skip: params?.skip ?? 0, limit: params?.limit ?? 100 },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取组织列表失败: ${result.error}`);
      }

      return result.data ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      // eslint-disable-next-line no-console
      console.error('获取组织列表失败:', enhancedError.message);
      return [];
    }
  }

  /**
   * 根据ID获取组织详情
   */
  async getOrganization(id: string): Promise<Organization> {
    try {
      const result = await apiClient.get<Organization>(`${this.baseUrl}/${id}`, {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取组织详情失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 创建组织
   */
  async createOrganization(organization: OrganizationCreate): Promise<Organization> {
    try {
      const result = await apiClient.post<Organization>(this.baseUrl, organization, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`创建组织失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新组织
   */
  async updateOrganization(id: string, organization: OrganizationUpdate): Promise<Organization> {
    try {
      const result = await apiClient.put<Organization>(
        `${this.baseUrl}/${id}`,
        organization,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`更新组织失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 删除组织
   */
  async deleteOrganization(id: string, deletedBy?: string): Promise<void> {
    try {
      const params =
        deletedBy !== null && deletedBy !== undefined && deletedBy !== ''
          ? { deleted_by: deletedBy }
          : {};
      const result = await apiClient.delete<void>(`${this.baseUrl}/${id}`, {
        params,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

      if (!result.success) {
        throw new Error(`删除组织失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 组织树形结构 ====================

  /**
   * 获取组织树形结构
   */
  async getOrganizationTree(parentId?: string): Promise<OrganizationTree[]> {
    try {
      const params =
        parentId !== null && parentId !== undefined && parentId !== ''
          ? { parent_id: parentId }
          : {};
      const result = await apiClient.get<OrganizationTree[]>(`${this.baseUrl}/tree`, {
        params,
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取组织树失�? ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      // eslint-disable-next-line no-console
      console.error('获取组织树失�?', enhancedError.message);
      return [];
    }
  }

  /**
   * 获取组织的子组织
   */
  async getOrganizationChildren(id: string, recursive: boolean = false): Promise<Organization[]> {
    try {
      const result = await apiClient.get<Organization[]>(`${this.baseUrl}/${id}/children`, {
        params: { recursive },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取子组织失�? ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取组织到根节点的路�?   */
  async getOrganizationPath(id: string): Promise<OrganizationPath> {
    try {
      const result = await apiClient.get<Organization[]>(`${this.baseUrl}/${id}/path`, {
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
  async searchOrganizations(
    keyword: string,
    params?: { skip?: number; limit?: number }
  ): Promise<Organization[]> {
    try {
      const result = await apiClient.get<Organization[]>(`${this.baseUrl}/search`, {
        params: { keyword, ...params, skip: params?.skip ?? 0, limit: params?.limit ?? 20 },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`搜索组织失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 高级搜索组织
   */
  async detailedSearchOrganizations(
    searchRequest: OrganizationSearchCriteria
  ): Promise<Organization[]> {
    try {
      const result = await apiClient.post<Organization[]>(
        `${this.baseUrl}/advanced-search`,
        searchRequest,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`高级搜索组织失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 统计和分�?====================

  /**
   * 获取组织统计信息
   */
  async getStatistics(): Promise<OrganizationStatistics> {
    try {
      const result = await apiClient.get<OrganizationStatistics>(
        `${this.baseUrl}/statistics`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

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
  async getOrganizationHistory(
    id: string,
    params?: { skip?: number; limit?: number }
  ): Promise<OrganizationHistory[]> {
    try {
      const result = await apiClient.get<OrganizationHistory[]>(
        `${this.baseUrl}/${id}/history`,
        {
          params: { ...params, skip: params?.skip ?? 0, limit: params?.limit ?? 20 },
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取组织历史失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 组织操作 ====================

  /**
   * 移动组织
   */
  async moveOrganization(
    id: string,
    moveRequest: OrganizationMoveRequest
  ): Promise<OrganizationMoveResult> {
    try {
      const result = await apiClient.post<OrganizationMoveResult>(
        `${this.baseUrl}/${id}/move`,
        moveRequest,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`移动组织失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 批量操作组织
   */
  async batchOrganizationOperation(
    batchRequest: OrganizationBatchRequest
  ): Promise<OrganizationBatchResult> {
    try {
      const result = await apiClient.post<OrganizationBatchResult>(
        `${this.baseUrl}/batch`,
        batchRequest,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`批量操作组织失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 批量删除组织
   */
  async batchDeleteOrganizations(
    organizationIds: string[],
    deletedBy?: string
  ): Promise<OrganizationBatchResult> {
    try {
      return await this.batchOrganizationOperation({
        organization_ids: organizationIds,
        action: 'delete',
        updated_by: deletedBy,
      });
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 导入导出功能 ====================

  /**
   * 导出组织数据
   */
  async exportOrganizations(format: 'excel' | 'csv' = 'excel'): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(`${this.baseUrl}/export`, {
        params: { format },
        responseType: 'blob',
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

      if (!result.success) {
        throw new Error(`导出组织数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 导入组织数据
   */
  async importOrganizations(file: File): Promise<{
    success: boolean;
    message: string;
    data?: unknown;
  }> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const result = await apiClient.post<{
        success: boolean;
        message: string;
        data?: unknown;
      }>(`${this.baseUrl}/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`导入组织数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 工具方法 ====================

  /**
   * 构建组织树形数据
   */
  buildOrganizationTreeData(organizations: Organization[]): TreeNode[] {
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
          // 找到父节点并添加子节�?          this.addChildToTreeNode(treeData, org.parent_id, treeNode);
        }
      }
    });

    return treeData;
  }

  /**
   * 向树节点添加子节�?   */
  private addChildToTreeNode(treeData: TreeNode[], parentId: string, childNode: TreeNode): boolean {
    for (const node of treeData) {
      if (node.key === parentId) {
        node.children = node.children ?? [];
        node.children.push(childNode);
        return true;
      }
      if (node.children && this.addChildToTreeNode(node.children, parentId, childNode)) {
        return true;
      }
    }
    return false;
  }

  /**
   * 获取组织层级路径
   */
  getOrganizationLevelPath(organization: Organization, allOrganizations: Organization[]): string[] {
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
   * 检查是否可以移动组织（避免循环引用�?   */
  canMoveOrganization(
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
  formatOrganizationDisplayName(organization: Organization): string {
    return organization.name;
  }

  /**
   * 获取组织层级深度
   */
  getOrganizationDepth(organization: Organization, allOrganizations: Organization[]): number {
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
   * 获取组织的所有子组织ID（递归�?   */
  getAllChildOrganizationIds(organizationId: string, allOrganizations: Organization[]): string[] {
    const childIds: string[] = [];
    const children = allOrganizations.filter(org => org.parent_id === organizationId);

    for (const child of children) {
      childIds.push(child.id);
      const grandChildren = this.getAllChildOrganizationIds(child.id, allOrganizations);
      childIds.push(...grandChildren);
    }

    return childIds;
  }

  /**
   * 验证组织编码唯一�?   */
  async validateOrganizationCode(code: string, excludeId?: string): Promise<{ exists: boolean }> {
    try {
      const organizations = await this.getOrganizations({ limit: 1000 });
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
   */
  async getRootOrganizations(): Promise<Organization[]> {
    try {
      const organizations = await this.getOrganizations();
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
   */
  async findOrganizationByName(name: string): Promise<Organization | null> {
    try {
      const organizations = await this.getOrganizations({ limit: 1000 });
      return organizations.find(org => org.name === name) || null;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('根据名称查找组织失败', { error: enhancedError.message });
      return null;
    }
  }
}

export const organizationService = new OrganizationService();
