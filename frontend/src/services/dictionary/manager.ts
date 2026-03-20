/**
 * 字典管理服务 - 统一响应处理版本
 *
 * @description 字典的完整CRUD操作，主要用于管理界面，支持枚举类型和枚举值的管理
 *
 * 本文件是 re-export hub：
 *   - 类型定义来自 ./dictionaryTypes
 *   - 缓存逻辑来自 ./dictionaryCache
 *   - 批量操作/搜索/验证来自 ./dictionarySync
 *
 * @author Claude Code
 */

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { DICTIONARY_CONFIGS } from './config';
import { createLogger } from '@/utils/logger';
import { EnumTypeCache } from './dictionaryCache';
import {
  batchAddEnumValues as _batchAdd,
  batchUpdateEnumValues as _batchUpdate,
  batchDeleteEnumValues as _batchDelete,
  searchEnumTypes as _searchEnumTypes,
  validateDictionaryData as _validateDictionaryData,
  validateEnumTypeCode as _validateEnumTypeCode,
} from './dictionarySync';

// ── Re-export all types for backward compatibility ──
export type {
  EnumFieldType,
  EnumFieldValue,
  EnumFieldWithType,
  DictionaryManagerResult,
  DictionaryUsageStats,
  DictionaryBatchResult,
  CreateEnumFieldTypeRequest,
  UpdateEnumFieldTypeRequest,
  CreateEnumFieldValueRequest,
  UpdateEnumFieldValueRequest,
} from './dictionaryTypes';

// Re-export sub-modules for direct access
export { EnumTypeCache } from './dictionaryCache';
export type { EnumTypeResolveResult } from './dictionaryCache';
export {
  chunkArray,
  batchAddEnumValues,
  batchUpdateEnumValues,
  batchDeleteEnumValues,
  searchEnumTypes,
  validateDictionaryData,
  validateEnumTypeCode,
} from './dictionarySync';
export type { DictionaryCoreCrud } from './dictionarySync';

// Import concrete types needed by the class implementation
import type {
  EnumFieldType,
  EnumFieldValue,
  EnumFieldWithType,
  DictionaryBatchResult,
  CreateEnumFieldTypeRequest,
  UpdateEnumFieldTypeRequest,
  CreateEnumFieldValueRequest,
  UpdateEnumFieldValueRequest,
  DictionaryUsageStats,
} from './dictionaryTypes';

const dictLogger = createLogger('Dictionary');

/**
 * 字典管理服务类
 */
class DictionaryManagerService {
  private readonly baseUrl = '/enum-fields';
  private readonly DEFAULT_TIMEOUT = 10000;
  private readonly BATCH_SIZE = 50;
  private readonly cache = new EnumTypeCache(5 * 60 * 1000);

  /**
   * 获取所有枚举类型（用于管理界面）
   */
  async getEnumFieldTypes(): Promise<EnumFieldType[]> {
    try {
      const result = await apiClient.get<EnumFieldType[]>(`${this.baseUrl}/types`, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (result.success === false) {
        throw new Error(`获取枚举类型失败: ${result.error}`);
      }

      const data = result.data!;

      // 处理后端返回的字符串数组，转换为完整的枚举类型对象数组
      if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'string') {
        const enumTypes: EnumFieldType[] = (data as unknown[]).map(
          (item: unknown, index: number): EnumFieldType => {
            const typeCode = String(item);
            const config = Object.values(DICTIONARY_CONFIGS).find(c => c.code === typeCode);

            return {
              id: `enum-type-${index}`,
              name:
                config?.name ?? typeCode.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
              code: typeCode,
              category: config?.category ?? '系统字典',
              description: config?.description ?? `${typeCode} 枚举类型`,
              is_system: true,
              is_multiple: false,
              is_hierarchical: false,
              default_value: undefined,
              status: 'active' as const,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            };
          }
        );

        this.cache.refresh(enumTypes);
        return enumTypes;
      }

      const normalized = Array.isArray(data) ? data : [];
      this.cache.refresh(normalized);
      return normalized;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('获取枚举类型失败:', undefined, { error: enhancedError.message });

      const fallback = this.getFallbackEnumFieldTypes();
      this.cache.refresh(fallback);
      return fallback;
    }
  }

  /**
   * 获取备用枚举类型数据
   */
  private getFallbackEnumFieldTypes(): EnumFieldType[] {
    return Object.values(DICTIONARY_CONFIGS).map((config, index) => ({
      id: `fallback-${index}`,
      name: config.name,
      code: config.code,
      category: config.category,
      description: config.description,
      is_system: true,
      is_multiple: false,
      is_hierarchical: false,
      default_value: undefined,
      status: 'active' as const,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));
  }

  /**
   * 获取特定类型的枚举值
   */
  async getEnumFieldValues(typeId: string): Promise<EnumFieldValue[]> {
    const resolved = await this.cache.resolve(typeId, () => this.getEnumFieldTypes());
    const requestTypeId = resolved.id;
    const requestTypeCode = resolved.code ?? typeId;

    if (requestTypeId === '') {
      return [];
    }

    try {
      const result = await apiClient.get<EnumFieldValue[]>(
        `${this.baseUrl}/types/${requestTypeId}/values`,
        {
          cache: true,
          timeout: this.DEFAULT_TIMEOUT,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (result.success === false) {
        throw new Error(`获取枚举值失败: ${result.error}`);
      }

      const data = result.data!;
      const dataArray = Array.isArray(data) ? data : [];

      const mappedData = dataArray.map((rawOption: unknown, index: number) => {
        const option = rawOption as Record<string, unknown>;
        const id = typeof option.id === 'string' ? option.id : undefined;
        const enumTypeId =
          typeof option.enum_type_id === 'string' && option.enum_type_id !== ''
            ? option.enum_type_id
            : requestTypeId;
        const label =
          (typeof option.label === 'string' && option.label !== '' ? option.label : undefined) ??
          (typeof option.name === 'string' && option.name !== '' ? option.name : undefined) ??
          (typeof option.code === 'string' && option.code !== '' ? option.code : undefined) ??
          (typeof option.id === 'string' && option.id !== '' ? option.id : undefined) ??
          index.toString();
        const value =
          (typeof option.value === 'string' && option.value !== '' ? option.value : undefined) ??
          (typeof option.code === 'string' && option.code !== '' ? option.code : undefined) ??
          (typeof option.id === 'string' && option.id !== '' ? option.id : undefined) ??
          index.toString();
        const code = typeof option.code === 'string' ? option.code : undefined;
        const description = typeof option.description === 'string' ? option.description : undefined;
        const level = typeof option.level === 'number' ? option.level : 1;
        const sortOrder = typeof option.sort_order === 'number' ? option.sort_order : index + 1;
        const color = typeof option.color === 'string' ? option.color : undefined;
        const icon = typeof option.icon === 'string' ? option.icon : undefined;
        const isActive = typeof option.is_active === 'boolean' ? option.is_active : true;
        const isDefault = typeof option.is_default === 'boolean' ? option.is_default : index === 0;
        const createdAt =
          typeof option.created_at === 'string' ? option.created_at : new Date().toISOString();

        return {
          id: id ?? `dict-${typeId}-${index}`,
          enum_type_id: enumTypeId,
          label,
          value,
          code,
          description,
          level,
          sort_order: sortOrder,
          color,
          icon,
          is_active: isActive,
          is_default: isDefault,
          created_at: createdAt,
          updated_at: new Date().toISOString(),
        };
      });

      return mappedData;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error(`获取枚举值失败 [${typeId}]:`, undefined, { error: enhancedError.message });

      const config = Object.values(DICTIONARY_CONFIGS).find(c => c.code === requestTypeCode);
      if (config) {
        return config.fallbackOptions.map((option, index) => {
          return {
            id: `fallback-${requestTypeCode}-${index}`,
            enum_type_id: requestTypeId,
            label: option.label,
            value: option.value,
            code: option.code,
            description: '',
            level: 1,
            sort_order: option.sort_order ?? index + 1,
            color: option.color,
            icon: option.icon,
            is_active: true,
            is_default: index === 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          };
        });
      }

      return [];
    }
  }

  /**
   * 获取完整的枚举字段数据（类型+值）
   */
  async getEnumFieldData(): Promise<EnumFieldWithType[]> {
    try {
      const types = await this.getEnumFieldTypes();
      const data: EnumFieldWithType[] = [];

      if (!Array.isArray(types)) {
        dictLogger.warn('getEnumFieldData: types is not an array, using empty array');
        return [];
      }

      const valuePromises = types.map(async type => {
        let values: EnumFieldValue[] = [];

        if (type.code !== undefined && type.code !== null && type.code !== '') {
          values = await this.getEnumFieldValues(type.code);
        }

        if (values.length === 0 && type.id) {
          values = await this.getEnumFieldValues(type.id);
        }

        if (values.length === 0 && type.enum_values && Array.isArray(type.enum_values)) {
          values = type.enum_values.map(val => ({
            id: val.id,
            enum_type_id: val.enum_type_id,
            label: val.label,
            value: val.value,
            code: val.code,
            description: val.description,
            parent_id: val.parent_id,
            level: val.level,
            sort_order: val.sort_order,
            color: val.color,
            icon: val.icon,
            is_active: val.is_active,
            is_default: val.is_default,
            created_at: val.created_at,
            updated_at: val.updated_at,
          }));
        }

        return { type, values };
      });

      const results = await Promise.allSettled(valuePromises);

      results.forEach(result => {
        if (result.status === 'fulfilled') {
          data.push(result.value);
        } else {
          dictLogger.error('获取枚举字段数据失败:', undefined, { reason: result.reason });
        }
      });

      return data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('获取枚举字段数据失败:', undefined, { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 创建新的枚举类型
   */
  async createEnumFieldType(data: CreateEnumFieldTypeRequest): Promise<EnumFieldType | null> {
    try {
      const validation = _validateEnumTypeCode(data.code);
      if (!validation.valid) {
        throw new Error(`代码验证失败: ${validation.errors.join(', ')}`);
      }

      const result = await apiClient.post<EnumFieldType>(`${this.baseUrl}/types`, data, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (result.success === false) {
        throw new Error(`创建枚举类型失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('创建枚举类型失败:', undefined, { error: enhancedError.message });
      return null;
    }
  }

  /**
   * 更新枚举类型
   */
  async updateEnumFieldType(
    typeId: string,
    data: UpdateEnumFieldTypeRequest
  ): Promise<EnumFieldType | null> {
    try {
      if (data.code !== undefined && data.code !== null && data.code !== '') {
        const validation = _validateEnumTypeCode(data.code);
        if (validation.valid === false) {
          throw new Error(`代码验证失败: ${validation.errors.join(', ')}`);
        }
      }

      const result = await apiClient.put<EnumFieldType>(`${this.baseUrl}/types/${typeId}`, data, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (result.success === false) {
        throw new Error(`更新枚举类型失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('更新枚举类型失败:', undefined, { error: enhancedError.message });
      return null;
    }
  }

  /**
   * 删除枚举类型
   */
  async deleteEnumFieldType(typeId: string): Promise<boolean> {
    try {
      const result = await apiClient.delete<{ success: boolean; message: string }>(
        `${this.baseUrl}/types/${typeId}`,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (result.success === false) {
        throw new Error(`删除枚举类型失败: ${result.error}`);
      }

      return result.data!.success;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('删除枚举类型失败:', undefined, { error: enhancedError.message });
      return false;
    }
  }

  /**
   * 添加枚举值
   */
  async addEnumFieldValue(
    typeId: string,
    data: CreateEnumFieldValueRequest
  ): Promise<EnumFieldValue | null> {
    try {
      const resolved = await this.cache.resolve(typeId, () => this.getEnumFieldTypes());
      const result = await apiClient.post<EnumFieldValue>(
        `${this.baseUrl}/types/${resolved.id}/values`,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (result.success === false) {
        throw new Error(`添加枚举值失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('添加枚举值失败:', undefined, { error: enhancedError.message });
      return null;
    }
  }

  /**
   * 更新枚举值
   */
  async updateEnumFieldValue(
    typeId: string,
    valueId: string,
    data: UpdateEnumFieldValueRequest
  ): Promise<EnumFieldValue | null> {
    try {
      const result = await apiClient.put<EnumFieldValue>(
        `${this.baseUrl}/values/${valueId}`,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (result.success === false) {
        throw new Error(`更新枚举值失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('更新枚举值失败:', undefined, { error: enhancedError.message, typeId });
      return null;
    }
  }

  /**
   * 删除枚举值
   */
  async deleteEnumFieldValue(typeId: string, valueId: string): Promise<boolean> {
    try {
      const result = await apiClient.delete<{ success: boolean; message: string }>(
        `${this.baseUrl}/values/${valueId}`,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (result.success === false) {
        throw new Error(`删除枚举值失败: ${result.error}`);
      }

      return result.data!.success;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('删除枚举值失败:', undefined, { error: enhancedError.message, typeId });
      return false;
    }
  }

  /**
   * 获取枚举字段使用统计
   */
  async getEnumFieldUsageStats(typeId: string): Promise<DictionaryUsageStats> {
    try {
      const resolved = typeId !== '' ? await this.cache.resolve(typeId, () => this.getEnumFieldTypes()) : { id: '' };
      const params: Record<string, string> = {};
      if (resolved.id !== '') {
        params.enum_type_id = resolved.id;
      }

      const result = await apiClient.get<unknown>(`${this.baseUrl}/usage`, {
        params,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (result.success === false) {
        throw new Error(`获取枚举字段使用统计失败: ${result.error}`);
      }

      const data = result.data;
      const usageRecords = Array.isArray(data) ? data : [];
      const usageByField: Record<string, number> = {};
      let activeCount = 0;

      usageRecords.forEach(record => {
        const usage = record as Record<string, unknown>;
        const fieldName = typeof usage.field_name === 'string' ? usage.field_name : '';
        const tableName = typeof usage.table_name === 'string' ? usage.table_name : '';
        const key = tableName !== '' ? `${tableName}.${fieldName}` : fieldName;

        if (key !== '') {
          usageByField[key] = (usageByField[key] ?? 0) + 1;
        }

        if (usage.is_active === true) {
          activeCount += 1;
        }
      });

      return {
        total_records: usageRecords.length,
        active_records: activeCount,
        usage_by_field: usageByField,
        last_updated: new Date().toISOString(),
        popular_values: [],
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('获取枚举字段使用统计失败:', undefined, { error: enhancedError.message });

      return {
        total_records: 0,
        active_records: 0,
        usage_by_field: {},
        last_updated: new Date().toISOString(),
        popular_values: [],
      };
    }
  }

  /**
   * 验证枚举类型代码
   */
  validateEnumTypeCode(code: string): { valid: boolean; errors: string[] } {
    return _validateEnumTypeCode(code);
  }

  /**
   * 导出枚举字段数据
   */
  async exportEnumFieldData(typeId: string, format: 'json' | 'excel' = 'json'): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(`${this.baseUrl}/${typeId}/export`, {
        params: { format },
        responseType: 'blob',
        retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
      });

      if (result.success === false) {
        throw new Error(`导出枚举字段数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('导出枚举字段数据失败:', undefined, { error: enhancedError.message });
      throw new Error(`导出失败: ${enhancedError.message}`);
    }
  }

  /**
   * 导入枚举字段数据
   */
  async importEnumFieldData(
    typeId: string,
    file: File
  ): Promise<{ success: number; errors: string[] }> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const result = await apiClient.post<{ success: number; errors: string[] }>(
        `${this.baseUrl}/${typeId}/import`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (result.success === false) {
        throw new Error(`导入枚举字段数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('导入枚举字段数据失败:', undefined, { error: enhancedError.message });
      throw new Error(`导入失败: ${enhancedError.message}`);
    }
  }

  // ── 批量操作（委托到 dictionarySync 模块） ──

  async batchAddEnumValues(
    typeId: string,
    values: CreateEnumFieldValueRequest[]
  ): Promise<DictionaryBatchResult> {
    return _batchAdd(this, typeId, values, this.BATCH_SIZE);
  }

  async batchUpdateEnumValues(
    typeId: string,
    updates: Array<{ valueId: string; data: UpdateEnumFieldValueRequest }>
  ): Promise<DictionaryBatchResult> {
    return _batchUpdate(this, typeId, updates, this.BATCH_SIZE);
  }

  async batchDeleteEnumValues(typeId: string, valueIds: string[]): Promise<DictionaryBatchResult> {
    return _batchDelete(this, typeId, valueIds, this.BATCH_SIZE);
  }

  // ── 搜索（委托到 dictionarySync 模块，带 API 优先策略） ──

  async searchEnumTypes(
    keyword: string,
    filters?: {
      category?: string;
      status?: 'active' | 'inactive';
      is_system?: boolean;
    }
  ): Promise<EnumFieldType[]> {
    try {
      const params: Record<string, unknown> = { keyword };
      if (filters) {
        Object.assign(params, filters);
      }

      const result = await apiClient.get<EnumFieldType[]>(`${this.baseUrl}/types/search`, {
        params,
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`搜索枚举类型失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      dictLogger.error('搜索枚举类型失败:', undefined, { error: enhancedError.message });

      // 本地搜索作为备用方案
      return _searchEnumTypes(this, keyword, filters);
    }
  }

  // ── 验证（委托到 dictionarySync 模块） ──

  async validateDictionaryData(typeId: string): Promise<{
    isValid: boolean;
    issues: string[];
    suggestions: string[];
    warnings: string[];
  }> {
    return _validateDictionaryData(this, typeId);
  }
}

// 创建单例实例
export const dictionaryManagerService = new DictionaryManagerService();
// 为了向后兼容，导出默认实例
export default dictionaryManagerService;
