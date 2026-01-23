/**
 * 权属方相关服务 - 统一响应处理版本
 *
 * @description 权属方管理核心服务，提供权属方CRUD、搜索、统计等完整功能
 * @author Claude Code
 */

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '../utils/responseExtractor';
import { API_ENDPOINTS } from '@/constants/api';
import { createLogger } from '../utils/logger';

const ownershipLogger = createLogger('Ownership');
import type {
  Ownership,
  OwnershipCreate,
  OwnershipUpdate,
  OwnershipListResponse,
  OwnershipSearchRequest,
  OwnershipStatisticsResponse,
  OwnershipDeleteResponse,
  OwnershipSearchParams,
  OwnershipDropdownOption,
} from '@/types/ownership';

export class OwnershipService {
  private baseUrl = API_ENDPOINTS.OWNERSHIP.LIST;

  // ==================== 基础CRUD操作 ====================

  /**
   * 搜索权属方
   */
  async searchOwnerships(searchParams: OwnershipSearchRequest): Promise<OwnershipListResponse> {
    try {
      const result = await apiClient.post<OwnershipListResponse>(
        `${this.baseUrl}/search`,
        searchParams,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`搜索权属方失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取权属方详情
   */
  async getOwnership(id: string): Promise<Ownership> {
    try {
      const result = await apiClient.get<Ownership>(API_ENDPOINTS.OWNERSHIP.DETAIL(id), {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取权属方详情失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取权属方列表
   */
  async getOwnerships(params?: OwnershipSearchParams): Promise<OwnershipListResponse> {
    try {
      // 确保提供必需的分页参数
      const requestParams = {
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 10,
        keyword: params?.keyword,
        is_active: params?.is_active,
      };

      const result = await apiClient.get<OwnershipListResponse>(this.baseUrl, {
        params: requestParams,
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取权属方列表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 创建权属方
   */
  async createOwnership(data: OwnershipCreate): Promise<Ownership> {
    try {
      const result = await apiClient.post<Ownership>(this.baseUrl, data, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`创建权属方失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新权属方
   */
  async updateOwnership(id: string, data: OwnershipUpdate): Promise<Ownership> {
    try {
      const result = await apiClient.put<Ownership>(API_ENDPOINTS.OWNERSHIP.UPDATE(id), data, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`更新权属方失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 删除权属方
   */
  async deleteOwnership(id: string): Promise<OwnershipDeleteResponse> {
    try {
      const result = await apiClient.delete<OwnershipDeleteResponse>(
        API_ENDPOINTS.OWNERSHIP.DELETE(id),
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`删除权属方失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 权属方操作 ====================

  /**
   * 切换权属方状态
   */
  async toggleOwnershipStatus(id: string): Promise<Ownership> {
    try {
      const result = await apiClient.put<Ownership>(
        `${this.baseUrl}/${id}/status`,
        {},
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`切换权属方状态失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取权属方统计信息
   */
  async getOwnershipStatistics(): Promise<OwnershipStatisticsResponse> {
    try {
      const result = await apiClient.get<OwnershipStatisticsResponse>(`${this.baseUrl}/stats/overview`, {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        });

      if (!result.success) {
        throw new Error(`获取权属方统计失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取权属方选项列表
   */
  async getOwnershipOptions(isActive: boolean = true): Promise<OwnershipDropdownOption[]> {
    try {
      const result = await apiClient.get<OwnershipDropdownOption[]>(
        `${this.baseUrl}/dropdown-options?is_active=${isActive}`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取权属方选项失败: ${result.error}`);
      }

      // 确保返回数组格式
      const data = result.data!;
      if (Array.isArray(data)) return data;
      const possibleData = (data as Record<string, unknown>).data;
      return Array.isArray(possibleData) ? (possibleData as OwnershipDropdownOption[]) : [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 验证功能 ====================

  /**
   * 验证权属方编码唯一性
   */
  async validateOwnershipCode(code: string, excludeId?: string): Promise<boolean> {
    try {
      const result = await this.getOwnerships({ keyword: code });
      return !result.items.some(item => item.code === code && item.id !== excludeId);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      ownershipLogger.error('验证权属方编码失败:', undefined, { error: enhancedError.message });
      return false;
    }
  }

  /**
   * 验证权属方名称唯一性
   */
  async validateOwnershipName(name: string, excludeId?: string): Promise<boolean> {
    try {
      const result = await this.getOwnerships({ keyword: name });
      return !result.items.some(item => item.name === name && item.id !== excludeId);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      ownershipLogger.error('验证权属方名称失败:', undefined, { error: enhancedError.message });
      return false;
    }
  }

  // ==================== 查询功能 ====================

  /**
   * 根据条件获取权属方数量
   */
  async getOwnershipCount(params?: OwnershipSearchParams): Promise<number> {
    try {
      const result = await this.getOwnerships({ ...params, page_size: 1 });
      return result.total;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      ownershipLogger.error('获取权属方数量失败:', undefined, { error: enhancedError.message });
      return 0;
    }
  }

  /**
   * 检查权属方是否可以删除
   */
  async canDeleteOwnership(id: string): Promise<{ canDelete: boolean; reason?: string }> {
    try {
      const ownership = await this.getOwnership(id);
      if (ownership == null) {
        return { canDelete: false, reason: '权属方不存在' };
      }

      // 检查是否有关联的资产或项目
      if ((ownership.asset_count ?? 0) > 0) {
        return {
          canDelete: false,
          reason: `该权属方还有 ${ownership.asset_count} 个关联资产，无法删除`,
        };
      }

      return { canDelete: true };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      ownershipLogger.error('检查权属方删除条件失败:', undefined, { error: enhancedError.message });
      return { canDelete: false, reason: '检查失败，请稍后重试' };
    }
  }

  /**
   * 获取权属方下拉选项（简化版）
   */
  async getOwnershipSelectOptions(): Promise<Array<{ value: string; label: string }>> {
    try {
      const options = await this.getOwnershipOptions();
      return options.map(option => ({
        value: option.id,
        label: `${option.name} (${option.code})`,
      }));
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      ownershipLogger.error('获取权属方选择选项失败:', undefined, { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 根据关键词搜索权属方
   */
  async searchOwnershipsByKeyword(keyword: string): Promise<Ownership[]> {
    try {
      const result = await this.searchOwnerships({ keyword, page: 1, page_size: 100 });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      ownershipLogger.error('关键词搜索权属方失败:', undefined, { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取活跃权属方列表
   */
  async getActiveOwnerships(): Promise<Ownership[]> {
    try {
      const result = await this.getOwnerships({ is_active: true });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      ownershipLogger.error('获取活跃权属方失败:', undefined, { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取非活跃权属方列表
   */
  async getInactiveOwnerships(): Promise<Ownership[]> {
    try {
      const result = await this.getOwnerships({ is_active: false });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      ownershipLogger.error('获取非活跃权属方失败:', undefined, { error: enhancedError.message });
      return [];
    }
  }

  // ==================== 高级功能 ====================

  /**
   * 权属方数据导出
   */
  async exportOwnerships(
    format: 'excel' | 'csv' = 'excel',
    filters?: OwnershipSearchParams
  ): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(`${this.baseUrl}/export`, {
        params: { format, ...filters },
        responseType: 'blob',
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

      if (!result.success) {
        throw new Error(`导出权属方数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 权属方数据导入
   */
  async importOwnerships(file: File): Promise<{
    success: boolean;
    message: string;
    imported?: number;
    errors?: string[];
  }> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const result = await apiClient.post<{
        success: boolean;
        message: string;
        imported?: number;
        errors?: string[];
      }>(`${this.baseUrl}/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`导入权属方数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

// 创建单例实例
export const ownershipService = new OwnershipService();
