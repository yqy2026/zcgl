/**
 * 字典管理服务 - 类型定义
 *
 * @description 枚举字段类型、枚举值、批量操作结果等所有接口定义
 * @module dictionaryTypes
 */

// 枚举字段类型接口
export interface EnumFieldType {
  id: string;
  name: string;
  code: string;
  category?: string;
  description?: string;
  is_system: boolean;
  is_multiple: boolean;
  is_hierarchical: boolean;
  default_value?: string;
  validation_rules?: Record<string, unknown>;
  display_config?: Record<string, unknown>;
  status: 'active' | 'inactive';
  is_deleted?: boolean;
  created_by?: string;
  updated_by?: string;
  created_at: string;
  updated_at: string;
  enum_values?: Array<{
    id: string;
    enum_type_id: string;
    label: string;
    value: string;
    code?: string;
    description?: string;
    parent_id?: string;
    level: number;
    sort_order: number;
    color?: string;
    icon?: string;
    extra_properties?: Record<string, unknown>;
    is_active: boolean;
    is_default: boolean;
    path?: string;
    is_deleted?: boolean;
    created_at: string;
    updated_at: string;
    created_by?: string;
    updated_by?: string;
    children?: unknown[];
  }>;
}

// 枚举字段值接口
export interface EnumFieldValue {
  id: string;
  enum_type_id: string;
  label: string;
  value: string;
  code?: string;
  description?: string;
  parent_id?: string;
  level: number;
  sort_order: number;
  color?: string;
  icon?: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

// 枚举字段与值的组合接口
export interface EnumFieldWithType {
  type: EnumFieldType;
  values: EnumFieldValue[];
}

// 字典管理操作结果接口
export interface DictionaryManagerResult<T = unknown> {
  success: boolean;
  data?: T;
  message: string;
  error?: string;
  operationType: string;
  timestamp: string;
}

// 字典使用统计接口
export interface DictionaryUsageStats {
  total_records: number;
  active_records: number;
  usage_by_field: Record<string, number>;
  last_updated: string;
  popular_values: Array<{
    value: string;
    label: string;
    usage_count: number;
  }>;
}

// 字典批量操作结果接口
export interface DictionaryBatchResult {
  success: number;
  failed: number;
  total: number;
  results: DictionaryManagerResult[];
  operationSummary: {
    operation: string;
    duration: number; // 毫秒
    errors: string[];
  };
}

// 创建枚举类型请求接口
export interface CreateEnumFieldTypeRequest {
  name: string;
  code: string;
  category?: string;
  description?: string;
  is_multiple?: boolean;
  is_hierarchical?: boolean;
  default_value?: string;
}

// 更新枚举类型请求接口
export interface UpdateEnumFieldTypeRequest {
  name?: string;
  code?: string;
  category?: string;
  description?: string;
  is_multiple?: boolean;
  is_hierarchical?: boolean;
  default_value?: string;
  status?: 'active' | 'inactive';
}

// 创建枚举值请求接口
export interface CreateEnumFieldValueRequest {
  label: string;
  value: string;
  code?: string;
  description?: string;
  sort_order?: number;
  color?: string;
  icon?: string;
  is_default?: boolean;
}

// 更新枚举值请求接口
export interface UpdateEnumFieldValueRequest {
  label?: string;
  value?: string;
  code?: string;
  description?: string;
  sort_order?: number;
  color?: string;
  icon?: string;
  is_active?: boolean;
  is_default?: boolean;
}
