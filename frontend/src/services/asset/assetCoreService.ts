/**
 * Asset Core Service
 * 资产核心 CRUD 操作
 */

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '../../utils/responseExtractor';
import { ASSET_API } from '../../constants/api';
import type {
  Asset,
  AssetSearchParams,
  AssetListResponse,
  AssetCreateRequest,
  AssetUpdateRequest,
  AssetSearchFilters,
} from './types';

/**
 * 资产核心服务类
 * 提供资产的基础 CRUD 操作
 */
export class AssetCoreService {
  /**
   * 获取资产列表
   */
  async getAssets(params?: AssetSearchParams): Promise<AssetListResponse> {
    try {
      const result = await apiClient.get<AssetListResponse>(ASSET_API.LIST, {
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
        throw new Error(`获取资产列表失败: ${result.error}`);
      }

      return (
        result.data ?? {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          pages: 0,
        }
      );
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取所有资产（不分页，用于导出等场景）
   */
  async getAllAssets(params?: Omit<AssetSearchParams, 'page' | 'page_size'>): Promise<Asset[]> {
    try {
      const result = await apiClient.get<Asset[]>(`${ASSET_API.LIST}/all`, {
        params: {
          ...params,
          page_size: 10000,
        },
        cache: true,
        retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取所有资产失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 根据ID列表获取资产
   */
  async getAssetsByIds(ids: string[]): Promise<Asset[]> {
    try {
      const result = await apiClient.post<Asset[]>(
        `${ASSET_API.LIST}/by-ids`,
        { ids },
        {
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`根据ID列表获取资产失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取单个资产
   */
  async getAsset(id: string): Promise<Asset> {
    try {
      const result = await apiClient.get<Asset>(ASSET_API.DETAIL(id), {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取资产详情失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 创建资产
   */
  async createAsset(data: AssetCreateRequest): Promise<Asset> {
    try {
      const result = await apiClient.post<Asset>(ASSET_API.CREATE, data, {
        retry: false,
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`创建资产失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新资产
   */
  async updateAsset(id: string, data: AssetUpdateRequest): Promise<Asset> {
    try {
      const result = await apiClient.put<Asset>(ASSET_API.UPDATE(id), data, {
        retry: false,
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`更新资产失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 删除资产
   */
  async deleteAsset(id: string): Promise<void> {
    try {
      const result = await apiClient.delete<void>(ASSET_API.DELETE(id), {
        retry: false,
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`删除资产失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 批量删除资产
   */
  async deleteAssets(ids: string[]): Promise<void> {
    try {
      const result = await apiClient.post<void>(
        ASSET_API.BATCH_DELETE,
        { ids },
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`批量删除资产失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 搜索资产
   */
  async searchAssets(query: string, filters?: AssetSearchFilters): Promise<AssetListResponse> {
    return this.getAssets({
      search: query,
      ...filters,
    });
  }

  /**
   * 验证资产数据
   */
  async validateAsset(data: AssetCreateRequest | AssetUpdateRequest): Promise<{
    valid: boolean;
    errors: string[];
  }> {
    try {
      const result = await apiClient.post<{
        is_valid: boolean;
        errors: Array<{ field?: string; message?: string }>;
        warnings: Array<{ field?: string; message?: string }>;
      }>(
        `${ASSET_API.LIST}/validate`,
        { data },
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success) {
        return {
          valid: false,
          errors: [result.error ?? '验证失败'],
        };
      }

      return {
        valid: Boolean(result.data?.is_valid),
        errors: (result.data?.errors ?? []).map(e => e.message ?? '验证失败'),
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      return {
        valid: false,
        errors: [enhancedError.message],
      };
    }
  }

  /**
   * 获取权属方列表
   */
  async getOwnershipEntities(): Promise<string[]> {
    try {
      const result = await apiClient.get<string[]>(ASSET_API.OWNERSHIP_ENTITIES, {
        timeout: 3000,
        cache: true,
        retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取权属方列表失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取业态类别列表
   */
  async getBusinessCategories(): Promise<string[]> {
    try {
      const result = await apiClient.get<string[]>(ASSET_API.BUSINESS_CATEGORIES, {
        timeout: 3000,
        cache: true,
        retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取业态类别失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取管理实体列表
   */
  async getManagementEntities(): Promise<string[]> {
    try {
      const result = await apiClient.get<string[]>('/assets/management-entities', {
        timeout: 3000,
        cache: true,
        retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取管理实体列表失败: ${result.error}`);
      }

      return result.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

// 导出服务实例
export const assetCoreService = new AssetCoreService();
