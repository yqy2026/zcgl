/**
 * 统一字典服务入口 - 统一响应处理版本
 *
 * @description 整合基础功能和管理功能，提供简化的使用接口和向后兼容性
 * @author Claude Code
 */

// 导入核心功能
export * from './config';
export * from './base';
export * from './manager';

// 重新导出常用类型和接口
export type { DictionaryConfig, DictionaryOption } from './config';

export type { DictionaryServiceResult, DictionaryStatistics, PreloadResult } from './base';

export type {
  EnumFieldType,
  CreateEnumFieldValueRequest,
  UpdateEnumFieldValueRequest,
} from './manager';

// 系统字典类型定义（向后兼容）
import type { SystemDictionary } from '@/types/asset';

// 导入服务实例
import { baseDictionaryService } from './base';
import {
  dictionaryManagerService,
  type EnumFieldType,
  type EnumFieldValue,
  type CreateEnumFieldValueRequest,
  type UpdateEnumFieldValueRequest,
} from './manager';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '../../utils/responseExtractor';
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
 * 统一字典服务类
 * 整合基础功能和管理功能，提供简化的使用接口
 */
export class DictionaryService {
  // 基础功能 - 直接绑定到基础服务方法
  getOptions = baseDictionaryService.getOptions.bind(baseDictionaryService);
  getBatchOptions = baseDictionaryService.getBatchOptions.bind(baseDictionaryService);
  getParallelOptions = baseDictionaryService.getParallelOptions.bind(baseDictionaryService);
  getAvailableTypes = baseDictionaryService.getAvailableTypes.bind(baseDictionaryService);
  searchTypes = baseDictionaryService.searchTypes.bind(baseDictionaryService);
  isTypeAvailable = baseDictionaryService.isTypeAvailable.bind(baseDictionaryService);
  getTypeConfig = baseDictionaryService.getTypeConfig.bind(baseDictionaryService);
  clearCache = baseDictionaryService.clearCache.bind(baseDictionaryService);
  cleanupExpiredCache = baseDictionaryService.cleanupExpiredCache.bind(baseDictionaryService);
  preload = baseDictionaryService.preload.bind(baseDictionaryService);
  smartPreload = baseDictionaryService.smartPreload.bind(baseDictionaryService);
  getStats = baseDictionaryService.getStats.bind(baseDictionaryService);
  getCacheReport = baseDictionaryService.getCacheReport.bind(baseDictionaryService);
  refreshTypes = baseDictionaryService.refreshTypes.bind(baseDictionaryService);
  validateDictionaryData = baseDictionaryService.validateDictionaryData.bind(baseDictionaryService);

  // 管理功能 - 直接绑定到管理服务方法
  getEnumFieldTypes = dictionaryManagerService.getEnumFieldTypes.bind(dictionaryManagerService);
  getEnumFieldValues = dictionaryManagerService.getEnumFieldValues.bind(dictionaryManagerService);
  getEnumFieldData = dictionaryManagerService.getEnumFieldData.bind(dictionaryManagerService);
  createEnumFieldType = dictionaryManagerService.createEnumFieldType.bind(dictionaryManagerService);
  updateEnumFieldType = dictionaryManagerService.updateEnumFieldType.bind(dictionaryManagerService);
  deleteEnumFieldType = dictionaryManagerService.deleteEnumFieldType.bind(dictionaryManagerService);
  addEnumFieldValue = dictionaryManagerService.addEnumFieldValue.bind(dictionaryManagerService);
  updateEnumFieldValue =
    dictionaryManagerService.updateEnumFieldValue.bind(dictionaryManagerService);
  deleteEnumFieldValue =
    dictionaryManagerService.deleteEnumFieldValue.bind(dictionaryManagerService);
  getEnumFieldUsageStats =
    dictionaryManagerService.getEnumFieldUsageStats.bind(dictionaryManagerService);
  validateEnumTypeCode =
    dictionaryManagerService.validateEnumTypeCode.bind(dictionaryManagerService);
  exportEnumFieldData = dictionaryManagerService.exportEnumFieldData.bind(dictionaryManagerService);
  importEnumFieldData = dictionaryManagerService.importEnumFieldData.bind(dictionaryManagerService);

  /**
   * 向后兼容的方法 - 获取字典类型列表
   */
  async getTypes(): Promise<string[]> {
    try {
      const types = baseDictionaryService.getAvailableTypes();
      return types.map(config => config.code);
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      serviceLogger.error(`获取字典类型失败: ${apiError.message}`);
      return [];
    }
  }

  /**
   * 快速创建字典（向后兼容）
   */
  async quickCreate(
    dictType: string,
    _data: { options: Array<{ label: string; value: string }> }
  ): Promise<DictionaryOperationResult> {
    try {
      // 检查是否为系统字典类型
      const config = baseDictionaryService.getAvailableTypes().find(c => c.code === dictType);
      if (config !== undefined) {
        return {
          success: true,
          message: `字典类型已存在: ${dictType}`,
          operationType: 'quickCreate',
          timestamp: new Date().toISOString(),
        };
      }

      // 对于自定义字典类型，创建新的枚举类型
      const result = await this.createEnumFieldType({
        name: dictType,
        code: dictType,
        description: `自定义字典类型: ${dictType}`,
      });

      if (result) {
        return {
          success: true,
          message: `字典类型创建成功: ${dictType}`,
          data: result,
          operationType: 'quickCreate',
          timestamp: new Date().toISOString(),
        };
      } else {
        return {
          success: false,
          message: `字典类型创建失败: ${dictType}`,
          operationType: 'quickCreate',
          timestamp: new Date().toISOString(),
        };
      }
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      return {
        success: false,
        message: `快速创建字典失败 [${dictType}]: ${apiError.message}`,
        error: apiError.message,
        operationType: 'quickCreate',
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * 删除字典类型（向后兼容）
   */
  async deleteType(dictType: string): Promise<DictionaryOperationResult> {
    try {
      // 查找对应的枚举类型
      const types = await this.getEnumFieldTypes();
      const targetType = types.find(t => t.code === dictType);

      if (targetType !== undefined) {
        const success = await this.deleteEnumFieldType(targetType.id);
        return {
          success,
          message: success ? `字典类型删除成功: ${dictType}` : `字典类型删除失败: ${dictType}`,
          operationType: 'deleteType',
          timestamp: new Date().toISOString(),
        };
      }

      return {
        success: false,
        message: `字典类型不存在: ${dictType}`,
        operationType: 'deleteType',
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      return {
        success: false,
        message: `删除字典类型失败 [${dictType}]: ${apiError.message}`,
        error: apiError.message,
        operationType: 'deleteType',
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * 添加字典值（向后兼容）
   */
  async addValue(
    dictType: string,
    valueData: {
      label: string;
      value: string;
      code?: string;
      description?: string;
      sort_order?: number;
      color?: string;
      icon?: string;
    }
  ): Promise<DictionaryOperationResult> {
    try {
      const types = await this.getEnumFieldTypes();
      const targetType = types.find(t => t.code === dictType);

      if (targetType !== undefined) {
        const result = await this.addEnumFieldValue(targetType.id, valueData);
        if (result) {
          return {
            success: true,
            message: `字典值添加成功: ${valueData.label}`,
            data: result,
            operationType: 'addValue',
            timestamp: new Date().toISOString(),
          };
        }
      }

      return {
        success: false,
        message: `字典类型不存在: ${dictType}`,
        operationType: 'addValue',
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      return {
        success: false,
        message: `添加字典值失败 [${dictType}]: ${apiError.message}`,
        error: apiError.message,
        operationType: 'addValue',
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * 获取统一的字典统计信息
   */
  async getDictionaryStats(): Promise<DictionaryStats> {
    try {
      const startTime = Date.now();

      // 并行获取统计数据
      const [types, cacheStats, usageStats] = await Promise.allSettled([
        this.getEnumFieldTypes(),
        Promise.resolve(baseDictionaryService.getStats()),
        this.getEnumFieldUsageStats(''),
      ]);

      const enumTypes = types.status === 'fulfilled' ? types.value : [];
      const activeTypes = enumTypes.filter(t => t.status === 'active').length;
      const systemStatsValue = usageStats.status === 'fulfilled' ? usageStats.value : {};

      // 计算总数值
      let totalValues = 0;
      try {
        for (const type of enumTypes) {
          const values = await this.getEnumFieldValues(type.code);
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
            cacheStats.status === 'fulfilled'
              ? ((cacheStats.value as unknown as Record<string, number>)?.cacheHitRate ?? 0)
              : 0,
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

  /**
   * 获取系统字典（兼容旧系统）
   */
  async getSystemDictionaries(dictType: string): Promise<SystemDictionary[]> {
    try {
      const result = await apiClient.get<SystemDictionary[]>('/system/dictionaries', {
        params: { dict_type: dictType },
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (result.success) {
        return result.data!;
      }

      throw new Error(result.error ?? '获取系统字典失败');
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      serviceLogger.error(`获取系统字典失败 [${dictType}]: ${apiError.message}`);

      // 如果系统字典API失败，尝试从枚举字段获取
      try {
        return await this.getEnumFieldValuesByTypeCode(dictType);
      } catch (fallbackError) {
        serviceLogger.error(`备用方案也失败: ${String(fallbackError)}`);
        return [];
      }
    }
  }

  /**
   * 通过类型代码获取枚举值
   */
  async getEnumFieldValuesByTypeCode(typeCode: string): Promise<SystemDictionary[]> {
    try {
      const enumTypes = await this.getEnumFieldTypes();
      const targetType = enumTypes.find(t => t.code === typeCode);

      if (targetType !== undefined) {
        const values = await this.getEnumFieldValues(targetType.code);
        return values.map(value => ({
          id: value.id,
          dict_type: typeCode,
          dict_label: value.label,
          dict_value: value.value,
          dict_code: String(value.code ?? value.value ?? value.label),
          description: value.description,
          sort_order: value.sort_order,
          is_active: value.is_active,
          created_at: value.created_at,
          updated_at: value.updated_at,
        }));
      }

      return [];
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      serviceLogger.error(`通过类型代码获取枚举值失败 [${typeCode}]: ${apiError.message}`);
      return [];
    }
  }

  /**
   * 创建枚举值（简化接口）
   */
  async createEnumValue(
    typeId: string,
    data: CreateEnumFieldValueRequest
  ): Promise<DictionaryOperationResult> {
    try {
      const result = await this.addEnumFieldValue(typeId, data);
      if (result) {
        return {
          success: true,
          message: '枚举值创建成功',
          data: result,
          operationType: 'createEnumValue',
          timestamp: new Date().toISOString(),
        };
      }

      return {
        success: false,
        message: '枚举值创建失败',
        operationType: 'createEnumValue',
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      return {
        success: false,
        message: `创建枚举值失败: ${apiError.message}`,
        error: apiError.message,
        operationType: 'createEnumValue',
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * 更新枚举值（简化接口）
   */
  async updateEnumValue(
    valueId: string,
    data: UpdateEnumFieldValueRequest
  ): Promise<DictionaryOperationResult> {
    try {
      // 需要先获取值所属的类型ID
      const enumData = await this.getEnumFieldData();
      for (const item of enumData) {
        const value = item.values.find(v => v.id === valueId);
        if (value !== undefined) {
          const result = await this.updateEnumFieldValue(item.type.id, valueId, data);
          if (result) {
            return {
              success: true,
              message: '枚举值更新成功',
              data: result,
              operationType: 'updateEnumValue',
              timestamp: new Date().toISOString(),
            };
          }
        }
      }

      return {
        success: false,
        message: '未找到指定的枚举值',
        operationType: 'updateEnumValue',
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      return {
        success: false,
        message: `更新枚举值失败: ${apiError.message}`,
        error: apiError.message,
        operationType: 'updateEnumValue',
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * 删除枚举值（简化接口）
   */
  async deleteEnumValue(valueId: string): Promise<DictionaryOperationResult> {
    try {
      const enumData = await this.getEnumFieldData();
      for (const item of enumData) {
        const value = item.values.find(v => v.id === valueId);
        if (value !== undefined) {
          const success = await this.deleteEnumFieldValue(item.type.id, valueId);
          return {
            success,
            message: success ? '枚举值删除成功' : '枚举值删除失败',
            operationType: 'deleteEnumValue',
            timestamp: new Date().toISOString(),
          };
        }
      }

      return {
        success: false,
        message: '未找到指定的枚举值',
        operationType: 'deleteEnumValue',
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      return {
        success: false,
        message: `删除枚举值失败: ${apiError.message}`,
        error: apiError.message,
        operationType: 'deleteEnumValue',
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * 切换枚举值激活状态
   */
  async toggleEnumValueActive(
    valueId: string,
    isActive: boolean
  ): Promise<DictionaryOperationResult> {
    try {
      // 首先获取当前的枚举值信息
      const enumData = await this.getEnumFieldData();
      let currentValue = null;

      for (const item of enumData) {
        const value = item.values.find(v => v.id === valueId);
        if (value !== undefined) {
          currentValue = value;

          break;
        }
      }

      if (currentValue === undefined || currentValue === null) {
        return {
          success: false,
          message: '未找到指定的枚举值',
          operationType: 'toggleEnumValueActive',
          timestamp: new Date().toISOString(),
        };
      }

      // 然后更新状态，保持原有的其他字段
      const result = await this.updateEnumValue(valueId, {
        label: currentValue.label,
        value: currentValue.value,
        code: currentValue.code,
        description: currentValue.description,
        sort_order: currentValue.sort_order,
        is_active: isActive,
      });

      return result;
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      return {
        success: false,
        message: `切换枚举值状态失败: ${apiError.message}`,
        error: apiError.message,
        operationType: 'toggleEnumValueActive',
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * 批量操作字典值
   */
  async batchOperation(
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
              result = await this.createEnumValue(
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
              result = await this.updateEnumValue(
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
              result = await this.deleteEnumValue(op.valueId);
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

  /**
   * 搜索字典值
   */
  async searchDictionaryValues(
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
        const values = await this.getEnumFieldValuesByTypeCode(dictType);
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
        const types = await this.getEnumFieldTypes();

        for (const type of types.slice(0, 10)) {
          // 限制搜索的类型数量以避免性能问题
          try {
            const values = await this.getEnumFieldValues(type.code);
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

  /**
   * 导出字典数据
   */
  async exportDictionaryData(dictType?: string, format: 'json' | 'excel' = 'json'): Promise<Blob> {
    try {
      let data: unknown;

      if (dictType !== undefined) {
        // 导出特定类型的字典数据
        const values = await this.getEnumFieldValuesByTypeCode(dictType);
        data = {
          type: dictType,
          values: values,
          exportTime: new Date().toISOString(),
        };
        const _filename = `dictionary_${dictType}_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : 'json'}`;
      } else {
        // 导出所有字典数据
        const types = await this.getEnumFieldTypes();
        const allData: Record<string, unknown> = {
          types: [],
          values: [],
          exportTime: new Date().toISOString(),
        };

        for (const type of types) {
          const values = await this.getEnumFieldValues(type.code);
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
        return await this.exportEnumFieldData(dictType ?? 'all');
      }
    } catch (error) {
      const apiError = ApiErrorHandler.handleError(error);
      throw new Error(`导出字典数据失败: ${apiError.message}`);
    }
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{
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
      const types = await this.getEnumFieldTypes();
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
}

// 创建统一服务实例
export const dictionaryService = new DictionaryService();

// 向后兼容：导出默认实例
export default dictionaryService;

// 向后兼容：导出旧的接口名称
export const unifiedDictionaryService = dictionaryService;
export const enumFieldService = dictionaryManagerService;
