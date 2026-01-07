/**
 * 枚举字段管理相关类型定义
 */

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
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  enum_values?: EnumFieldValue[];
}

export interface EnumFieldValue {
  id: string;
  enum_type_id: string;
  label: string;
  value: string;
  code?: string;
  description?: string;
  parent_id?: string;
  level: number;
  path?: string;
  sort_order: number;
  color?: string;
  icon?: string;
  extra_properties?: Record<string, unknown>;
  is_active: boolean;
  is_default: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  children?: EnumFieldValue[];
}

export interface EnumFieldUsage {
  id: string;
  enum_type_id: string;
  table_name: string;
  field_name: string;
  field_label?: string;
  module_name?: string;
  is_required: boolean;
  default_value?: string;
  validation_config?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

export interface EnumFieldHistory {
  id: string;
  enum_type_id?: string;
  enum_value_id?: string;
  action: 'create' | 'update' | 'delete';
  target_type: 'type' | 'value';
  field_name?: string;
  old_value?: string;
  new_value?: string;
  change_reason?: string;
  created_at: string;
  created_by?: string;
  ip_address?: string;
}

export interface EnumFieldTree {
  id: string;
  label: string;
  value: string;
  code?: string;
  level: number;
  sort_order: number;
  is_active: boolean;
  color?: string;
  icon?: string;
  children: EnumFieldTree[];
}

export interface EnumFieldStatistics {
  total_types: number;
  active_types: number;
  total_values: number;
  active_values: number;
  usage_count: number;
  categories: Array<{
    name: string;
    count: number;
  }>;
}

// 创建和更新的表单数据类型
export interface EnumFieldTypeFormData {
  name: string;
  code: string;
  category?: string;
  description?: string;
  is_multiple?: boolean;
  is_hierarchical?: boolean;
  default_value?: string;
  validation_rules?: Record<string, unknown>;
  display_config?: Record<string, unknown>;
  status?: 'active' | 'inactive';
  created_by?: string;
  updated_by?: string;
}

export interface EnumFieldValueFormData {
  enum_type_id?: string;
  label: string;
  value: string;
  code?: string;
  description?: string;
  parent_id?: string;
  sort_order?: number;
  color?: string;
  icon?: string;
  extra_properties?: Record<string, unknown>;
  is_active?: boolean;
  is_default?: boolean;
  created_by?: string;
  updated_by?: string;
}

export interface EnumFieldUsageFormData {
  enum_type_id: string;
  table_name: string;
  field_name: string;
  field_label?: string;
  module_name?: string;
  is_required?: boolean;
  default_value?: string;
  validation_config?: Record<string, unknown>;
  is_active?: boolean;
  created_by?: string;
  updated_by?: string;
}

// 批量操作类型
export interface EnumFieldBatchCreate {
  enum_type_id: string;
  values: Array<Partial<EnumFieldValueFormData>>;
  created_by?: string;
}

export interface EnumFieldBatchUpdate {
  updates: Array<{
    id: string;
    data: Partial<EnumFieldValueFormData>;
  }>;
  updated_by?: string;
}

// API 响应类型
export interface EnumFieldTypeListResponse {
  data: EnumFieldType[];
  total: number;
}

export interface EnumFieldValueListResponse {
  data: EnumFieldValue[];
  total: number;
}

export interface EnumFieldUsageListResponse {
  data: EnumFieldUsage[];
  total: number;
}

// 查询参数类型
export interface EnumFieldTypeQueryParams {
  skip?: number;
  limit?: number;
  category?: string;
  status?: 'active' | 'inactive';
  is_system?: boolean;
  keyword?: string;
}

export interface EnumFieldValueQueryParams {
  parent_id?: string;
  is_active?: boolean;
}

export interface EnumFieldUsageQueryParams {
  enum_type_id?: string;
  table_name?: string;
  module_name?: string;
}

export interface EnumFieldHistoryQueryParams {
  skip?: number;
  limit?: number;
}
