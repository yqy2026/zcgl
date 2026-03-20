/**
 * 组织架构管理服务 - 统一响应处理版本
 *
 * @description 组织架构管理核心服务，提供组织树、搜索、批量操作等完整功能。
 *              查询/搜索/工具逻辑已提取至 organizationQuery.ts，本文件作为 hub 保持完整的对外 API。
 * @author Claude Code
 */

import {
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
  OrganizationMoveRequest,
  OrganizationBatchRequest,
  OrganizationBatchResult,
  OrganizationMoveResult,
} from '@/types/organization';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import {
  getOrganizationReadOnlyErrorMessage,
  isOrganizationWriteEnabled,
} from '@/constants/organization';

import {
  extractList,
  fetchOrganizationTree,
  fetchOrganizationChildren,
  fetchOrganizationPath,
  searchOrganizations as searchOrganizationsImpl,
  detailedSearchOrganizations as detailedSearchOrganizationsImpl,
  fetchStatistics,
  fetchOrganizationHistory,
  buildOrganizationTreeData as buildOrganizationTreeDataImpl,
  getOrganizationLevelPath as getOrganizationLevelPathImpl,
  canMoveOrganization as canMoveOrganizationImpl,
  formatOrganizationDisplayName as formatOrganizationDisplayNameImpl,
  getOrganizationDepth as getOrganizationDepthImpl,
  getAllChildOrganizationIds as getAllChildOrganizationIdsImpl,
  validateOrganizationCode as validateOrganizationCodeImpl,
  getRootOrganizations as getRootOrganizationsImpl,
  findOrganizationByName as findOrganizationByNameImpl,
} from './organizationQuery';

import type { TreeNode } from './organizationQuery';
export type { TreeNode };

class OrganizationService {
  private baseUrl = '/organizations';

  private assertWriteAllowed(actionLabel: string): void {
    if (isOrganizationWriteEnabled()) {
      return;
    }
    throw new Error(getOrganizationReadOnlyErrorMessage(actionLabel));
  }

  // ==================== 基础CRUD操作 ====================

  /**
   * 获取组织列表
   */
  async getOrganizations(params?: { page?: number; page_size?: number }): Promise<Organization[]> {
    try {
      const result = await apiClient.get<Organization[]>(this.baseUrl, {
        params: { ...params, page: params?.page ?? 1, page_size: params?.page_size ?? 100 },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取组织列表失败: ${result.error}`);
      }

      return extractList<Organization>(result.data);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
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
      this.assertWriteAllowed('新增组织');
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
      this.assertWriteAllowed('编辑组织');
      const result = await apiClient.put<Organization>(`${this.baseUrl}/${id}`, organization, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

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
      this.assertWriteAllowed('删除组织');
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

  // ==================== 组织树形结构（委托 organizationQuery） ====================

  async getOrganizationTree(...args: Parameters<typeof fetchOrganizationTree>) {
    return fetchOrganizationTree(...args);
  }

  async getOrganizationChildren(...args: Parameters<typeof fetchOrganizationChildren>) {
    return fetchOrganizationChildren(...args);
  }

  async getOrganizationPath(...args: Parameters<typeof fetchOrganizationPath>) {
    return fetchOrganizationPath(...args);
  }

  // ==================== 搜索功能（委托 organizationQuery） ====================

  async searchOrganizations(...args: Parameters<typeof searchOrganizationsImpl>) {
    return searchOrganizationsImpl(...args);
  }

  async detailedSearchOrganizations(
    ...args: Parameters<typeof detailedSearchOrganizationsImpl>
  ) {
    return detailedSearchOrganizationsImpl(...args);
  }

  // ==================== 统计和分析（委托 organizationQuery） ====================

  async getStatistics() {
    return fetchStatistics();
  }

  async getOrganizationHistory(...args: Parameters<typeof fetchOrganizationHistory>) {
    return fetchOrganizationHistory(...args);
  }

  // ==================== 组织操作（写入） ====================

  /**
   * 移动组织
   */
  async moveOrganization(
    id: string,
    moveRequest: OrganizationMoveRequest
  ): Promise<OrganizationMoveResult> {
    try {
      this.assertWriteAllowed('移动组织');
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
      this.assertWriteAllowed('批量组织操作');
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
      this.assertWriteAllowed('导入组织');
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

  // ==================== 工具方法（委托 organizationQuery） ====================

  buildOrganizationTreeData(...args: Parameters<typeof buildOrganizationTreeDataImpl>) {
    return buildOrganizationTreeDataImpl(...args);
  }

  getOrganizationLevelPath(...args: Parameters<typeof getOrganizationLevelPathImpl>) {
    return getOrganizationLevelPathImpl(...args);
  }

  canMoveOrganization(...args: Parameters<typeof canMoveOrganizationImpl>) {
    return canMoveOrganizationImpl(...args);
  }

  formatOrganizationDisplayName(...args: Parameters<typeof formatOrganizationDisplayNameImpl>) {
    return formatOrganizationDisplayNameImpl(...args);
  }

  getOrganizationDepth(...args: Parameters<typeof getOrganizationDepthImpl>) {
    return getOrganizationDepthImpl(...args);
  }

  getAllChildOrganizationIds(...args: Parameters<typeof getAllChildOrganizationIdsImpl>) {
    return getAllChildOrganizationIdsImpl(...args);
  }

  // ==================== 带 API 查询的工具方法（委托 organizationQuery） ====================

  async validateOrganizationCode(code: string, excludeId?: string) {
    return validateOrganizationCodeImpl(code, excludeId, (params) =>
      this.getOrganizations(params)
    );
  }

  async getRootOrganizations() {
    return getRootOrganizationsImpl((params) => this.getOrganizations(params));
  }

  async findOrganizationByName(name: string) {
    return findOrganizationByNameImpl(name, (params) => this.getOrganizations(params));
  }
}

export const organizationService = new OrganizationService();
