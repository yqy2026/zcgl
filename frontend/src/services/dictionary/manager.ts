/**
 * 字典管理服务
 * 提供字典的完整CRUD操作，主要用于管理界面
 */

import { apiRequest } from '@/utils/request'
import {
  DictionaryConfig,
  DictionaryOption,
  DICTIONARY_CONFIGS,
  getDictionaryConfig
} from './config'
import {
  globalDataCache,
  batchOptimizer,
  createCachedRequest,
  type DataCache
} from '@/utils/dataCache'

export interface EnumFieldType {
  id: string
  name: string
  code: string
  category?: string
  description?: string
  is_system: boolean
  is_multiple: boolean
  is_hierarchical: boolean
  default_value?: string
  status: 'active' | 'inactive'
  created_at: string
  updated_at: string
}

export interface EnumFieldValue {
  id: string
  enum_type_id: string
  label: string
  value: string
  code?: string
  description?: string
  parent_id?: string
  level: number
  sort_order: number
  color?: string
  icon?: string
  is_active: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface EnumFieldWithType {
  type: EnumFieldType
  values: EnumFieldValue[]
}

class DictionaryManagerService {
  private readonly API_BASE = '/enum-fields'

  /**
   * 获取所有枚举类型（用于管理界面）- 带缓存
   */
  async getEnumFieldTypes(): Promise<EnumFieldType[]> {
    const cacheKey = 'enum_field_types'

    // 尝试从缓存获取
    const cached = globalDataCache.get<EnumFieldType[]>(cacheKey)
    if (cached) {
      return cached
    }

    try {
      const response = await apiRequest.get(`${this.API_BASE}/types`)
      const data = response.data

      // 缓存结果（5分钟）
      globalDataCache.set(cacheKey, data, 5 * 60 * 1000)
      return data
    } catch (error) {
      console.error('获取枚举类型失败:', error)
      // 返回基于配置的备用数据
      return this.getFallbackEnumFieldTypes()
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
      default_value: null,
      status: 'active' as const,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }))
  }

  /**
   * 获取特定类型的枚举值
   */
  async getEnumFieldValues(typeId: string): Promise<EnumFieldValue[]> {
    try {
      const response = await apiRequest.get(`${this.API_BASE}/types/${typeId}/values`)
      return response.data
    } catch (error) {
      console.error(`获取枚举值失败 [${typeId}]:`, error)

      // 尝试从配置中获取备用数据（这里typeId是UUID，需要通过types映射找到对应的code）
      try {
        const types = await this.getEnumFieldTypes()
        const type = types.find(t => t.id === typeId)
        if (type) {
          const config = Object.values(DICTIONARY_CONFIGS).find(c => c.code === type.code)
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
            }))
          }
        }
      } catch (fallbackError) {
        console.warn('获取备用数据失败:', fallbackError)
      }

      return []
    }
  }

  /**
   * 获取完整的枚举字段数据（类型+值）
   */
  async getEnumFieldData(): Promise<EnumFieldWithType[]> {
    try {
      const types = await this.getEnumFieldTypes()
      const data: EnumFieldWithType[] = []

      for (const type of types) {
        const values = await this.getEnumFieldValues(type.id)  // 使用 type.id 而不是 type.code
        data.push({ type, values })
      }

      return data
    } catch (error) {
      console.error('获取枚举字段数据失败:', error)
      return []
    }
  }

  /**
   * 创建新的枚举类型
   */
  async createEnumFieldType(data: {
    name: string
    code: string
    category?: string
    description?: string
    is_multiple?: boolean
    is_hierarchical?: boolean
    default_value?: string
  }): Promise<EnumFieldType | null> {
    try {
      const response = await apiRequest.post(`${this.API_BASE}/types`, data)
      return response.data
    } catch (error) {
      console.error('创建枚举类型失败:', error)
      return null
    }
  }

  /**
   * 更新枚举类型
   */
  async updateEnumFieldType(
    typeId: string,
    data: Partial<{
      name: string
      code: string
      category?: string
      description?: string
      is_multiple: boolean
      is_hierarchical: boolean
      default_value?: string
      status: 'active' | 'inactive'
    }>
  ): Promise<EnumFieldType | null> {
    try {
      const response = await apiRequest.put(`${this.API_BASE}/types/${typeId}`, data)
      return response.data
    } catch (error) {
      console.error('更新枚举类型失败:', error)
      return null
    }
  }

  /**
   * 删除枚举类型
   */
  async deleteEnumFieldType(typeId: string): Promise<boolean> {
    try {
      await apiRequest.delete(`${this.API_BASE}/types/${typeId}`)
      // 清理相关缓存
      this.clearCache()
      return true
    } catch (error) {
      console.error('删除枚举类型失败:', error)
      return false
    }
  }

  /**
   * 添加枚举值
   */
  async addEnumFieldValue(
    typeId: string,
    data: {
      label: string
      value: string
      code?: string
      description?: string
      sort_order?: number
      color?: string
      icon?: string
      is_default?: boolean
    }
  ): Promise<EnumFieldValue | null> {
    try {
      const response = await apiRequest.post(`${this.API_BASE}/types/${typeId}/values`, data)
      return response.data
    } catch (error) {
      console.error('添加枚举值失败:', error)
      return null
    }
  }

  /**
   * 更新枚举值
   */
  async updateEnumFieldValue(
    typeId: string,
    valueId: string,
    data: Partial<{
      label: string
      value: string
      code?: string
      description?: string
      sort_order?: number
      color?: string
      icon?: string
      is_active: boolean
      is_default: boolean
    }>
  ): Promise<EnumFieldValue | null> {
    try {
      const response = await apiRequest.put(`${this.API_BASE}/types/${typeId}/values/${valueId}`, data)
      return response.data
    } catch (error) {
      console.error('更新枚举值失败:', error)
      return null
    }
  }

  /**
   * 删除枚举值
   */
  async deleteEnumFieldValue(typeId: string, valueId: string): Promise<boolean> {
    try {
      await apiRequest.delete(`${this.API_BASE}/types/${typeId}/values/${valueId}`)
      return true
    } catch (error) {
      console.error('删除枚举值失败:', error)
      return false
    }
  }

  /**
   * 获取枚举字段使用统计
   */
  async getEnumFieldUsageStats(typeId: string): Promise<{
    total_records: number
    active_records: number
    usage_by_field: Record<string, number>
  }> {
    try {
      const response = await apiRequest.get(`${this.API_BASE}/types/${typeId}/usage`)
      return response.data
    } catch (error) {
      console.error('获取枚举字段使用统计失败:', error)
      return {
        total_records: 0,
        active_records: 0,
        usage_by_field: {}
      }
    }
  }

  /**
   * 验证枚举类型代码
   */
  validateEnumTypeCode(code: string): { valid: boolean; errors: string[] } {
    const errors: string[] = []

    if (!code) {
      errors.push('代码不能为空')
    }

    if (!/^[a-z][a-z0-9_]*$/.test(code)) {
      errors.push('代码只能包含小写字母、数字和下划线，且必须以字母开头')
    }

    if (code.length > 50) {
      errors.push('代码长度不能超过50个字符')
    }

    // 检查是否与系统字典冲突
    if (code in DICTIONARY_CONFIGS) {
      errors.push('代码与系统字典冲突')
    }

    return {
      valid: errors.length === 0,
      errors
    }
  }

  /**
   * 导出枚举字段数据
   */
  async exportEnumFieldData(typeId: string): Promise<string> {
    try {
      const response = await apiRequest.get(`${this.API_BASE}/types/${typeId}/export`, {
        responseType: 'blob'
      })
      return URL.createObjectURL(response.data)
    } catch (error) {
      console.error('导出枚举字段数据失败:', error)
      throw error
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
      const formData = new FormData()
      formData.append('file', file)

      const response = await apiRequest.post(`${this.API_BASE}/types/${typeId}/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      // 导入完成后清理缓存
      this.clearCache()
      return response.data
    } catch (error) {
      console.error('导入枚举字段数据失败:', error)
      throw error
    }
  }

  /**
   * 清理相关缓存
   */
  private clearCache(): void {
    // 清理所有字典相关的缓存
    const cacheKeys = [
      'enum_field_types',
      'enum_field_data',
      'enum_field_values'
    ]

    cacheKeys.forEach(key => {
      // 删除匹配该模式的所有缓存
      globalDataCache.cache.forEach((_, cacheKey) => {
        if (cacheKey.includes(key)) {
          globalDataCache.cache.delete(cacheKey)
        }
      })
    })

    // 强制清理枚举类型缓存
    globalDataCache.cache.delete('enum_field_types')
  }

  /**
   * 预加载常用数据
   */
  async preloadData(): Promise<void> {
    try {
      // 预加载枚举类型
      await this.getEnumFieldTypes()

      // 预加载前10个类型的枚举值
      const types = await this.getEnumFieldTypes()
      const limitedTypes = types.slice(0, 10)

      await Promise.all(
        limitedTypes.map(type =>
          this.getEnumFieldValues(type.id).catch(() => {
            // 静默失败，不影响其他预加载
          })
        )
      )
    } catch (error) {
      console.warn('预加载数据失败:', error)
    }
  }
}

// 创建单例实例
export const dictionaryManagerService = new DictionaryManagerService()

// 为了向后兼容，导出默认实例
export default dictionaryManagerService