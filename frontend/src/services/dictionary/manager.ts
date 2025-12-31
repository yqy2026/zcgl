/**
 * 字典管理服务 - 统一响应处理版本
 *
 * @description 字典的完整CRUD操作，主要用于管理界面，支持枚举类型和枚举值的管理
 * @author Claude Code
 * @updated 2025-11-10
 */

import { enhancedApiClient } from '@/api/client';
import { ApiErrorHandler } from '../../utils/responseExtractor';
import { API_CONFIG } from '../../api/config';
import {
  DictionaryOption,
  DICTIONARY_CONFIGS
} from './config';

// 枚举字段类型接口
export interface EnumFieldType {
  id: string;
  name: string;
  code: string;
  category?: string;
  description?: string;
  is_system: boolean;
  is_multiple: boolean;
  is_hierarchical: boolean;
  default_value?: string;
  validation_rules?: Record<string, unknown>;
  display_config?: Record<string, unknown>;
  status: 'active' | 'inactive';
  is_deleted?: boolean;
  created_by?: string;
  updated_by?: string;
  created_at: string;
  updated_at: string;
  enum_values?: Array<{
    id: string;
    enum_type_id: string;
    label: string;
    value: string;
    code?: string;
    description?: string;
    parent_id?: string;
    level: number;
    sort_order: number;
    color?: string;
    icon?: string;
    extra_properties?: Record<string, unknown>;
    is_active: boolean;
    is_default: boolean;
    path?: string;
    is_deleted?: boolean;
    created_at: string;
    updated_at: string;
    created_by?: string;
    updated_by?: string;
    children?: unknown[];
  }>;
}

// 枚举字段值接口
export interface EnumFieldValue {
  id: string;
  enum_type_id: string;
  label: string;
  value: string;
  code?: string;
  description?: string;
  parent_id?: string;
  level: number;
  sort_order: number;
  color?: string;
  icon?: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

// 枚举字段与值的组合接口
export interface EnumFieldWithType {
  type: EnumFieldType;
  values: EnumFieldValue[];
}

// 字典管理操作结果接口
export interface DictionaryManagerResult<T = any> {
  success: boolean;
  data?: T;
  message: string;
  error?: string;
  operationType: string;
  timestamp: string;
}

// 字典使用统计接口
export interface DictionaryUsageStats {
  total_records: number;
  active_records: number;
  usage_by_field: Record<string, number>;
  last_updated: string;
  popular_values: Array<{
    value: string;
    label: string;
    usage_count: number;
  }>;
}

// 字典批量操作结果接口
export interface DictionaryBatchResult {
  success: number;
  failed: number;
  total: number;
  results: DictionaryManagerResult[];
  operationSummary: {
    operation: string;
    duration: number; // 毫秒
    errors: string[];
  };
}

/**
 * 字典管理服务类
 */
class DictionaryManagerService {
  private readonly baseUrl = '/api/v1/enum-fields';
  private readonly DEFAULT_TIMEOUT = 10000; // 默认超时时间
  private readonly BATCH_SIZE = 50; // 批量操作大小

  /**
   * 获取所有枚举类型（用于管理界面）
   */
  async getEnumFieldTypes(): Promise<EnumFieldType[]> {
    try {
      const result = await enhancedApiClient.get<EnumFieldType[]>(
        `${this.baseUrl}/types`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取枚举类型失败: ${result.error}`);
      }

      const data = result.data!;

      // 处理后端返回的字符串数组，转换为完整的枚举类型对象数组
      if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'string') {
        // 如果是字符串数组，转换为完整的枚举类型对象
        const enumTypes: EnumFieldType[] = (data as any).map((typeCode: string, index: number) => {
          // 从DICTIONARY_CONFIGS中查找配置
          const config = Object.values(DICTIONARY_CONFIGS).find(c => c.code === typeCode);

          return {
            id: `enum-type-${index}`,
            name: config?.name || typeCode.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
            code: typeCode,
            category: config?.category || '系统字典',
            description: config?.description || `${typeCode} 枚举类型`,
            is_system: true,
            is_multiple: false,
            is_hierarchical: false,
            default_value: undefined,
            status: 'active' as const,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          };
        });

        return enumTypes;
      }

      // 如果不是字符串数组，直接返回
      return Array.isArray(data) ? data : [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('获取枚举类型失败:', enhancedError.message);

      // 返回基于配置的备用数据
      return this.getFallbackEnumFieldTypes();
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
      updated_at: new Date().toISOString()
    }));
  }

  /**
   * 获取特定类型的枚举值
   */
  async getEnumFieldValues(typeId: string): Promise<EnumFieldValue[]> {
    try {
      const result = await enhancedApiClient.get<EnumFieldValue[]>(
        `${this.baseUrl}/${typeId}/options`,
        {
          cache: true,
          timeout: this.DEFAULT_TIMEOUT,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取枚举值失败: ${result.error}`);
      }

      const data = result.data!;

      // 确保返回数组格式
      const dataArray = Array.isArray(data) ? data : [];

      // 映射数据到标准格式
      const mappedData = dataArray.map((option: any, index: number) => ({
        id: option.id || `dict-${typeId}-${index}`,
        enum_type_id: typeId,
        label: option.label || option.name || option.code || option.id || index.toString(),
        value: option.value || option.code || option.id || index.toString(),
        code: option.code,
        description: option.description,
        level: option.level || 1,
        sort_order: option.sort_order || index + 1,
        color: option.color,
        icon: option.icon,
        is_active: option.is_active !== false,
        is_default: option.is_default || index === 0,
        created_at: option.created_at || new Date().toISOString(),
        updated_at: option.updated_at || new Date().toISOString()
      }));

      return mappedData;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error(`获取枚举值失败 [${typeId}]:`, enhancedError.message);

      // 尝试从配置中获取备用数据
      const config = Object.values(DICTIONARY_CONFIGS).find(c => c.code === typeId);
      if (config) {
        return config.fallbackOptions.map((option, index) => ({
          id: `fallback-${typeId}-${index}`,
          enum_type_id: typeId,
          label: option.label,
          value: option.value,
          code: option.code,
          description: '',
          level: 1,
          sort_order: option.sort_order || index + 1,
          color: option.color,
          icon: option.icon,
          is_active: true,
          is_default: index === 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }));
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

      // 安全检查：确保types是可迭代的数组
      if (!Array.isArray(types)) {
        console.warn('getEnumFieldData: types is not an array, using empty array');
        return [];
      }

      // 并行获取所有类型的值以提高性能
      const valuePromises = types.map(async (type) => {
        let values: EnumFieldValue[] = [];

        // 首先尝试使用type.code获取枚举值
        if (type.code) {
          values = await this.getEnumFieldValues(type.code);
        }

        // 如果没有获取到值，则尝试使用type.id
        if (values.length === 0 && type.id) {
          values = await this.getEnumFieldValues(type.id);
        }

        // 最后的备用方案：如果有enum_values数据，则使用它
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
            updated_at: val.updated_at
          }));
        }

        return { type, values };
      });

      const results = await Promise.allSettled(valuePromises);

      results.forEach((result) => {
        if (result.status === 'fulfilled') {
          data.push(result.value);
        } else {
          console.error('获取枚举字段数据失败:', result.reason);
        }
      });

      return data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('获取枚举字段数据失败:', enhancedError.message);
      return [];
    }
  }

  /**
   * 创建新的枚举类型
   */
  async createEnumFieldType(data: {
    name: string;
    code: string;
    category?: string;
    description?: string;
    is_multiple?: boolean;
    is_hierarchical?: boolean;
    default_value?: string;
  }): Promise<EnumFieldType | null> {
    try {
      // 验证代码
      const validation = this.validateEnumTypeCode(data.code);
      if (!validation.valid) {
        throw new Error(`代码验证失败: ${validation.errors.join(', ')}`);
      }

      const result = await enhancedApiClient.post<EnumFieldType>(
        `${this.baseUrl}/types`,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`创建枚举类型失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('创建枚举类型失败:', enhancedError.message);
      return null;
    }
  }

  /**
   * 更新枚举类型
   */
  async updateEnumFieldType(
    typeId: string,
    data: Partial<{
      name: string;
      code: string;
      category?: string;
      description?: string;
      is_multiple: boolean;
      is_hierarchical: boolean;
      default_value?: string;
      status: 'active' | 'inactive';
    }>
  ): Promise<EnumFieldType | null> {
    try {
      // 如果更新了代码，需要验证新代码
      if (data.code) {
        const validation = this.validateEnumTypeCode(data.code);
        if (!validation.valid) {
          throw new Error(`代码验证失败: ${validation.errors.join(', ')}`);
        }
      }

      const result = await enhancedApiClient.put<EnumFieldType>(
        `${this.baseUrl}/types/${typeId}`,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`更新枚举类型失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('更新枚举类型失败:', enhancedError.message);
      return null;
    }
  }

  /**
   * 删除枚举类型
   */
  async deleteEnumFieldType(typeId: string): Promise<boolean> {
    try {
      const result = await enhancedApiClient.delete<{ success: boolean; message: string }>(
        `${this.baseUrl}/types/${typeId}`,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`删除枚举类型失败: ${result.error}`);
      }

      return result.data!.success;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('删除枚举类型失败:', enhancedError.message);
      return false;
    }
  }

  /**
   * 添加枚举值
   */
  async addEnumFieldValue(
    typeId: string,
    data: {
      label: string;
      value: string;
      code?: string;
      description?: string;
      sort_order?: number;
      color?: string;
      icon?: string;
      is_default?: boolean;
    }
  ): Promise<EnumFieldValue | null> {
    try {
      const result = await enhancedApiClient.post<EnumFieldValue>(
        `${this.baseUrl}/${typeId}/values`,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`添加枚举值失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('添加枚举值失败:', enhancedError.message);
      return null;
    }
  }

  /**
   * 更新枚举值
   */
  async updateEnumFieldValue(
    typeId: string,
    valueId: string,
    data: Partial<{
      label: string;
      value: string;
      code?: string;
      description?: string;
      sort_order?: number;
      color?: string;
      icon?: string;
      is_active: boolean;
      is_default: boolean;
    }>
  ): Promise<EnumFieldValue | null> {
    try {
      const result = await enhancedApiClient.put<EnumFieldValue>(
        `${this.baseUrl}/${typeId}/values/${valueId}`,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`更新枚举值失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('更新枚举值失败:', enhancedError.message);
      return null;
    }
  }

  /**
   * 删除枚举值
   */
  async deleteEnumFieldValue(typeId: string, valueId: string): Promise<boolean> {
    try {
      const result = await enhancedApiClient.delete<{ success: boolean; message: string }>(
        `${this.baseUrl}/${typeId}/values/${valueId}`,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`删除枚举值失败: ${result.error}`);
      }

      return result.data!.success;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('删除枚举值失败:', enhancedError.message);
      return false;
    }
  }

  /**
   * 获取枚举字段使用统计
   */
  async getEnumFieldUsageStats(typeId: string): Promise<DictionaryUsageStats> {
    try {
      const result = await enhancedApiClient.get<DictionaryUsageStats>(
        `${this.baseUrl}/${typeId}/usage`,
        {
          cache: true,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取枚举字段使用统计失败: ${result.error}`);
      }

      const data = result.data!;

      // 确保返回完整的统计信息
      return {
        total_records: data.total_records || 0,
        active_records: data.active_records || 0,
        usage_by_field: data.usage_by_field || {},
        last_updated: new Date().toISOString(),
        popular_values: data.popular_values || []
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('获取枚举字段使用统计失败:', enhancedError.message);

      // 返回默认统计信息
      return {
        total_records: 0,
        active_records: 0,
        usage_by_field: {},
        last_updated: new Date().toISOString(),
        popular_values: []
      };
    }
  }

  /**
   * 验证枚举类型代码
   */
  validateEnumTypeCode(code: string): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!code) {
      errors.push('代码不能为空');
    }

    if (!/^[a-z][a-z0-9_]*$/.test(code)) {
      errors.push('代码只能包含小写字母、数字和下划线，且必须以字母开头');
    }

    if (code.length > 50) {
      errors.push('代码长度不能超过50个字符');
    }

    // 检查是否与系统字典冲突
    if (code in DICTIONARY_CONFIGS) {
      errors.push('代码与系统字典冲突');
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * 导出枚举字段数据
   */
  async exportEnumFieldData(typeId: string, format: 'json' | 'excel' = 'json'): Promise<Blob> {
    try {
      const result = await enhancedApiClient.get<Blob>(
        `${this.baseUrl}/${typeId}/export`,
        {
          params: { format },
          responseType: 'blob',
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 }
        }
      );

      if (!result.success) {
        throw new Error(`导出枚举字段数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('导出枚举字段数据失败:', enhancedError.message);
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

      const result = await enhancedApiClient.post<{ success: number; errors: string[] }>(
        `${this.baseUrl}/${typeId}/import`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`导入枚举字段数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('导入枚举字段数据失败:', enhancedError.message);
      throw new Error(`导入失败: ${enhancedError.message}`);
    }
  }

  /**
   * 批量添加枚举值
   */
  async batchAddEnumValues(
    typeId: string,
    values: Array<{
      label: string;
      value: string;
      code?: string;
      description?: string;
      sort_order?: number;
      color?: string;
      icon?: string;
    }>
  ): Promise<DictionaryBatchResult> {
    const startTime = Date.now();
    const results: DictionaryManagerResult[] = [];
    let successCount = 0;
    let failedCount = 0;

    // 分批处理以避免性能问题
    const batches = this.chunkArray(values, this.BATCH_SIZE);

    for (const batch of batches) {
      const batchPromises = batch.map(async (valueData, index) => {
        try {
          const result = await this.addEnumFieldValue(typeId, valueData);
          return {
            success: true,
            data: result,
            message: `枚举值添加成功: ${valueData.label}`,
            operationType: 'batchAddEnumValue',
            timestamp: new Date().toISOString()
          };
        } catch (error) {
          const enhancedError = ApiErrorHandler.handleError(error);
          return {
            success: false,
            message: `枚举值添加失败: ${enhancedError.message}`,
            error: enhancedError.message,
            operationType: 'batchAddEnumValue',
            timestamp: new Date().toISOString()
          };
        }
      });

      const batchResults = await Promise.allSettled(batchPromises);

      batchResults.forEach((promiseResult) => {
        if (promiseResult.status === 'fulfilled') {
          results.push(promiseResult.value);
          if (promiseResult.value.success) {
            successCount++;
          } else {
            failedCount++;
          }
        } else {
          failedCount++;
        }
      });
    }

    const duration = Date.now() - startTime;
    const errors = results
      .filter(r => !r.success)
      .map(r => r.message || 'Unknown error');

    return {
      success: successCount,
      failed: failedCount,
      total: values.length,
      results,
      operationSummary: {
        operation: 'batchAddEnumValues',
        duration,
        errors
      }
    };
  }

  /**
   * 批量更新枚举值
   */
  async batchUpdateEnumValues(
    typeId: string,
    updates: Array<{
      valueId: string;
      data: Partial<{
        label: string;
        value: string;
        code?: string;
        description?: string;
        sort_order?: number;
        color?: string;
        icon?: string;
        is_active: boolean;
        is_default: boolean;
      }>;
    }>
  ): Promise<DictionaryBatchResult> {
    const startTime = Date.now();
    const results: DictionaryManagerResult[] = [];
    let successCount = 0;
    let failedCount = 0;

    // 分批处理
    const batches = this.chunkArray(updates, this.BATCH_SIZE);

    for (const batch of batches) {
      const batchPromises = batch.map(async ({ valueId, data }) => {
        try {
          const result = await this.updateEnumFieldValue(typeId, valueId, data);
          return {
            success: true,
            data: result,
            message: `枚举值更新成功: ${valueId}`,
            operationType: 'batchUpdateEnumValues',
            timestamp: new Date().toISOString()
          };
        } catch (error) {
          const enhancedError = ApiErrorHandler.handleError(error);
          return {
            success: false,
            message: `枚举值更新失败: ${enhancedError.message}`,
            error: enhancedError.message,
            operationType: 'batchUpdateEnumValues',
            timestamp: new Date().toISOString()
          };
        }
      });

      const batchResults = await Promise.allSettled(batchPromises);

      batchResults.forEach((promiseResult) => {
        if (promiseResult.status === 'fulfilled') {
          results.push(promiseResult.value);
          if (promiseResult.value.success) {
            successCount++;
          } else {
            failedCount++;
          }
        } else {
          failedCount++;
        }
      });
    }

    const duration = Date.now() - startTime;
    const errors = results
      .filter(r => !r.success)
      .map(r => r.message || 'Unknown error');

    return {
      success: successCount,
      failed: failedCount,
      total: updates.length,
      results,
      operationSummary: {
        operation: 'batchUpdateEnumValues',
        duration,
        errors
      }
    };
  }

  /**
   * 批量删除枚举值
   */
  async batchDeleteEnumValues(
    typeId: string,
    valueIds: string[]
  ): Promise<DictionaryBatchResult> {
    const startTime = Date.now();
    const results: DictionaryManagerResult[] = [];
    let successCount = 0;
    let failedCount = 0;

    // 分批处理
    const batches = this.chunkArray(valueIds, this.BATCH_SIZE);

    for (const batch of batches) {
      const batchPromises = batch.map(async (valueId) => {
        try {
          const success = await this.deleteEnumFieldValue(typeId, valueId);
          return {
            success,
            message: success ? `枚举值删除成功: ${valueId}` : `枚举值删除失败: ${valueId}`,
            operationType: 'batchDeleteEnumValues',
            timestamp: new Date().toISOString()
          };
        } catch (error) {
          const enhancedError = ApiErrorHandler.handleError(error);
          return {
            success: false,
            message: `枚举值删除失败: ${enhancedError.message}`,
            error: enhancedError.message,
            operationType: 'batchDeleteEnumValues',
            timestamp: new Date().toISOString()
          };
        }
      });

      const batchResults = await Promise.allSettled(batchPromises);

      batchResults.forEach((promiseResult) => {
        if (promiseResult.status === 'fulfilled') {
          results.push(promiseResult.value);
          if (promiseResult.value.success) {
            successCount++;
          } else {
            failedCount++;
          }
        } else {
          failedCount++;
        }
      });
    }

    const duration = Date.now() - startTime;
    const errors = results
      .filter(r => !r.success)
      .map(r => r.message || 'Unknown error');

    return {
      success: successCount,
      failed: failedCount,
      total: valueIds.length,
      results,
      operationSummary: {
        operation: 'batchDeleteEnumValues',
        duration,
        errors
      }
    };
  }

  /**
   * 搜索枚举类型
   */
  async searchEnumTypes(keyword: string, filters?: {
    category?: string;
    status?: 'active' | 'inactive';
    is_system?: boolean;
  }): Promise<EnumFieldType[]> {
    try {
      const params: any = { keyword };
      if (filters) {
        Object.assign(params, filters);
      }

      const result = await enhancedApiClient.get<EnumFieldType[]>(
        `${this.baseUrl}/types/search`,
        {
          params,
          cache: true,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`搜索枚举类型失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('搜索枚举类型失败:', enhancedError.message);

      // 本地搜索作为备用方案
      const allTypes = await this.getEnumFieldTypes();
      const lowerKeyword = keyword.toLowerCase();

      return allTypes.filter(type => {
        let matches = type.name.toLowerCase().includes(lowerKeyword) ||
                     type.code.toLowerCase().includes(lowerKeyword) ||
                     (type.description && type.description.toLowerCase().includes(lowerKeyword));

        if (filters) {
          if (filters.category && type.category !== filters.category) {
            matches = false;
          }
          if (filters.status && type.status !== filters.status) {
            matches = false;
          }
          if (filters.is_system !== undefined && type.is_system !== filters.is_system) {
            matches = false;
          }
        }

        return matches;
      });
    }
  }

  /**
   * 验证字典数据完整性
   */
  async validateDictionaryData(typeId: string): Promise<{
    isValid: boolean;
    issues: string[];
    suggestions: string[];
    warnings: string[];
  }> {
    try {
      const issues: string[] = [];
      const suggestions: string[] = [];
      const warnings: string[] = [];

      // 获取类型信息
      const types = await this.getEnumFieldTypes();
      const targetType = types.find(t => t.id === typeId || t.code === typeId);

      if (!targetType) {
        issues.push(`字典类型不存在: ${typeId}`);
        return { isValid: false, issues, suggestions, warnings };
      }

      // 获取值信息
      const values = await this.getEnumFieldValues(targetType.code);

      // 检查是否有值
      if (values.length === 0) {
        issues.push('字典类型没有任何值');
        suggestions.push('添加至少一个枚举值');
      }

      // 检查重复值
      const valueLabels = values.map(v => v.label.toLowerCase());
      const valueCodes = values.map(v => v.value.toLowerCase());
      const duplicateLabels = valueLabels.filter((label, index) => valueLabels.indexOf(label) !== index);
      const duplicateCodes = valueCodes.filter((code, index) => valueCodes.indexOf(code) !== index);

      if (duplicateLabels.length > 0) {
        warnings.push(`发现重复的标签: ${[...new Set(duplicateLabels)].join(', ')}`);
        suggestions.push('确保所有标签都是唯一的');
      }

      if (duplicateCodes.length > 0) {
        issues.push(`发现重复的值: ${[...new Set(duplicateCodes)].join(', ')}`);
        suggestions.push('确保所有值都是唯一的');
      }

      // 检查必需字段
      const invalidValues = values.filter(v => !v.label || !v.value);
      if (invalidValues.length > 0) {
        issues.push(`发现${invalidValues.length}个缺少必需字段的枚举值`);
        suggestions.push('确保所有枚举值都有label和value');
      }

      // 检查默认值
      const defaultValues = values.filter(v => v.is_default);
      if (defaultValues.length === 0) {
        warnings.push('没有设置默认值');
        suggestions.push('考虑设置一个默认值');
      } else if (defaultValues.length > 1) {
        warnings.push(`发现${defaultValues.length}个默认值`);
        suggestions.push('只应该设置一个默认值');
      }

      // 检查排序
      const unsortedValues = values.filter(v => !v.sort_order);
      if (unsortedValues.length > 0) {
        warnings.push(`发现${unsortedValues.length}个未设置排序的枚举值`);
        suggestions.push('为所有枚举值设置排序顺序');
      }

      return {
        isValid: issues.length === 0,
        issues,
        suggestions,
        warnings
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      return {
        isValid: false,
        issues: [`验证失败: ${enhancedError.message}`],
        suggestions: ['检查网络连接和权限'],
        warnings: []
      };
    }
  }

  /**
   * 工具方法：数组分块
   */
  private chunkArray<T>(array: T[], chunkSize: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
  }
}

// 创建单例实例
export const dictionaryManagerService = new DictionaryManagerService();

// 为了向后兼容，导出默认实例
export default dictionaryManagerService;
