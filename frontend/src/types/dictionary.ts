/**
 * 字典管理相关类型定义
 */

// 枚举字段值类型 - 完整定义，与services/dictionary/manager.ts保持一致
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
  enum_values?: EnumFieldValue[];
}

// 枚举字段与值的组合接口
export interface EnumFieldWithType {
  type: EnumFieldType;
  values: EnumFieldValue[];
}

// 字典类型
export interface DictionaryType {
  id: string;
  name: string;
  code: string;
  description?: string;
  is_active: boolean;
  field_count?: number;
  created_at: string;
  updated_at: string;
}

// 字典字段
export interface DictionaryField {
  id: string;
  type_id: string;
  field_name: string;
  field_label: string;
  field_type: string;
  is_required: boolean;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// 字典选项
export interface DictionaryOption {
  value: string;
  label: string;
  disabled?: boolean;
  isActive?: boolean;
  code?: string;
  sort_order?: number;
  color?: string;
  icon?: string;
}

// 字典类型信息 - 用于描述字典类型本身（不是字典值）
export interface DictionaryTypeInfo {
  id: string;
  name: string;
  code: string;
  description?: string;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

// 系统字典值 - 与asset.ts中的SystemDictionary保持一致
// 重新导出asset.ts中的类型，避免重复定义
export type { SystemDictionary } from './asset';

// 字典服务响应类型
export interface DictionaryServiceResult {
  success: boolean;
  data?: DictionaryOption[]; // 主要用于字典选项
  error?: string;
  message?: string;
  source?: 'api' | 'fallback' | 'cache';
  metadata?: {
    totalItems?: number;
    activeItems?: number;
    lastUpdated?: string;
  };
}

// 字典查询参数
export interface DictionaryQueryParams {
  type_id?: string;
  is_active?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}
