/**
 * 字典管理服务
 * 提供字典的完整CRUD操作，主要用于管理界面
 */

import { apiClient } from '../api'
import { API_CONFIG } from '../config'
import {
  DictionaryOption,
  DICTIONARY_CONFIGS
} from './config'

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
  validation_rules?: any
  display_config?: any
  status: 'active' | 'inactive'
  is_deleted?: boolean
  created_by?: string
  updated_by?: string
  created_at: string
  updated_at: string
  enum_values?: Array<{
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
    extra_properties?: any
    is_active: boolean
    is_default: boolean
    path?: string
    is_deleted?: boolean
    created_at: string
    updated_at: string
    created_by?: string
    updated_by?: string
    children?: any[]
  }>
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
  /**
   * 获取所有枚举类型（用于管理界面）
   */
  async getEnumFieldTypes(): Promise<EnumFieldType[]> {
    try {
      const response = await apiClient.get(API_CONFIG.ENDPOINTS.DICTIONARIES.TYPES)
      console.log('🔍 [manager] getEnumFieldTypes 响应类型:', typeof response)
      console.log('🔍 [manager] getEnumFieldTypes 响应内容:', response)

      // apiClient 直接返回数据，而不是包装在 response.data 中
      const data = response

      // 处理后端返回的字符串数组，转换为完整的枚举类型对象数组
      if (Array.isArray(data)) {
        // 如果是字符串数组，转换为完整的枚举类型对象
        const enumTypes: EnumFieldType[] = data.map((typeCode: string, index: number) => {
          // 从DICTIONARY_CONFIGS中查找配置
          const config = Object.values(DICTIONARY_CONFIGS).find(c => c.code === typeCode)

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
          }
        })

        console.log('✅ [manager] getEnumFieldTypes 转换结果:', enumTypes)
        return enumTypes
      }

      // 如果不是数组，尝试作为对象数组处理
      if (data && typeof data === 'object') {
        const enumTypes = Array.isArray(data) ? data : [data]
        console.log('✅ [manager] getEnumFieldTypes 对象数组结果:', enumTypes)
        return enumTypes
      }

      console.warn('⚠️ [manager] getEnumFieldTypes: 响应数据不是预期的格式')
      return []
    } catch (error) {
      console.error('❌ 获取枚举类型失败:', error)
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
      default_value: undefined,
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
      console.log(`🔍 [manager] getEnumFieldValues 调用, typeId: ${typeId}`)

      // 优先尝试直接从字典API获取（支持类型代码）
      console.log(`📡 [manager] 尝试从字典API获取: /dictionaries/${typeId}/options`)
      const response = await apiClient.get(`/dictionaries/${typeId}/options`)
      console.log(`✅ [manager] 字典API响应成功, 数据类型: ${typeof response}, 数据长度: ${response?.length || 0}`)

      // apiClient 直接返回数据，不是包装的响应对象
      const data = Array.isArray(response) ? response : (response.data || [])

      const mappedData = data.map((option: any, index: number) => {
        console.log(`🏷️ [manager] 映射选项 ${index}:`, {
          originalLabel: option.label,
          originalValue: option.value,
          mappedLabel: option.label,
          mappedValue: option.value
        })

        return {
          id: option.id || `dict-${typeId}-${index}`,
          enum_type_id: typeId,
          label: option.label,
          value: option.value,
          code: option.code,
          description: option.description,
          level: 1,
          sort_order: option.sort_order || index + 1,
          color: option.color,
          icon: option.icon,
          is_active: option.is_active !== false,
          is_default: index === 0,
          created_at: option.created_at || new Date().toISOString(),
          updated_at: option.updated_at || new Date().toISOString()
        }
      })

      console.log(`🎯 [manager] 最终映射完成, 返回 ${mappedData.length} 个选项`)
      return mappedData

    } catch (error) {
      console.error(`❌ 获取枚举值失败 [${typeId}]:`, error)

      // 尝试从配置中获取备用数据
      const config = Object.values(DICTIONARY_CONFIGS).find(c => c.code === typeId)
      if (config) {
        console.log(`💾 [manager] 使用备用配置数据: ${typeId}`)
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

      console.log(`🚫 [manager] 没有找到任何数据，返回空数组`)
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

      // 安全检查：确保types是可迭代的数组
      if (!Array.isArray(types)) {
        console.warn('getEnumFieldData: types is not an array, using empty array')
        return []
      }

      for (const type of types) {
        // 优先使用type.code作为字典类型代码来获取枚举值
        let values: EnumFieldValue[] = []

        // 首先尝试使用type.code获取枚举值
        if (type.code) {
          values = await this.getEnumFieldValues(type.code)
        }

        // 如果没有获取到值，则尝试使用type.id
        if (values.length === 0 && type.id) {
          values = await this.getEnumFieldValues(type.id)
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
          }))
        }

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
      const response = await apiClient.post(`${API_CONFIG.ENDPOINTS.DICTIONARIES.BASE}/types`, data)
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
      const response = await apiClient.put(`${API_CONFIG.ENDPOINTS.DICTIONARIES.BASE}/types/${typeId}`, data)
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
      await apiClient.delete(`${API_CONFIG.ENDPOINTS.DICTIONARIES.BASE}/types/${typeId}`)
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
      const response = await apiClient.post(`/dictionaries/${typeId}/values`, data)
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
      const response = await apiClient.put(`/dictionaries/${typeId}/values/${valueId}`, data)
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
      await apiClient.delete(`/dictionaries/${typeId}/values/${valueId}`)
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
      const response = await apiClient.get(`/dictionaries/${typeId}/usage`)
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
      const response = await apiClient.get(`/dictionaries/${typeId}/export`, {
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

      const response = await apiClient.post(`/dictionaries/${typeId}/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      return response.data
    } catch (error) {
      console.error('导入枚举字段数据失败:', error)
      throw error
    }
  }
}

// 创建单例实例
export const dictionaryManagerService = new DictionaryManagerService()

// 为了向后兼容，导出默认实例
export default dictionaryManagerService
