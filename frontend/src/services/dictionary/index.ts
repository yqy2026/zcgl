/**
 * 统一字典服务入口
 * 提供简化的使用接口和向后兼容性
 */

// 导入核心功能
export * from './config'
export * from './base'
export * from './manager'

// 重新导出常用类型和接口
export type {
  DictionaryConfig,
  DictionaryOption
} from './config'

export type {
  DictionaryServiceResult
} from './base'

export type {
  EnumFieldType,
  EnumFieldValue,
  EnumFieldWithType
} from './manager'

// 系统字典类型定义（向后兼容）
export interface SystemDictionary {
  id: string
  dict_type: string
  dict_label: string
  dict_value: string
  dict_code?: string
  description?: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// 导入服务实例
import { baseDictionaryService } from './base'
import { dictionaryManagerService } from './manager'
import { apiClient } from '../api'
import { API_CONFIG } from '../config'

/**
 * 统一字典服务类
 * 整合基础功能和管理功能，提供简化的使用接口
 */
class UnifiedDictionaryService {
  // 基础功能
  getOptions = baseDictionaryService.getOptions.bind(baseDictionaryService)
  getBatchOptions = baseDictionaryService.getBatchOptions.bind(baseDictionaryService)
  getAvailableTypes = baseDictionaryService.getAvailableTypes.bind(baseDictionaryService)
  isTypeAvailable = baseDictionaryService.isTypeAvailable.bind(baseDictionaryService)
  clearCache = baseDictionaryService.clearCache.bind(baseDictionaryService)
  preload = baseDictionaryService.preload.bind(baseDictionaryService)
  getStats = baseDictionaryService.getStats.bind(baseDictionaryService)

  // 管理功能
  getEnumFieldTypes = dictionaryManagerService.getEnumFieldTypes.bind(dictionaryManagerService)
  getEnumFieldValues = dictionaryManagerService.getEnumFieldValues.bind(dictionaryManagerService)
  getEnumFieldData = dictionaryManagerService.getEnumFieldData.bind(dictionaryManagerService)
  createEnumFieldType = dictionaryManagerService.createEnumFieldType.bind(dictionaryManagerService)
  updateEnumFieldType = dictionaryManagerService.updateEnumFieldType.bind(dictionaryManagerService)
  deleteEnumFieldType = dictionaryManagerService.deleteEnumFieldType.bind(dictionaryManagerService)
  addEnumFieldValue = dictionaryManagerService.addEnumFieldValue.bind(dictionaryManagerService)
  updateEnumFieldValue = dictionaryManagerService.updateEnumFieldValue.bind(dictionaryManagerService)
  deleteEnumFieldValue = dictionaryManagerService.deleteEnumFieldValue.bind(dictionaryManagerService)
  getEnumFieldUsageStats = dictionaryManagerService.getEnumFieldUsageStats.bind(dictionaryManagerService)
  validateEnumTypeCode = dictionaryManagerService.validateEnumTypeCode.bind(dictionaryManagerService)
  exportEnumFieldData = dictionaryManagerService.exportEnumFieldData.bind(dictionaryManagerService)
  importEnumFieldData = dictionaryManagerService.importEnumFieldData.bind(dictionaryManagerService)

  /**
   * 向后兼容的方法
   */
  async getTypes(): Promise<string[]> {
    return Object.keys(baseDictionaryService.getAvailableTypes().reduce((acc, config) => {
      acc[config.code] = config
      return acc
    }, {} as Record<string, any>))
  }

  /**
   * 快速创建字典（向后兼容）
   */
  async quickCreate(dictType: string, _data: { options: Array<{ label: string; value: string }> }): Promise<boolean> {
    try {
      // 检查是否为系统字典类型
      const config = baseDictionaryService.getAvailableTypes().find(c => c.code === dictType)
      if (config) {
        // Dictionary type already exists, skip creation
        return true
      }

      // 对于自定义字典类型，创建新的枚举类型
      return await this.createEnumFieldType({
        name: dictType,
        code: dictType,
        description: `自定义字典类型: ${dictType}`
      }) !== null
    } catch (error) {
      console.error(`快速创建字典失败 [${dictType}]:`, error)
      return false
    }
  }

  /**
   * 删除字典类型（向后兼容）
   */
  async deleteType(dictType: string): Promise<boolean> {
    try {
      // 查找对应的枚举类型
      const types = await this.getEnumFieldTypes()
      const targetType = types.find(t => t.code === dictType)

      if (targetType) {
        return await this.deleteEnumFieldType(targetType.id)
      }

      console.warn(`字典类型不存在 [${dictType}]`)
      return false
    } catch (error) {
      console.error(`删除字典类型失败 [${dictType}]:`, error)
      return false
    }
  }

  /**
   * 添加字典值（向后兼容）
   */
  async addValue(dictType: string, valueData: {
    label: string
    value: string
    code?: string
    description?: string
    sort_order?: number
    color?: string
    icon?: string
  }): Promise<boolean> {
    try {
      const types = await this.getEnumFieldTypes()
      const targetType = types.find(t => t.code === dictType)

      if (targetType) {
        return await this.addEnumFieldValue(targetType.id, valueData) !== null
      }

      console.warn(`字典类型不存在 [${dictType}]`)
      return false
    } catch (error) {
      console.error(`添加字典值失败 [${dictType}]:`, error)
      return false
    }
  }

  /**
   * 获取字典统计信息
   */
  async getDictionaryStats(): Promise<{
    totalTypes: number
    activeTypes: number
    totalValues: number
    cacheStats: ReturnType<typeof baseDictionaryService.getStats>
  }> {
    try {
      const types = await this.getEnumFieldTypes()
      const activeTypes = types.filter(t => t.status === 'active').length

      let totalValues = 0
      for (const type of types) {
        const values = await this.getEnumFieldValues(type.code)
        totalValues += values.length
      }

      const cacheStats = baseDictionaryService.getStats()

      return {
        totalTypes: types.length,
        activeTypes,
        totalValues,
        cacheStats
      }
    } catch (error) {
      console.error('获取字典统计失败:', error)
      return {
        totalTypes: 0,
        activeTypes: 0,
        totalValues: 0,
        cacheStats: baseDictionaryService.getStats()
      }
    }
  }

  /**
   * 获取系统字典（兼容旧系统）
   */
  async getSystemDictionaries(dictType: string): Promise<any[]> {
    try {
      const response = await apiClient.get(API_CONFIG.ENDPOINTS.DICTIONARIES.LIST_SYSTEM, {
        params: { dict_type: dictType }
      })
      return response.data
    } catch (error) {
      console.error(`获取系统字典失败 [${dictType}]:`, error)
      // 如果系统字典API失败，尝试从枚举字段获取
      try {
        const enumTypes = await this.getEnumFieldTypes()
        const targetType = enumTypes.find(t => t.code === dictType)
        if (targetType) {
          const values = await this.getEnumFieldValues(targetType.id)
          return values.map(value => ({
            id: value.id,
            dict_type: dictType,
            dict_label: value.label,
            dict_value: value.value,
            dict_code: value.code,
            description: value.description,
            sort_order: value.sort_order,
            is_active: value.is_active,
            created_at: value.created_at,
            updated_at: value.updated_at
          }))
        }
      } catch (fallbackError) {
        console.error('备用方案也失败:', fallbackError)
      }
      return []
    }
  }

  /**
   * 通过类型代码获取枚举值
   */
  async getEnumFieldValuesByTypeCode(typeCode: string): Promise<any[]> {
    try {
      const enumTypes = await this.getEnumFieldTypes()
      const targetType = enumTypes.find(t => t.code === typeCode)

      if (targetType) {
        const values = await this.getEnumFieldValues(targetType.id)
        return values.map(value => ({
          id: value.id,
          dict_type: typeCode,
          dict_label: value.label,
          dict_value: value.value,
          dict_code: value.code,
          description: value.description,
          sort_order: value.sort_order,
          is_active: value.is_active,
          created_at: value.created_at,
          updated_at: value.updated_at
        }))
      }
      return []
    } catch (error) {
      console.error(`通过类型代码获取枚举值失败 [${typeCode}]:`, error)
      return []
    }
  }

  /**
   * 创建枚举值（简化接口）
   */
  async createEnumValue(typeId: string, data: {
    label: string
    value: string
    code?: string
    description?: string
    sort_order?: number
  }): Promise<boolean> {
    try {
      const result = await this.addEnumFieldValue(typeId, data)
      return result !== null
    } catch (error) {
      console.error('创建枚举值失败:', error)
      return false
    }
  }

  /**
   * 更新枚举值（简化接口）
   */
  async updateEnumValue(valueId: string, data: {
    label: string
    value: string
    code?: string
    description?: string
    sort_order?: number
    is_active?: boolean
  }): Promise<boolean> {
    try {
      // 需要先获取值所属的类型ID
      const enumData = await this.getEnumFieldData()
      for (const item of enumData) {
        const value = item.values.find(v => v.id === valueId)
        if (value) {
          const result = await this.updateEnumFieldValue(item.type.id, valueId, data)
          return result !== null
        }
      }
      return false
    } catch (error) {
      console.error('更新枚举值失败:', error)
      return false
    }
  }

  /**
   * 删除枚举值（简化接口）
   */
  async deleteEnumValue(valueId: string): Promise<boolean> {
    try {
      const enumData = await this.getEnumFieldData()
      for (const item of enumData) {
        const value = item.values.find(v => v.id === valueId)
        if (value) {
          return await this.deleteEnumFieldValue(item.type.id, valueId)
        }
      }
      return false
    } catch (error) {
      console.error('删除枚举值失败:', error)
      return false
    }
  }

  /**
   * 切换枚举值激活状态
   */
  async toggleEnumValueActive(valueId: string, isActive: boolean): Promise<boolean> {
    try {
      // 首先获取当前的枚举值信息
      const enumData = await this.getEnumFieldData()
      let currentValue = null
      for (const item of enumData) {
        const value = item.values.find(v => v.id === valueId)
        if (value) {
          currentValue = value
          break
        }
      }
      if (!currentValue) {
        console.error('未找到指定的枚举值')
        return false
      }

      // 然后更新状态，保持原有的其他字段
      return await this.updateEnumValue(valueId, {
        label: currentValue.label,
        value: currentValue.value,
        code: currentValue.code,
        description: currentValue.description,
        sort_order: currentValue.sort_order,
        is_active: isActive
      })
    } catch (error) {
      console.error('切换枚举值状态失败:', error)
      return false
    }
  }
}

// 创建统一服务实例
export const dictionaryService = new UnifiedDictionaryService()

// 向后兼容：导出默认实例
export default dictionaryService

// 向后兼容：导出旧的接口名称
export const unifiedDictionaryService = dictionaryService
export const enumFieldService = dictionaryManagerService
