/**
 * 权属方相关服务
 */

import { API_BASE_URL } from '@/config/api';
import { apiRequest } from '@/utils/request';
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
  private baseUrl = `${API_BASE_URL}/ownerships`;

  /**
   * 获取权属方列表
   */
  async getOwnerships(params?: OwnershipSearchParams): Promise<OwnershipListResponse> {
    const searchParams = new URLSearchParams();

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
    }

    const response = await apiRequest.get(`${this.baseUrl}?${searchParams.toString()}`);
    return response.data;
  }

  /**
   * 搜索权属方
   */
  async searchOwnerships(searchParams: OwnershipSearchRequest): Promise<OwnershipListResponse> {
    const response = await apiRequest.post(`${this.baseUrl}/search`, searchParams);
    return response.data;
  }

  /**
   * 获取权属方详情
   */
  async getOwnership(id: string): Promise<Ownership> {
    const response = await apiRequest.get(`${this.baseUrl}/${id}`);
    return response.data;
  }

  /**
   * 创建权属方
   */
  async createOwnership(data: OwnershipCreate): Promise<Ownership> {
    const response = await apiRequest.post(this.baseUrl, data);
    return response.data;
  }

  /**
   * 更新权属方
   */
  async updateOwnership(id: string, data: OwnershipUpdate): Promise<Ownership> {
    const response = await apiRequest.put(`${this.baseUrl}/${id}`, data);
    return response.data;
  }

  /**
   * 删除权属方
   */
  async deleteOwnership(id: string): Promise<OwnershipDeleteResponse> {
    const response = await apiRequest.delete(`${this.baseUrl}/${id}`);
    return response.data;
  }

  /**
   * 切换权属方状态
   */
  async toggleOwnershipStatus(id: string): Promise<Ownership> {
    const response = await apiRequest.post(`${this.baseUrl}/${id}/toggle-status`);
    return response.data;
  }

  /**
   * 获取权属方统计信息
   */
  async getOwnershipStatistics(): Promise<OwnershipStatisticsResponse> {
    const response = await apiRequest.get(`${this.baseUrl}/statistics/summary`);
    return response.data;
  }

  
  /**
   * 获取权属方选项列表
   */
  async getOwnershipOptions(isActive: boolean = true): Promise<Ownership[]> {
    const response = await apiRequest.get(`${this.baseUrl}/options?is_active=${isActive}`);
    return response.data;
  }

  /**
   * 验证权属方编码唯一性
   */
  async validateOwnershipCode(code: string, excludeId?: string): Promise<boolean> {
    try {
      const result = await this.getOwnerships({ keyword: code });
      return !result.items.some(item =>
        item.code === code && item.id !== excludeId
      );
    } catch (error) {
      console.error('验证权属方编码失败:', error);
      return false;
    }
  }

  /**
   * 验证权属方名称唯一性
   */
  async validateOwnershipName(name: string, excludeId?: string): Promise<boolean> {
    try {
      const result = await this.getOwnerships({ keyword: name });
      return !result.items.some(item =>
        item.name === name && item.id !== excludeId
      );
    } catch (error) {
      console.error('验证权属方名称失败:', error);
      return false;
    }
  }
}

// 创建单例实例
export const ownershipService = new OwnershipService();