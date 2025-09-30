/**
 * 字典配置文件
 * 集中管理所有字典类型的配置和备用数据
 */

export interface DictionaryConfig {
  code: string
  name: string
  category: string
  description: string
  apiEndpoint: string
  fallbackOptions: DictionaryOption[]
}

export interface DictionaryOption {
  label: string
  value: string
  code?: string
  sort_order?: number
  color?: string
  icon?: string
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
    fallbackOptions: []
  },

  property_nature: {
    code: 'property_nature',
    name: '物业性质',
    category: '资产属性',
    description: '物业性质分类',
    apiEndpoint: '/dictionaries/property_nature/options',
    fallbackOptions: []
  },

  usage_status: {
    code: 'usage_status',
    name: '使用状态',
    category: '资产状态',
    description: '资产使用状态分类',
    apiEndpoint: '/dictionaries/usage_status/options',
    fallbackOptions: []
  },

  ownership_status: {
    code: 'ownership_status',
    name: '权属状态',
    category: '资产状态',
    description: '资产权属状态分类',
    apiEndpoint: '/dictionaries/ownership_status/options',
    fallbackOptions: []
  },

  business_category: {
    code: 'business_category',
    name: '业态分类',
    category: '资产分类',
    description: '资产业态分类',
    apiEndpoint: '/dictionaries/business_category/options',
    fallbackOptions: []
  },

  certificated_usage: {
    code: 'certificated_usage',
    name: '证载用途',
    category: '资产用途',
    description: '证载用途分类',
    apiEndpoint: '/dictionaries/certificated_usage/options',
    fallbackOptions: []
  },

  actual_usage: {
    code: 'actual_usage',
    name: '实际用途',
    category: '资产用途',
    description: '实际用途分类',
    apiEndpoint: '/dictionaries/actual_usage/options',
    fallbackOptions: []
  },

  tenant_type: {
    code: 'tenant_type',
    name: '租户类型',
    category: '租赁信息',
    description: '租户类型分类',
    apiEndpoint: '/dictionaries/tenant_type/options',
    fallbackOptions: []
  },

  contract_status: {
    code: 'contract_status',
    name: '合同状态',
    category: '租赁信息',
    description: '合同状态分类',
    apiEndpoint: '/dictionaries/contract_status/options',
    fallbackOptions: []
  },

  business_model: {
    code: 'business_model',
    name: '接收模式',
    category: '接收信息',
    description: '接收模式分类',
    apiEndpoint: '/dictionaries/business_model/options',
    fallbackOptions: []
  },

  operation_status: {
    code: 'operation_status',
    name: '经营状态',
    category: '经营信息',
    description: '经营状态分类',
    apiEndpoint: '/dictionaries/operation_status/options',
    fallbackOptions: []
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