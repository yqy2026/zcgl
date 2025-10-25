/**
 * 统一字典服务
 * 整合系统字典和枚举字段功能，提供简化的使用接口
 */

import { apiClient } from './api'

export interface DictionaryOption {
  label: string
  value: string
  code?: string
  sort_order?: number
  color?: string
  icon?: string
}

export interface SimpleDictionaryData {
  options: Array<{
    label: string
    value: string
    code?: string
    description?: string
    sort_order?: number
    color?: string
    icon?: string
    is_active?: boolean
  }>
  description?: string
}

export interface DictionaryServiceResult {
  success: boolean
  data: DictionaryOption[]
  error?: string
  source?: string
}

class DictionaryService {
  /**
   * 获取字典选项（统一接口）
   */
  async getOptions(dictType: string, options: {
    useCache?: boolean
    useFallback?: boolean
    isActive?: boolean
  } = {}): Promise<DictionaryServiceResult> {
    const { useCache = true, useFallback = true, isActive: _isActive = true } = options

    try {
      const response = await apiClient.get(`dictionaries/${dictType}/options`, {
        params: { is_active: _isActive },
        timeout: 5000 // 5秒超时
      })
      const data = response.data || []

      return {
        success: true,
        data,
        source: 'api'
      }
    } catch (error: any) {
      // 只在真正错误时输出日志
      if (error.response?.status !== 404) {
        console.error(`❌ 获取字典选项失败 [${dictType}]:`, error.message)
      }

      // 如果API不存在（404），返回空数组而不是报错
      if (error.response?.status === 404) {
        return {
          success: true,
          data: [],
          source: 'not_found'
        }
      }

      // 为常用字典类型提供备用数据
      if (useFallback) {
        const fallbackData = this.getFallbackDictionaryData(dictType)
        if (fallbackData.length > 0) {
          return {
            success: true,
            data: fallbackData,
            source: 'fallback'
          }
        }
      }
      return {
        success: false,
        data: [],
        error: error.message || '获取字典数据失败',
        source: 'error'
      }
    }
  }

  /**
   * 批量获取字典选项
   */
  async getBatchOptions(dictTypes: string[], options: {
    useCache?: boolean
    useFallback?: boolean
    isActive?: boolean
  } = {}): Promise<Record<string, DictionaryServiceResult>> {
    const { useCache = true, useFallback = true, isActive: _isActive = true } = options

    const results: Record<string, DictionaryServiceResult> = {}

    // 并行请求所有字典类型
    const promises = dictTypes.map(async (dictType) => {
      try {
        const result = await this.getOptions(dictType, { useCache, useFallback, isActive: _isActive })
        results[dictType] = result
      } catch (error) {
        console.error(`批量获取字典失败 [${dictType}]:`, error)
        results[dictType] = {
          success: false,
          data: [],
          error: error instanceof Error ? error.message : '获取字典数据失败'
        }
      }
    })

    await Promise.all(promises)
    return results
  }

  /**
   * 获取备用字典数据（当API不可用时使用）
   */
  private getFallbackDictionaryData(dictType: string): DictionaryOption[] {
    const fallbackData: Record<string, DictionaryOption[]> = {
      ownership_category: [
        { label: '国资管理集团合并口径', value: '1', code: 'state_group_merged' },
        { label: '民政托管企业', value: '2', code: 'civil_administration_trustee' },
        { label: '其他', value: '3', code: 'other' }
      ],
      property_nature: [
        { label: '经营性', value: 'commercial', code: 'commercial' },
        { label: '非经营性', value: 'non_commercial', code: 'non_commercial' }
      ],
      usage_status: [
        { label: '出租', value: 'rented', code: 'rented' },
        { label: '空置', value: 'vacant', code: 'vacant' },
        { label: '自用', value: 'self_use', code: 'self_use' },
        { label: '公房', value: 'public_housing', code: 'public_housing' },
        { label: '待移交', value: 'pending_transfer', code: 'pending_transfer' },
        { label: '待处置', value: 'pending_disposal', code: 'pending_disposal' },
        { label: '其他', value: 'other', code: 'other' }
      ],
      ownership_status: [
        { label: '已确权', value: 'confirmed', code: 'confirmed' },
        { label: '未确权', value: 'unconfirmed', code: 'unconfirmed' },
        { label: '部分确权', value: 'partial', code: 'partial' }
      ],
      business_category: [
        { label: '商业', value: 'commercial', code: 'commercial' },
        { label: '办公', value: 'office', code: 'office' },
        { label: '住宅', value: 'residential', code: 'residential' },
        { label: '仓储', value: 'warehouse', code: 'warehouse' },
        { label: '工业', value: 'industrial', code: 'industrial' },
        { label: '其他', value: 'other', code: 'other' }
      ],
      certificated_usage: [
        { label: '商业', value: 'commercial', code: 'commercial' },
        { label: '办公', value: 'office', code: 'office' },
        { label: '住宅', value: 'residential', code: 'residential' },
        { label: '工业', value: 'industrial', code: 'industrial' },
        { label: '其他', value: 'other', code: 'other' }
      ],
      actual_usage: [
        { label: '商业', value: 'commercial', code: 'commercial' },
        { label: '办公', value: 'office', code: 'office' },
        { label: '住宅', value: 'residential', code: 'residential' },
        { label: '工业', value: 'industrial', code: 'industrial' },
        { label: '其他', value: 'other', code: 'other' }
      ],
      tenant_type: [
        { label: '个人', value: 'individual', code: 'individual' },
        { label: '企业', value: 'enterprise', code: 'enterprise' },
        { label: '政府机构', value: 'government', code: 'government' },
        { label: '其他', value: 'other', code: 'other' }
      ],
      contract_status: [
        { label: '生效中', value: 'active', code: 'active' },
        { label: '已到期', value: 'expired', code: 'expired' },
        { label: '已终止', value: 'terminated', code: 'terminated' },
        { label: '待签署', value: 'pending', code: 'pending' }
      ],
      business_model: [
        { label: '承租转租', value: 'sublease', code: 'sublease' },
        { label: '委托经营', value: 'entrusted', code: 'entrusted' },
        { label: '自营', value: 'self_operated', code: 'self_operated' },
        { label: '其他', value: 'other', code: 'other' }
      ],
      operation_status: [
        { label: '正常经营', value: 'normal', code: 'normal' },
        { label: '停业整顿', value: 'suspended', code: 'suspended' },
        { label: '装修中', value: 'renovating', code: 'renovating' },
        { label: '待招租', value: 'vacant_for_rent', code: 'vacant_for_rent' }
      ]
    }

    return fallbackData[dictType] || []
  }

  /**
   * 检查字典类型是否可用
   */
  isTypeAvailable(dictType: string): boolean {
    // 检查是否有备用数据
    const fallbackData = this.getFallbackDictionaryData(dictType)
    return fallbackData.length > 0
  }

  /**
   * 获取可用的字典类型列表
   */
  getAvailableTypes(): Array<{ code: string; name: string }> {
    return [
      { code: 'ownership_category', name: '权属类别' },
      { code: 'property_nature', name: '物业性质' },
      { code: 'usage_status', name: '使用状态' },
      { code: 'ownership_status', name: '确权状态' },
      { code: 'business_category', name: '业态类别' },
      { code: 'certificated_usage', name: '证载用途' },
      { code: 'actual_usage', name: '实际用途' },
      { code: 'tenant_type', name: '租户类型' },
      { code: 'contract_status', name: '合同状态' },
      { code: 'business_model', name: '经营模式' },
      { code: 'operation_status', name: '经营状态' }
    ]
  }

  /**
   * 快速创建字典
   */
  async quickCreate(dictType: string, data: SimpleDictionaryData): Promise<boolean> {
    try {
      await apiClient.post(`dictionaries/${dictType}/quick-create`, data)
      return true
    } catch (error) {
      console.error(`创建字典失败 [${dictType}]:`, error)
      return false
    }
  }

  /**
   * 获取所有字典类型
   */
  async getTypes(): Promise<string[]> {
    try {
      const response = await apiClient.get(`dictionaries/types`)
      return response.data
    } catch (error) {
      console.error('获取字典类型失败:', error)
      return []
    }
  }

  /**
   * 为字典类型添加新选项
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
      await apiClient.post(`dictionaries/${dictType}/values`, valueData)
      return true
    } catch (error) {
      console.error(`添加字典值失败 [${dictType}]:`, error)
      return false
    }
  }

  /**
   * 删除字典类型
   */
  async deleteType(dictType: string): Promise<boolean> {
    try {
      await apiClient.delete(`dictionaries/${dictType}`)
      return true
    } catch (error) {
      console.error(`删除字典类型失败 [${dictType}]:`, error)
      return false
    }
  }

  /**
   * 初始化常用字典（开发时使用）
   */
  async initializeCommonDictionaries(): Promise<void> {
    const commonDictionaries = {
      property_nature: {
        options: [
          { label: '经营性', value: 'commercial', code: 'commercial' },
          { label: '非经营性', value: 'non_commercial', code: 'non_commercial' }
        ],
        description: '物业性质分类'
      },
      usage_status: {
        options: [
          { label: '出租', value: 'rented', code: 'rented' },
          { label: '空置', value: 'vacant', code: 'vacant' },
          { label: '自用', value: 'self_use', code: 'self_use' },
          { label: '公房', value: 'public_housing', code: 'public_housing' },
          { label: '待移交', value: 'pending_transfer', code: 'pending_transfer' },
          { label: '待处置', value: 'pending_disposal', code: 'pending_disposal' },
          { label: '其他', value: 'other', code: 'other' }
        ],
        description: '资产使用状态分类'
      },
      ownership_status: {
        options: [
          { label: '已确权', value: 'confirmed', code: 'confirmed' },
          { label: '未确权', value: 'unconfirmed', code: 'unconfirmed' },
          { label: '部分确权', value: 'partial', code: 'partial' }
        ],
        description: '资产确权状态分类'
      },
      business_category: {
        options: [
          { label: '商业', value: 'commercial', code: 'commercial' },
          { label: '办公', value: 'office', code: 'office' },
          { label: '住宅', value: 'residential', code: 'residential' },
          { label: '仓储', value: 'warehouse', code: 'warehouse' },
          { label: '工业', value: 'industrial', code: 'industrial' },
          { label: '其他', value: 'other', code: 'other' }
        ],
        description: '资产业态分类'
      },
      ownership_category: {
        options: [
          { label: '国资管理集团合并口径', value: '1', code: 'state_group_merged' },
          { label: '民政托管企业', value: '2', code: 'civil_administration_trustee' },
          { label: '其他', value: '3', code: 'other' }
        ],
        description: '权属类别分类'
      }
    }

    for (const [dictType, dictData] of Object.entries(commonDictionaries)) {
      try {
        await this.quickCreate(dictType, dictData)
        console.log(`字典 ${dictType} 初始化成功`)
      } catch (error) {
        console.warn(`字典 ${dictType} 可能已存在`)
      }
    }
  }
}

export const dictionaryService = new DictionaryService()
export default dictionaryService