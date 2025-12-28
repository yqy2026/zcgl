/**
 * 字典配置文件
 * 集中管理所有字典类型的配置和备用数据
 */

import type { DictionaryOption } from '@/types/dictionary'

// Re-export DictionaryOption for backward compatibility
export type { DictionaryOption } from '@/types/dictionary'

export interface DictionaryConfig {
  code: string
  name: string
  category: string
  description: string
  apiEndpoint: string
  fallbackOptions: DictionaryOption[]
  tags?: string[]
  requiredFields?: string[]
}

/**
 * 系统字典类型配置
 */
export const DICTIONARY_CONFIGS: Record<string, DictionaryConfig> = {
  ownership_category: {
    code: 'ownership_category',
    name: '权属类别',
    category: '资产属性',
    description: '资产权属类别分类',
    apiEndpoint: '/dictionaries/ownership_category/options',
    fallbackOptions: [
      { label: '国有资产', value: 'state_owned', code: 'state_owned', sort_order: 1 },
      { label: '集体资产', value: 'collective', code: 'collective', sort_order: 2 },
      { label: '私有资产', value: 'private', code: 'private', sort_order: 3 },
      { label: '混合所有制', value: 'mixed', code: 'mixed', sort_order: 4 },
      { label: '其他', value: 'other', code: 'other', sort_order: 5 }
    ]
  },

  property_nature: {
    code: 'property_nature',
    name: '物业性质',
    category: '资产属性',
    description: '物业性质分类',
    apiEndpoint: '/dictionaries/property_nature/options',
    fallbackOptions: [
      { label: '经营性', value: 'commercial', code: 'commercial', sort_order: 1 },
      { label: '非经营性', value: 'non_commercial', code: 'non_commercial', sort_order: 2 }
    ]
  },

  usage_status: {
    code: 'usage_status',
    name: '使用状态',
    category: '资产状态',
    description: '资产使用状态分类',
    apiEndpoint: '/dictionaries/usage_status/options',
    fallbackOptions: [
      { label: '出租', value: 'rented', code: 'rented', sort_order: 1 },
      { label: '空置', value: 'vacant', code: 'vacant', sort_order: 2 },
      { label: '自用', value: 'self_use', code: 'self_use', sort_order: 3 },
      { label: '公房', value: 'public_housing', code: 'public_housing', sort_order: 4 },
      { label: '待移交', value: 'pending_transfer', code: 'pending_transfer', sort_order: 5 },
      { label: '待处置', value: 'pending_disposal', code: 'pending_disposal', sort_order: 6 },
      { label: '其他', value: 'other', code: 'other', sort_order: 7 }
    ]
  },

  ownership_status: {
    code: 'ownership_status',
    name: '权属状态',
    category: '资产状态',
    description: '资产权属状态分类',
    apiEndpoint: '/dictionaries/ownership_status/options',
    fallbackOptions: [
      { label: '已确权', value: 'confirmed', code: 'confirmed', sort_order: 1 },
      { label: '未确权', value: 'unconfirmed', code: 'unconfirmed', sort_order: 2 },
      { label: '部分确权', value: 'partial', code: 'partial', sort_order: 3 }
    ]
  },

  business_category: {
    code: 'business_category',
    name: '业态分类',
    category: '资产分类',
    description: '资产业态分类',
    apiEndpoint: '/dictionaries/business_category/options',
    fallbackOptions: [
      { label: '商业', value: 'commercial', code: 'commercial', sort_order: 1 },
      { label: '办公', value: 'office', code: 'office', sort_order: 2 },
      { label: '住宅', value: 'residential', code: 'residential', sort_order: 3 },
      { label: '仓储', value: 'warehouse', code: 'warehouse', sort_order: 4 },
      { label: '工业', value: 'industrial', code: 'industrial', sort_order: 5 },
      { label: '其他', value: 'other', code: 'other', sort_order: 6 }
    ]
  },

  certificated_usage: {
    code: 'certificated_usage',
    name: '证载用途',
    category: '资产用途',
    description: '证载用途分类',
    apiEndpoint: '/dictionaries/certificated_usage/options',
    fallbackOptions: [
      { label: '商业', value: 'commercial', code: 'commercial', sort_order: 1 },
      { label: '办公', value: 'office', code: 'office', sort_order: 2 },
      { label: '住宅', value: 'residential', code: 'residential', sort_order: 3 },
      { label: '工业', value: 'industrial', code: 'industrial', sort_order: 4 },
      { label: '其他', value: 'other', code: 'other', sort_order: 5 }
    ]
  },

  actual_usage: {
    code: 'actual_usage',
    name: '实际用途',
    category: '资产用途',
    description: '实际用途分类',
    apiEndpoint: '/dictionaries/actual_usage/options',
    fallbackOptions: [
      { label: '商业', value: 'commercial', code: 'commercial', sort_order: 1 },
      { label: '办公', value: 'office', code: 'office', sort_order: 2 },
      { label: '住宅', value: 'residential', code: 'residential', sort_order: 3 },
      { label: '工业', value: 'industrial', code: 'industrial', sort_order: 4 },
      { label: '其他', value: 'other', code: 'other', sort_order: 5 }
    ]
  },

  tenant_type: {
    code: 'tenant_type',
    name: '租户类型',
    category: '租赁信息',
    description: '租户类型分类',
    apiEndpoint: '/dictionaries/tenant_type/options',
    fallbackOptions: [
      { label: '个人', value: 'individual', code: 'individual', sort_order: 1 },
      { label: '企业', value: 'enterprise', code: 'enterprise', sort_order: 2 },
      { label: '政府机构', value: 'government', code: 'government', sort_order: 3 },
      { label: '其他', value: 'other', code: 'other', sort_order: 4 }
    ]
  },

  contract_status: {
    code: 'contract_status',
    name: '合同状态',
    category: '租赁信息',
    description: '合同状态分类',
    apiEndpoint: '/dictionaries/contract_status/options',
    fallbackOptions: [
      { label: '生效中', value: 'active', code: 'active', sort_order: 1 },
      { label: '已到期', value: 'expired', code: 'expired', sort_order: 2 },
      { label: '已终止', value: 'terminated', code: 'terminated', sort_order: 3 },
      { label: '待签署', value: 'pending', code: 'pending', sort_order: 4 }
    ]
  },

  business_model: {
    code: 'business_model',
    name: '经营模式',
    category: '经营信息',
    description: '经营模式分类',
    apiEndpoint: '/dictionaries/business_model/options',
    fallbackOptions: [
      { label: '承租转租', value: 'sublease', code: 'sublease', sort_order: 1 },
      { label: '委托经营', value: 'entrusted', code: 'entrusted', sort_order: 2 },
      { label: '自营', value: 'self_operated', code: 'self_operated', sort_order: 3 },
      { label: '其他', value: 'other', code: 'other', sort_order: 4 }
    ]
  },

  operation_status: {
    code: 'operation_status',
    name: '经营状态',
    category: '经营信息',
    description: '经营状态分类',
    apiEndpoint: '/dictionaries/operation_status/options',
    fallbackOptions: [
      { label: '正常经营', value: 'normal', code: 'normal', sort_order: 1 },
      { label: '停业整顿', value: 'suspended', code: 'suspended', sort_order: 2 },
      { label: '装修中', value: 'renovating', code: 'renovating', sort_order: 3 },
      { label: '待招租', value: 'vacant_for_rent', code: 'vacant_for_rent', sort_order: 4 }
    ]
  }
}

/**
 * 获取所有字典类型的配置
 */
export const getDictionaryConfigs = (): DictionaryConfig[] => {
  return Object.values(DICTIONARY_CONFIGS)
}

/**
 * 获取特定字典类型的配置
 */
export const getDictionaryConfig = (code: string): DictionaryConfig | null => {
  return DICTIONARY_CONFIGS[code] || null
}

/**
 * 获取所有字典类型的代码
 */
export const getDictionaryCodes = (): string[] => {
  return Object.keys(DICTIONARY_CONFIGS)
}

/**
 * 检查字典类型是否存在
 */
export const isDictionaryTypeExists = (code: string): boolean => {
  return code in DICTIONARY_CONFIGS
}