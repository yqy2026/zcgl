/**
 * 字典同步服务 - 批量操作、搜索与数据完整性验证
 *
 * @description 从 DictionaryManagerService 中提取的批量操作（add/update/delete）、
 *              搜索枚举类型、以及字典数据完整性验证逻辑
 * @module dictionarySync
 */

import { ApiErrorHandler } from '@/utils/responseExtractor';
import { DICTIONARY_CONFIGS } from './config';
import type {
  EnumFieldType,
  EnumFieldValue,
  DictionaryManagerResult,
  DictionaryBatchResult,
  CreateEnumFieldValueRequest,
  UpdateEnumFieldValueRequest,
} from './dictionaryTypes';

/**
 * 数组分块工具函数
 */
export function chunkArray<T>(array: T[], chunkSize: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += chunkSize) {
    chunks.push(array.slice(i, i + chunkSize));
  }
  return chunks;
}

// ---------- 批量操作接口（依赖注入核心 CRUD 方法） ----------

/**
 * 核心 CRUD 委托接口
 *
 * 批量操作与搜索函数不直接持有服务实例引用，
 * 而是通过此接口接收所需的原子操作，保持模块解耦。
 */
export interface DictionaryCoreCrud {
  addEnumFieldValue(
    typeId: string,
    data: CreateEnumFieldValueRequest
  ): Promise<EnumFieldValue | null>;
  updateEnumFieldValue(
    typeId: string,
    valueId: string,
    data: UpdateEnumFieldValueRequest
  ): Promise<EnumFieldValue | null>;
  deleteEnumFieldValue(typeId: string, valueId: string): Promise<boolean>;
  getEnumFieldTypes(): Promise<EnumFieldType[]>;
  getEnumFieldValues(typeId: string): Promise<EnumFieldValue[]>;
}

// ---------- 批量操作 ----------

/**
 * 批量添加枚举值
 */
export async function batchAddEnumValues(
  crud: DictionaryCoreCrud,
  typeId: string,
  values: CreateEnumFieldValueRequest[],
  batchSize: number = 50
): Promise<DictionaryBatchResult> {
  const startTime = Date.now();
  const results: DictionaryManagerResult[] = [];
  let successCount = 0;
  let failedCount = 0;

  const batches = chunkArray(values, batchSize);

  for (const batch of batches) {
    const batchPromises = batch.map(async (valueData, _index) => {
      try {
        const result = await crud.addEnumFieldValue(typeId, valueData);
        return {
          success: true,
          data: result,
          message: `枚举值添加成功: ${valueData.label}`,
          operationType: 'batchAddEnumValue',
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        return {
          success: false,
          message: `枚举值添加失败: ${enhancedError.message}`,
          error: enhancedError.message,
          operationType: 'batchAddEnumValue',
          timestamp: new Date().toISOString(),
        };
      }
    });

    const batchResults = await Promise.allSettled(batchPromises);

    batchResults.forEach(promiseResult => {
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
  const errors = results.filter(r => !r.success).map(r => r.message || 'Unknown error');

  return {
    success: successCount,
    failed: failedCount,
    total: values.length,
    results,
    operationSummary: {
      operation: 'batchAddEnumValues',
      duration,
      errors,
    },
  };
}

/**
 * 批量更新枚举值
 */
export async function batchUpdateEnumValues(
  crud: DictionaryCoreCrud,
  typeId: string,
  updates: Array<{
    valueId: string;
    data: UpdateEnumFieldValueRequest;
  }>,
  batchSize: number = 50
): Promise<DictionaryBatchResult> {
  const startTime = Date.now();
  const results: DictionaryManagerResult[] = [];
  let successCount = 0;
  let failedCount = 0;

  const batches = chunkArray(updates, batchSize);

  for (const batch of batches) {
    const batchPromises = batch.map(async ({ valueId, data }) => {
      try {
        const result = await crud.updateEnumFieldValue(typeId, valueId, data);
        return {
          success: true,
          data: result,
          message: `枚举值更新成功: ${valueId}`,
          operationType: 'batchUpdateEnumValues',
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        return {
          success: false,
          message: `枚举值更新失败: ${enhancedError.message}`,
          error: enhancedError.message,
          operationType: 'batchUpdateEnumValues',
          timestamp: new Date().toISOString(),
        };
      }
    });

    const batchResults = await Promise.allSettled(batchPromises);

    batchResults.forEach(promiseResult => {
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
  const errors = results.filter(r => !r.success).map(r => r.message || 'Unknown error');

  return {
    success: successCount,
    failed: failedCount,
    total: updates.length,
    results,
    operationSummary: {
      operation: 'batchUpdateEnumValues',
      duration,
      errors,
    },
  };
}

/**
 * 批量删除枚举值
 */
export async function batchDeleteEnumValues(
  crud: DictionaryCoreCrud,
  typeId: string,
  valueIds: string[],
  batchSize: number = 50
): Promise<DictionaryBatchResult> {
  const startTime = Date.now();
  const results: DictionaryManagerResult[] = [];
  let successCount = 0;
  let failedCount = 0;

  const batches = chunkArray(valueIds, batchSize);

  for (const batch of batches) {
    const batchPromises = batch.map(async valueId => {
      try {
        const success = await crud.deleteEnumFieldValue(typeId, valueId);
        return {
          success,
          message: success ? `枚举值删除成功: ${valueId}` : `枚举值删除失败: ${valueId}`,
          operationType: 'batchDeleteEnumValues',
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        return {
          success: false,
          message: `枚举值删除失败: ${enhancedError.message}`,
          error: enhancedError.message,
          operationType: 'batchDeleteEnumValues',
          timestamp: new Date().toISOString(),
        };
      }
    });

    const batchResults = await Promise.allSettled(batchPromises);

    batchResults.forEach(promiseResult => {
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
  const errors = results.filter(r => !r.success).map(r => r.message || 'Unknown error');

  return {
    success: successCount,
    failed: failedCount,
    total: valueIds.length,
    results,
    operationSummary: {
      operation: 'batchDeleteEnumValues',
      duration,
      errors,
    },
  };
}

// ---------- 搜索 ----------

/**
 * 搜索枚举类型
 */
export async function searchEnumTypes(
  crud: DictionaryCoreCrud,
  keyword: string,
  filters?: {
    category?: string;
    status?: 'active' | 'inactive';
    is_system?: boolean;
  }
): Promise<EnumFieldType[]> {
  // 本地搜索：遍历已有枚举类型
  const allTypes = await crud.getEnumFieldTypes();
  const lowerKeyword = keyword.toLowerCase();

  return allTypes.filter(type => {
    let matches =
      type.name.toLowerCase().includes(lowerKeyword) ||
      type.code.toLowerCase().includes(lowerKeyword) ||
      (type.description !== undefined &&
        type.description !== null &&
        type.description.toLowerCase().includes(lowerKeyword));

    if (filters) {
      if (filters.category !== undefined && type.category !== filters.category) {
        matches = false;
      }
      if (filters.status !== undefined && type.status !== filters.status) {
        matches = false;
      }
      if (filters.is_system !== undefined && type.is_system !== filters.is_system) {
        matches = false;
      }
    }

    return matches;
  });
}

// ---------- 数据完整性验证 ----------

/**
 * 验证字典数据完整性
 */
export async function validateDictionaryData(
  crud: DictionaryCoreCrud,
  typeId: string
): Promise<{
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
    const types = await crud.getEnumFieldTypes();
    const targetType = types.find(t => t.id === typeId || t.code === typeId);

    if (!targetType) {
      issues.push(`字典类型不存在: ${typeId}`);
      return { isValid: false, issues, suggestions, warnings };
    }

    // 获取值信息
    const values = await crud.getEnumFieldValues(targetType.code);

    // 检查是否有值
    if (values.length === 0) {
      issues.push('字典类型没有任何值');
      suggestions.push('添加至少一个枚举值');
    }

    // 检查重复值
    const valueLabels = values.map(v => v.label.toLowerCase());
    const valueCodes = values.map(v => v.value.toLowerCase());
    const duplicateLabels = valueLabels.filter(
      (label, index) => valueLabels.indexOf(label) !== index
    );
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
      warnings,
    };
  } catch (error) {
    const enhancedError = ApiErrorHandler.handleError(error);
    return {
      isValid: false,
      issues: [`验证失败: ${enhancedError.message}`],
      suggestions: ['检查网络连接和权限'],
      warnings: [],
    };
  }
}

// ---------- 代码验证 ----------

/**
 * 验证枚举类型代码格式
 */
export function validateEnumTypeCode(code: string): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (code === undefined || code === null || code === '') {
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
    errors,
  };
}
