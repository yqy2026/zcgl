/**
 * 统一字典服务 - DictionaryService 类
 *
 * @description 整合基础功能和管理功能，提供简化的使用接口和向后兼容性。
 *              批量操作、搜索、导出、健康检查等高级功能委托至 operations.ts。
 * @author Claude Code
 */

// 系统字典类型定义（向后兼容）
import type { SystemDictionary } from '@/types/asset';

// 导入服务实例
import { baseDictionaryService } from './base';
import {
  dictionaryManagerService,
  type CreateEnumFieldValueRequest,
  type UpdateEnumFieldValueRequest,
} from './manager';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { createLogger } from '@/utils/logger';

// 导入高级操作函数和接口
import {
  type DictionaryStats,
  type DictionaryOperationResult,
  batchOperation as batchOperationImpl,
  searchDictionaryValues as searchDictionaryValuesImpl,
  exportDictionaryData as exportDictionaryDataImpl,
  healthCheck as healthCheckImpl,
  getDictionaryStats as getDictionaryStatsImpl,
} from './operations';

// 再导出接口类型，保持向后兼容
export type { DictionaryStats, DictionaryOperationResult } from './operations';

const serviceLogger = createLogger('dictionaryService');

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
    return getDictionaryStatsImpl(this);
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
    return batchOperationImpl(this, operation, operations);
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
    return searchDictionaryValuesImpl(this, keyword, dictType);
  }

  /**
   * 导出字典数据
   */
  async exportDictionaryData(dictType?: string, format: 'json' | 'excel' = 'json'): Promise<Blob> {
    return exportDictionaryDataImpl(this, dictType, format);
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
    return healthCheckImpl(this);
  }
}

export const dictionaryService = new DictionaryService();

// 向后兼容：导出默认实例
export default dictionaryService;

export const enumFieldService = dictionaryManagerService;
