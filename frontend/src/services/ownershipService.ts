/**
 * 权属方相关服务
 */

import { apiClient } from './api';
import type {
  Ownership,
  OwnershipCreate,
  OwnershipUpdate,
  OwnershipListResponse,
  OwnershipSearchRequest,
  OwnershipStatisticsResponse,
  OwnershipDeleteResponse,
  OwnershipSearchParams
} from '@/types/ownership';

export class OwnershipService {
  private baseUrl = '/ownerships';

  /**
   * 获取权属方列表
   */
  async getOwnerships(params?: OwnershipSearchParams): Promise<OwnershipListResponse> {
    const response = await apiClient.get(this.baseUrl, { params });
    return response;
  }

  /**
   * 搜索权属方
   */
  async searchOwnerships(searchParams: OwnershipSearchRequest): Promise<OwnershipListResponse> {
    const response = await apiClient.post(`${this.baseUrl}/search`, searchParams);
    return response;
  }

  /**
   * 获取权属方详情
   */
  async getOwnership(id: string): Promise<Ownership> {
    const response = await apiClient.get(`${this.baseUrl}/${id}`);
    return response;
  }

  /**
   * 创建权属方
   */
  async createOwnership(data: OwnershipCreate): Promise<Ownership> {
    const response = await apiClient.post(this.baseUrl, data);
    return response;
  }

  
  /**
   * 更新权属方
   */
  async updateOwnership(id: string, data: OwnershipUpdate): Promise<Ownership> {
    const response = await apiClient.put(`${this.baseUrl}/${id}`, data);
    return response;
  }

  /**
   * 删除权属方
   */
  async deleteOwnership(id: string): Promise<OwnershipDeleteResponse> {
    const response = await apiClient.delete(`${this.baseUrl}/${id}`);
    return response;
  }

  /**
   * 切换权属方状态
   */
  async toggleOwnershipStatus(id: string): Promise<Ownership> {
    const response = await apiClient.post(`${this.baseUrl}/${id}/toggle-status`);
    return response;
  }

  /**
   * 获取权属方统计信息
   */
  async getOwnershipStatistics(): Promise<OwnershipStatisticsResponse> {
    const response = await apiClient.get(`${this.baseUrl}/statistics/summary`);
    return response;
  }

  
  /**
   * 获取权属方选项列表
   */
  async getOwnershipOptions(isActive: boolean = true): Promise<Ownership[]> {
    const response = await apiClient.get(`${this.baseUrl}/dropdown-options?is_active=${isActive}`);
    return response;
  }

  /**
   * 验证权属方名称唯一性
   */
  async validateOwnershipName(name: string, excludeId?: string): Promise<boolean> {
    try {
      // 使用精确搜索来验证名称唯一性
      const result = await this.getOwnerships({ keyword: name });

      // 检查是否有完全匹配的名称
      const exactMatch = result.items.find(item => item.name === name);

      // 如果存在完全匹配且不是当前编辑的权属方，则名称不可用
      return !exactMatch || (excludeId && exactMatch.id === excludeId);
    } catch (error) {
      console.error('验证权属方名称失败:', error);
      return false;
    }
  }

  /**
   * 验证权属方编码唯一性
   */
  async validateOwnershipCode(code: string, excludeId?: string): Promise<boolean> {
    try {
      // 获取所有权属方来验证编码唯一性
      const result = await this.getOwnerships();

      // 检查是否有完全匹配的编码
      const exactMatch = result.items.find(item => item.code === code);

      // 如果存在完全匹配且不是当前编辑的权属方，则编码不可用
      return !exactMatch || (excludeId && exactMatch.id === excludeId);
    } catch (error) {
      console.error('验证权属方编码失败:', error);
      return false;
    }
  }

  /**
   * 更新权属方关联项目
   */
  async updateOwnershipProjects(ownershipId: string, projectIds: string[]): Promise<void> {
    try {
      const response = await apiClient.put(`${this.baseUrl}/${ownershipId}/projects`, projectIds);
      return response;
    } catch (error) {
      console.error('更新权属方关联项目失败:', error);
      throw error;
    }
  }
}

// 创建单例实例
export const ownershipService = new OwnershipService();