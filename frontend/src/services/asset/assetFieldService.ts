/**
 * Asset Field Service
 * 资产自定义字段相关操作
 */

import { enhancedApiClient } from '@/api/client';
import { ApiErrorHandler } from '../../utils/responseExtractor';
import type {
  AssetCustomField,
  CustomFieldValue,
  FieldOption,
  FieldValidationResult,
} from './types';

/**
 * 资产字段服务类
 * 提供自定义字段的管理功能
 */
export class AssetFieldService {
  /**
   * 获取资产自定义字段配置
   */
  async getAssetCustomFields(assetId?: string): Promise<AssetCustomField[]> {
    try {
      const result = await enhancedApiClient.get<AssetCustomField[]>('/asset-custom-fields', {
        params:
          assetId !== null && assetId !== undefined && assetId !== ''
            ? { asset_id: assetId }
            : undefined,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取资产自定义字段配置失败: ${result.error}`);
      }

      return result.data ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取单个自定义字段配置
   */
  async getAssetCustomField(id: string): Promise<AssetCustomField> {
    try {
      const result = await enhancedApiClient.get<AssetCustomField>(`/asset-custom-fields/${id}`, {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取自定义字段配置失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 创建自定义字段配置
   */
  async createAssetCustomField(
    data: Omit<AssetCustomField, 'id' | 'created_at' | 'updated_at'>
  ): Promise<AssetCustomField> {
    try {
      const result = await enhancedApiClient.post<AssetCustomField>('/asset-custom-fields', data, {
        retry: false,
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`创建自定义字段配置失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新自定义字段配置
   */
  async updateAssetCustomField(
    id: string,
    data: Partial<AssetCustomField>
  ): Promise<AssetCustomField> {
    try {
      const result = await enhancedApiClient.put<AssetCustomField>(
        `/asset-custom-fields/${id}`,
        data,
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`更新自定义字段配置失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 删除自定义字段配置
   */
  async deleteAssetCustomField(id: string): Promise<void> {
    try {
      const result = await enhancedApiClient.delete<void>(`/asset-custom-fields/${id}`, {
        retry: false,
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`删除自定义字段配置失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取资产的自定义字段值
   */
  async getAssetCustomFieldValues(assetId: string): Promise<CustomFieldValue[]> {
    try {
      const result = await enhancedApiClient.get<{ values: CustomFieldValue[] }>(
        `/assets/${assetId}/custom-field-values`,
        {
          cache: true,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取资产自定义字段值失败: ${result.error}`);
      }

      return result.data?.values ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新资产的自定义字段值
   */
  async updateAssetCustomFieldValues(
    assetId: string,
    values: CustomFieldValue[]
  ): Promise<CustomFieldValue[]> {
    try {
      const result = await enhancedApiClient.put<{ values: CustomFieldValue[] }>(
        `/assets/${assetId}/custom-field-values`,
        { values },
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`更新资产自定义字段值失败: ${result.error}`);
      }

      return result.data?.values ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 批量设置自定义字段值
   */
  async batchSetCustomFieldValues(
    updates: Array<{ assetId: string; values: CustomFieldValue[] }>
  ): Promise<void> {
    try {
      const result = await enhancedApiClient.post<void>(
        '/assets/batch-custom-field-values',
        { updates },
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`批量设置自定义字段值失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 验证自定义字段值
   */
  async validateCustomFieldValue(fieldId: string, value: unknown): Promise<FieldValidationResult> {
    try {
      const result = await enhancedApiClient.post<{ valid: boolean; error?: string }>(
        `/asset-custom-fields/${fieldId}/validate`,
        { value },
        {
          retry: false,
          smartExtract: true,
        }
      );

      if (!result.success) {
        return {
          valid: false,
          error: result.error,
        };
      }

      return result.data || { valid: true };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      return {
        valid: false,
        error: enhancedError.message,
      };
    }
  }

  /**
   * 获取字段选项（用于下拉框等）
   */
  async getFieldOptions(fieldType: string, category?: string): Promise<FieldOption[]> {
    try {
      const result = await enhancedApiClient.get<FieldOption[]>('/field-options', {
        params: { field_type: fieldType, category },
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取字段选项失败: ${result.error}`);
      }

      return result.data ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

// 导出服务实例
export const assetFieldService = new AssetFieldService();
