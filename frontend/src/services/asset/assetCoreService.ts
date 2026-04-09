/**
 * Asset Core Service
 * 资产核心 CRUD 操作
 */

import { apiClient } from '@/api/client';
import { ownershipService } from '@/services/ownershipService';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { ASSET_API } from '@/constants/api';
import { convertBackendToFrontend } from '@/utils/dataConversion';
import type {
  Asset,
  AssetReviewLog,
  AssetLeaseSummaryResponse,
  AssetSearchParams,
  AssetListResponse,
  AssetCreateRequest,
  AssetUpdateRequest,
  AssetSearchFilters,
} from './types';

const LEGACY_OWNER_FILTER_KEY = `${'ownership'}_${'id'}` as const;

type OwnerFilterCompatibleParams = Record<string, unknown> & {
  owner_party_id?: unknown;
  [LEGACY_OWNER_FILTER_KEY]?: unknown;
};

const normalizeOptionalId = (value: unknown): string | undefined => {
  if (typeof value !== 'string') {
    return undefined;
  }
  const normalized = value.trim();
  return normalized === '' ? undefined : normalized;
};

const withOwnerFilterCompatibility = <T extends Record<string, unknown>>(params: T): T => {
  const ownerFilterParams = params as OwnerFilterCompatibleParams;
  const ownerPartyId = normalizeOptionalId(ownerFilterParams.owner_party_id);
  const legacyOwnerId = normalizeOptionalId(ownerFilterParams[LEGACY_OWNER_FILTER_KEY]);
  const normalizedOwnerId = ownerPartyId ?? legacyOwnerId;

  if (normalizedOwnerId == null) {
    return params;
  }

  return {
    ...params,
    owner_party_id: normalizedOwnerId,
    [LEGACY_OWNER_FILTER_KEY]: normalizedOwnerId,
  };
};

/**
 * 资产核心服务类
 * 提供资产的基础 CRUD 操作
 */
export class AssetCoreService {
  private invalidateAssetCaches(): void {
    apiClient.invalidateCacheByPrefix(`GET:${ASSET_API.LIST}`);
  }

  /**
   * 获取资产列表
   */
  async getAssets(params?: AssetSearchParams): Promise<AssetListResponse> {
    try {
      const { page_size, pageSize, ...restParams } = params ?? {};
      const legacyPageSize = typeof pageSize === 'number' ? pageSize : undefined;
      const normalizedPageSize = page_size ?? legacyPageSize ?? 20;
      const compatibleParams = withOwnerFilterCompatibility(restParams as Record<string, unknown>);

      const result = await apiClient.get<AssetListResponse>(ASSET_API.LIST, {
        params: {
          ...compatibleParams,
          page: params?.page ?? 1,
          page_size: normalizedPageSize,
        },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取资产列表失败: ${result.error}`);
      }

      const payload = result.data ?? {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        pages: 0,
      };
      return convertBackendToFrontend<AssetListResponse>(payload);
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
      const compatibleParams = withOwnerFilterCompatibility(
        (params ?? {}) as Record<string, unknown>
      );
      const result = await apiClient.get<Asset[]>(`${ASSET_API.LIST}/all`, {
        params: {
          ...compatibleParams,
          page_size: 10000,
        },
        cache: true,
        retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取所有资产失败: ${result.error}`);
      }

      return convertBackendToFrontend<Asset[]>(result.data ?? []);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 根据ID列表获取资产
   */
  async getAssetsByIds(ids: string[], options?: { includeRelations?: boolean }): Promise<Asset[]> {
    try {
      const params = options?.includeRelations ? { include_relations: true } : undefined;
      const result = await apiClient.post<Asset[]>(
        `${ASSET_API.LIST}/by-ids`,
        { ids },
        {
          params,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`根据ID列表获取资产失败: ${result.error}`);
      }

      return convertBackendToFrontend<Asset[]>(result.data ?? []);
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

      if (result.data == null) {
        throw new Error('资产详情为空');
      }
      return convertBackendToFrontend<Asset>(result.data);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取资产租赁汇总
   */
  async getAssetLeaseSummary(
    id: string,
    params?: { period_start?: string; period_end?: string }
  ): Promise<AssetLeaseSummaryResponse> {
    try {
      const result = await apiClient.get<AssetLeaseSummaryResponse>(ASSET_API.LEASE_SUMMARY(id), {
        params,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取资产租赁汇总失败: ${result.error}`);
      }

      if (result.data == null) {
        throw new Error('资产租赁汇总为空');
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async submitAssetReview(id: string): Promise<Asset> {
    const result = await apiClient.post<Asset>(ASSET_API.SUBMIT_REVIEW(id), undefined, {
      retry: false,
      smartExtract: true,
    });
    if (!result.success || result.data == null) {
      throw new Error(`提交资产审核失败: ${result.error}`);
    }
    this.invalidateAssetCaches();
    return convertBackendToFrontend<Asset>(result.data);
  }

  async approveAssetReview(id: string): Promise<Asset> {
    const result = await apiClient.post<Asset>(ASSET_API.APPROVE_REVIEW(id), undefined, {
      retry: false,
      smartExtract: true,
    });
    if (!result.success || result.data == null) {
      throw new Error(`审核通过资产失败: ${result.error}`);
    }
    this.invalidateAssetCaches();
    return convertBackendToFrontend<Asset>(result.data);
  }

  async rejectAssetReview(id: string, reason: string): Promise<Asset> {
    const result = await apiClient.post<Asset>(
      ASSET_API.REJECT_REVIEW(id),
      { reason },
      {
        retry: false,
        smartExtract: true,
      }
    );
    if (!result.success || result.data == null) {
      throw new Error(`驳回资产审核失败: ${result.error}`);
    }
    this.invalidateAssetCaches();
    return convertBackendToFrontend<Asset>(result.data);
  }

  async reverseAssetReview(id: string, reason: string): Promise<Asset> {
    const result = await apiClient.post<Asset>(
      ASSET_API.REVERSE_REVIEW(id),
      { reason },
      {
        retry: false,
        smartExtract: true,
      }
    );
    if (!result.success || result.data == null) {
      throw new Error(`反审核资产失败: ${result.error}`);
    }
    this.invalidateAssetCaches();
    return convertBackendToFrontend<Asset>(result.data);
  }

  async resubmitAssetReview(id: string): Promise<Asset> {
    const result = await apiClient.post<Asset>(ASSET_API.RESUBMIT_REVIEW(id), undefined, {
      retry: false,
      smartExtract: true,
    });
    if (!result.success || result.data == null) {
      throw new Error(`重提资产审核失败: ${result.error}`);
    }
    this.invalidateAssetCaches();
    return convertBackendToFrontend<Asset>(result.data);
  }

  async withdrawAssetReview(id: string, reason?: string): Promise<Asset> {
    const result = await apiClient.post<Asset>(
      ASSET_API.WITHDRAW_REVIEW(id),
      reason != null && reason.trim() !== '' ? { reason } : undefined,
      {
        retry: false,
        smartExtract: true,
      }
    );
    if (!result.success || result.data == null) {
      throw new Error(`撤回资产审核失败: ${result.error}`);
    }
    this.invalidateAssetCaches();
    return convertBackendToFrontend<Asset>(result.data);
  }

  async getAssetReviewLogs(id: string): Promise<AssetReviewLog[]> {
    const result = await apiClient.get<AssetReviewLog[]>(ASSET_API.REVIEW_LOGS(id), {
      cache: false,
      retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
      smartExtract: true,
    });
    if (!result.success || result.data == null) {
      throw new Error(`获取资产审核历史失败: ${result.error}`);
    }
    return convertBackendToFrontend<AssetReviewLog[]>(result.data);
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

      this.invalidateAssetCaches();
      if (result.data == null) {
        throw new Error('创建资产返回为空');
      }
      return convertBackendToFrontend<Asset>(result.data);
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

      this.invalidateAssetCaches();
      if (result.data == null) {
        throw new Error('更新资产返回为空');
      }
      return convertBackendToFrontend<Asset>(result.data);
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

      this.invalidateAssetCaches();
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 恢复资产（仅管理员）
   */
  async restoreAsset(id: string): Promise<Asset> {
    try {
      const result = await apiClient.post<Asset>(
        ASSET_API.RESTORE(id),
        {},
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`恢复资产失败: ${result.error}`);
      }

      this.invalidateAssetCaches();
      if (result.data == null) {
        throw new Error('恢复资产返回为空');
      }
      return convertBackendToFrontend<Asset>(result.data);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 彻底删除资产（仅管理员）
   */
  async hardDeleteAsset(id: string): Promise<void> {
    try {
      const result = await apiClient.delete<void>(ASSET_API.HARD_DELETE(id), {
        retry: false,
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`彻底删除资产失败: ${result.error}`);
      }

      this.invalidateAssetCaches();
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
        { asset_ids: ids },
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`批量删除资产失败: ${result.error}`);
      }

      this.invalidateAssetCaches();
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 搜索资产
   */
  async searchAssets(query: string, filters?: AssetSearchFilters): Promise<AssetListResponse> {
    const normalizedFilters = (filters ?? {}) as Partial<AssetSearchParams>;
    return this.getAssets({
      search: query,
      ...normalizedFilters,
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
   * 获取权属方选项列表
   */
  async getOwnershipEntities(): Promise<Array<{ value: string; label: string }>> {
    return ownershipService.getOwnershipSelectOptions();
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
