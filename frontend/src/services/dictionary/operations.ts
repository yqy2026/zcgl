/**
 * 字典服务高级操作 - 批量操作、搜索、导出、健康检查
 *
 * @description 从 DictionaryService 类中提取的独立函数实现，
 *              由 unified.ts 中的类方法委托调用。
 * @author Claude Code
 */

import type { SystemDictionary } from '@/types/asset';
import { baseDictionaryService } from './base';
import type {
  DictionaryUsageStats,
  EnumFieldType,
  EnumFieldValue,
  CreateEnumFieldValueRequest,
  UpdateEnumFieldValueRequest,
} from './manager';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { createLogger } from '@/utils/logger';

const serviceLogger = createLogger('dictionaryService');

/**
 * 字典统计信息接口
 */
export interface DictionaryStats {
  totalTypes: number;
  activeTypes: number;
  totalValues: number;
  cacheStats: unknown; // Use unknown to avoid circular dependency with DictionaryStatistics
  systemStats: {
    systemDictionariesCount: number;
    enumFieldTypesCount: number;
    lastUpdated: string;
  };
  performanceMetrics: {
    averageResponseTime: number;
    cacheHitRate: number;
    errorRate: number;
  };
}

/**
 * 字典操作结果接口
 */
export interface DictionaryOperationResult {
  success: boolean;
  message: string;
  data?: unknown;
  error?: string;
  operationType: string;
  timestamp: string;
}

/**
 * DictionaryService 接口子集，用于 operations 函数的类型约束。
 * 避免循环依赖：operations.ts 不导入 DictionaryService 类本身。
 */
export interface DictionaryServiceLike {
  getEnumFieldTypes: () => Promise<EnumFieldType[]>;
  getEnumFieldValues: (code: string) => Promise<EnumFieldValue[]>;
  getEnumFieldData: () => Promise<Array<{ type: EnumFieldType; values: EnumFieldValue[] }>>;
  getEnumFieldValuesByTypeCode: (typeCode: string) => Promise<SystemDictionary[]>;
  addEnumFieldValue: (typeId: string, data: CreateEnumFieldValueRequest) => Promise<EnumFieldValue | null>;
  updateEnumFieldValue: (typeId: string, valueId: string, data: UpdateEnumFieldValueRequest) => Promise<EnumFieldValue | null>;
  deleteEnumFieldValue: (typeId: string, valueId: string) => Promise<boolean>;
  getEnumFieldUsageStats: (code: string) => Promise<DictionaryUsageStats>;
  exportEnumFieldData: (typeCode: string) => Promise<Blob>;
  createEnumValue: (typeId: string, data: CreateEnumFieldValueRequest) => Promise<DictionaryOperationResult>;
  updateEnumValue: (valueId: string, data: UpdateEnumFieldValueRequest) => Promise<DictionaryOperationResult>;
  deleteEnumValue: (valueId: string) => Promise<DictionaryOperationResult>;
}

// ── 批量操作 ─────────────────────────────────────────────────

export async function batchOperation(
  svc: DictionaryServiceLike,
  operation: 'create' | 'update' | 'delete',
  operations: Array<{
    typeId?: string;
    valueId?: string;
    data: unknown;
  }>
): Promise<{
  success: number;
  failed: number;
  results: DictionaryOperationResult[];
}> {
  const results: DictionaryOperationResult[] = [];
  let successCount = 0;
  let failedCount = 0;

  for (const op of operations) {
    try {
      let result: DictionaryOperationResult;

      switch (operation) {
        case 'create':
          if (op.typeId !== undefined) {
            result = await svc.createEnumValue(
              op.typeId,
              op.data as CreateEnumFieldValueRequest
            );
          } else {
            result = {
              success: false,
              message: '批量创建操作缺少typeId',
              operationType: 'batchCreate',
              timestamp: new Date().toISOString(),
            };
          }
          break;

        case 'update':
          if (op.valueId !== undefined) {
            result = await svc.updateEnumValue(
              op.valueId,
              op.data as UpdateEnumFieldValueRequest
            );
          } else {
            result = {
              success: false,
              message: '批量更新操作缺少valueId',
              operationType: 'batchUpdate',
              timestamp: new Date().toISOString(),
            };
          }
          break;

        case 'delete':
          if (op.valueId !== undefined) {
            result = await svc.deleteEnumValue(op.valueId);
          } else {
            result = {
              success: false,
              message: '批量删除操作缺少valueId',
              operationType: 'batchDelete',
              timestamp: new Date().toISOString(),
            };
          }
          break;

        default:
          result = {
            success: false,
            message: `不支持的批量操作: ${operation}`,
            operationType: 'batchOperation',
            timestamp: new Date().toISOString(),
          };
      }

      results.push(result);
      if (result.success) {
        successCount++;
      } else {
        failedCount++;
      }
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      results.push({
        success: false,
        message: `批量操作失败: ${apiError.message}`,
        error: apiError.message,
        operationType: `batch${operation}`,
        timestamp: new Date().toISOString(),
      });
      failedCount++;
    }
  }

  return {
    success: successCount,
    failed: failedCount,
    results,
  };
}

// ── 搜索字典值 ───────────────────────────────────────────────

export async function searchDictionaryValues(
  svc: DictionaryServiceLike,
  keyword: string,
  dictType?: string
): Promise<
  {
    type: string;
    values: Array<{
      id: string;
      label: string;
      value: string;
      description?: string;
    }>;
  }[]
> {
  try {
    const results: Array<{
      type: string;
      values: Array<{
        id: string;
        label: string;
        value: string;
        description?: string;
      }>;
    }> = [];

    if (dictType !== undefined) {
      // 搜索特定类型的字典值
      const values = await svc.getEnumFieldValuesByTypeCode(dictType);
      const filteredValues = values.filter(
        item =>
          item.dict_label.toLowerCase().includes(keyword.toLowerCase()) ||
          item.dict_value.toLowerCase().includes(keyword.toLowerCase()) ||
          (item.description !== undefined &&
            item.description !== null &&
            item.description.toLowerCase().includes(keyword.toLowerCase()))
      );

      if (filteredValues.length > 0) {
        results.push({
          type: dictType,
          values: filteredValues.map(item => ({
            id: item.id,
            label: item.dict_label,
            value: item.dict_value,
            description: item.description,
          })),
        });
      }
    } else {
      // 搜索所有类型的字典值
      const types = await svc.getEnumFieldTypes();

      for (const type of types.slice(0, 10)) {
        // 限制搜索的类型数量以避免性能问题
        try {
          const values = await svc.getEnumFieldValues(type.code);
          const filteredValues = values.filter(
            item =>
              item.label.toLowerCase().includes(keyword.toLowerCase()) ||
              item.value.toLowerCase().includes(keyword.toLowerCase()) ||
              (item.description !== undefined &&
                item.description !== null &&
                item.description.toLowerCase().includes(keyword.toLowerCase()))
          );

          if (filteredValues.length > 0) {
            results.push({
              type: type.code,
              values: filteredValues.map(item => ({
                id: item.id,
                label: item.label,
                value: item.value,
                description: item.description,
              })),
            });
          }
        } catch (error) {
          serviceLogger.warn(`搜索字典类型 ${type.code} 时出错: ${String(error)}`);
        }
      }
    }

    return results;
  } catch (error) {
    const apiError = ApiErrorHandler.handleError(error);
    serviceLogger.error(`搜索字典值失败: ${apiError.message}`);
    return [];
  }
}

// ── 导出字典数据 ─────────────────────────────────────────────

export async function exportDictionaryData(
  svc: DictionaryServiceLike,
  dictType?: string,
  format: 'json' | 'excel' = 'json'
): Promise<Blob> {
  try {
    let data: unknown;

    if (dictType !== undefined) {
      // 导出特定类型的字典数据
      const values = await svc.getEnumFieldValuesByTypeCode(dictType);
      data = {
        type: dictType,
        values: values,
        exportTime: new Date().toISOString(),
      };
      const _filename = `dictionary_${dictType}_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : 'json'}`;
    } else {
      // 导出所有字典数据
      const types = await svc.getEnumFieldTypes();
      const allData: Record<string, unknown> = {
        types: [],
        values: [],
        exportTime: new Date().toISOString(),
      };

      for (const type of types) {
        const values = await svc.getEnumFieldValues(type.code);
        (allData.types as EnumFieldType[]).push(type);
        (allData.values as EnumFieldValue[]).push(
          ...values.map(v => ({ ...v, type_code: type.code }))
        );
      }

      data = allData;
      const _filename = `dictionary_all_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : 'json'}`;
    }

    if (format === 'json') {
      return new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    } else {
      // 使用内置的Excel导出功能
      return await svc.exportEnumFieldData(dictType ?? 'all');
    }
  } catch (error) {
    const apiError = ApiErrorHandler.handleError(error);
    throw new Error(`导出字典数据失败: ${apiError.message}`);
  }
}

// ── 健康检查 ─────────────────────────────────────────────────

export async function healthCheck(
  svc: DictionaryServiceLike
): Promise<{
  status: 'healthy' | 'degraded' | 'unhealthy';
  checks: Array<{
    name: string;
    status: 'pass' | 'fail';
    message?: string;
    responseTime?: number;
  }>;
  timestamp: string;
}> {
  const checks: Array<{
    name: string;
    status: 'pass' | 'fail';
    message?: string;
    responseTime?: number;
  }> = [];
  let overallStatus: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';

  // 检查基础字典服务
  try {
    const startTime = Date.now();
    const baseStats = baseDictionaryService.getStats();
    const responseTime = Date.now() - startTime;

    checks.push({
      name: 'base_dictionary_service',
      status: 'pass',
      message: `缓存命中: ${(baseStats.cacheHitRate * 100).toFixed(1)}%`,
      responseTime,
    });
  } catch {
    checks.push({
      name: 'base_dictionary_service',
      status: 'fail',
      message: '基础字典服务异常',
    });
    overallStatus = 'unhealthy';
  }

  // 检查枚举字段管理服务
  try {
    const startTime = Date.now();
    const types = await svc.getEnumFieldTypes();
    const responseTime = Date.now() - startTime;

    checks.push({
      name: 'enum_field_manager',
      status: 'pass',
      message: `已加载${types.length}个枚举类型`,
      responseTime,
    });
  } catch {
    checks.push({
      name: 'enum_field_manager',
      status: 'fail',
      message: '枚举字段管理服务异常',
    });
    if (overallStatus === 'healthy') {
      overallStatus = 'degraded';
    }
  }

  return {
    status: overallStatus,
    checks,
    timestamp: new Date().toISOString(),
  };
}

// ── 获取统一的字典统计信息 ──────────────────────────────────

export async function getDictionaryStats(
  svc: DictionaryServiceLike
): Promise<DictionaryStats> {
  try {
    const startTime = Date.now();

    // 并行获取统计数据
    const [types, cacheStats, usageStats] = await Promise.allSettled([
      svc.getEnumFieldTypes(),
      Promise.resolve(baseDictionaryService.getStats()),
      svc.getEnumFieldUsageStats(''),
    ]);

    const enumTypes = types.status === 'fulfilled' ? types.value : [];
    const activeTypes = enumTypes.filter(t => t.status === 'active').length;
    const systemStatsValue = usageStats.status === 'fulfilled' ? usageStats.value : {};

    // 计算总数值
    let totalValues = 0;
    try {
      for (const type of enumTypes) {
        const values = await svc.getEnumFieldValues(type.code);
        totalValues += values.length;
      }
    } catch (error) {
      serviceLogger.warn(`计算总数值时出错: ${String(error)}`);
    }

    const responseTime = Date.now() - startTime;

    return {
      totalTypes: enumTypes.length,
      activeTypes,
      totalValues,
      cacheStats,
      systemStats: {
        systemDictionariesCount: enumTypes.length,
        enumFieldTypesCount: enumTypes.length,
        lastUpdated: new Date().toISOString(),
        ...systemStatsValue,
      },
      performanceMetrics: {
        averageResponseTime: responseTime,
        cacheHitRate:
          cacheStats.status === 'fulfilled' ? (cacheStats.value.cacheHitRate ?? 0) : 0,
        errorRate: types.status === 'rejected' || usageStats.status === 'rejected' ? 1 : 0,
      },
    };
  } catch (error) {
    const apiError = ApiErrorHandler.handleError(error);
    serviceLogger.error(`获取字典统计失败: ${apiError.message}`);

    // 返回默认统计信息
    return {
      totalTypes: 0,
      activeTypes: 0,
      totalValues: 0,
      cacheStats: baseDictionaryService.getStats(),
      systemStats: {
        systemDictionariesCount: 0,
        enumFieldTypesCount: 0,
        lastUpdated: new Date().toISOString(),
      },
      performanceMetrics: {
        averageResponseTime: 0,
        cacheHitRate: 0,
        errorRate: 1,
      },
    };
  }
}
