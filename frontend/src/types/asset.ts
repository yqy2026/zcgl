// 优化后的资产类型定义
export interface Asset {
  id: string
  // 基本信息 - 按照权属方、权属类别、项目名称、物业名称、物业地址顺序
  ownership_entity: string
  ownership_category?: string
  project_name?: string
  property_name: string
  address: string
  ownership_status: OwnershipStatus
  property_nature: PropertyNature
  usage_status: UsageStatus
  business_category?: string

  // 面积相关字段 - 使用Decimal精度类型以匹配后端
  land_area?: number // 前端使用number，传输时转换为Decimal字符串
  actual_property_area?: number
  rentable_area?: number
  rented_area?: number
  unrented_area?: number  // 后端纯计算字段，不存储
  non_commercial_area?: number
  occupancy_rate?: number  // 后端纯计算字段，0-100，不存储
  include_in_occupancy_rate?: boolean

  // 用途相关字段
  certificated_usage?: string
  actual_usage?: string

  // 租户相关字段
  tenant_name?: string
  tenant_type?: TenantType
  // tenant_contact 字段已删除

  // 合同相关字段
  lease_contract_number?: string
  contract_start_date?: string
  contract_end_date?: string
  monthly_rent?: number  // 金额字段，使用高精度number
  deposit?: number       // 金额字段，使用高精度number
  is_sublease?: boolean
  sublease_notes?: string

  // 管理相关字段
  manager_name?: string
  business_model?: BusinessModel  // 接收模式
  operation_status?: OperationStatus

  // 财务相关字段已删除
  // annual_income, annual_expense, net_income 字段已删除
  
  // 接收相关字段
  operation_agreement_start_date?: string
  operation_agreement_end_date?: string
  operation_agreement_attachments?: string

  // 终端合同相关字段
  terminal_contract_files?: string

  // 项目相关字段
  project_id?: string

  // 向后兼容字段
  wuyang_project_name?: string  // 用于向后兼容
  ownership_id?: string

  // 项目相关字段已移至基本信息部分
  
  // 系统字段
  data_status?: DataStatus
  created_by?: string
  updated_by?: string
  version?: number
  tags?: string
  
  // 审核相关字段已删除
  // last_audit_date, audit_status, auditor 字段已删除
  audit_notes?: string
  
  // 其他字段
  is_litigated?: boolean  // 优化为boolean类型
  notes?: string
  
  // 时间戳
  created_at?: string
  updated_at?: string
  
  // 多租户支持
  tenant_id?: string
}

// 枚举定义
export enum OwnershipStatus {
  CONFIRMED = '已确权',
  UNCONFIRMED = '未确权',
  PARTIAL = '部分确权',
  CANNOT_CONFIRM = '无法确认业权'
}

export enum PropertyNature {
  COMMERCIAL = '经营性',
  NON_COMMERCIAL = '非经营性',
  COMMERCIAL_EXTERNAL = '经营-外部',
  COMMERCIAL_INTERNAL = '经营-内部',
  COMMERCIAL_LEASE = '经营-租赁',
  NON_COMMERCIAL_PUBLIC = '非经营类-公配',
  NON_COMMERCIAL_OTHER = '非经营类-其他',
  COMMERCIAL_CLASS = '经营类',
  NON_COMMERCIAL_CLASS = '非经营类',
  COMMERCIAL_SUPPORTING = '经营-配套',
  NON_COMMERCIAL_SUPPORTING = '非经营-配套',
  COMMERCIAL_SUPPORTING_TOWN = '经营-配套镇',
  NON_COMMERCIAL_SUPPORTING_TOWN = '非经营-配套镇',
  COMMERCIAL_DISPOSAL = '经营-处置类',
  NON_COMMERCIAL_DISPOSAL = '非经营-处置类',
  NON_COMMERCIAL_PUBLIC_HOUSING = '非经营-公配房',
  NON_COMMERCIAL_SUPPORTING_HOUSING = '非经营类-配套'
}

export enum UsageStatus {
  RENTED = '出租',
  VACANT = '空置',
  SELF_USED = '自用',
  PUBLIC_HOUSING = '公房',
  OTHER = '其他',
  SUBLEASE = '转租',
  PUBLIC_FACILITY = '公配',
  VACANT_PLANNING = '空置规划',
  VACANT_RESERVED = '空置预留',
  SUPPORTING_FACILITY = '配套',
  VACANT_SUPPORTING = '空置配套',
  VACANT_SUPPORTING_SHORT = '空置配',
  PENDING_DISPOSAL = '待处置',
  PENDING_HANDOVER = '待移交',
  VACANT_DISPOSAL = '闲置'
}

export enum TenantType {
  INDIVIDUAL = '个人',
  ENTERPRISE = '企业',
  GOVERNMENT = '政府机构',
  OTHER = '其他'
}


export enum BusinessModel {
  LEASE_SUBLEASE = '承租转租',
  ENTRUSTED_OPERATION = '委托经营',
  SELF_OPERATION = '自营',
  OTHER = '其他'
}  // 接收模式枚举

export enum OperationStatus {
  NORMAL = '正常经营',
  SUSPENDED = '停业整顿',
  RENOVATING = '装修中',
  SEEKING_TENANT = '待招租'
}

export enum DataStatus {
  NORMAL = '正常',
  DELETED = '已删除',
  ARCHIVED = '已归档'
}

export enum AuditStatus {
  PENDING = '待审核',
  APPROVED = '已审核',
  REJECTED = '审核不通过'
}

export enum ContractStatus {
  ACTIVE = '生效中',
  EXPIRED = '已过期',
  TERMINATED = '已终止',
  PENDING = '待生效',
  SUSPENDED = '暂停'
}

export enum BusinessCategory {
  COMMERCIAL = '商业',
  OFFICE = '办公',
  RESIDENTIAL = '住宅',
  WAREHOUSE = '仓储',
  INDUSTRIAL = '工业',
  OTHER = '其他'
}

// 系统数据字典接口
export interface SystemDictionary {
  id: string
  dict_type: string
  dict_code: string
  dict_label: string
  dict_value: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// 自定义字段接口
export interface AssetCustomField {
  id: string
  asset_id: string
  field_name: string
  field_type: 'text' | 'number' | 'date' | 'boolean'
  field_value?: string
  created_at: string
  updated_at: string
}

export interface CustomFieldValue {
  field_name: string
  field_value: string | number | boolean | null
  field_type?: 'text' | 'number' | 'date' | 'boolean'
}

// 表单数据接口
export interface AssetFormData extends Omit<Asset, 'id' | 'created_at' | 'updated_at' | 'unrented_area' | 'occupancy_rate' | 'net_income'> {}

// API响应接口
export interface AssetListResponse {
  items: Asset[]
  total: number
  page: number
  limit: number
  pages: number
}

export interface AssetSummary {
  total: number
  rented: number
  vacant: number
  avgOccupancyRate: number
  totalArea: number
  rentableArea: number
  rentedArea: number
  totalIncome: number
  totalExpense: number
  netIncome: number
}

// 搜索参数
export interface AssetSearchParams {
  page?: number
  limit?: number
  search?: string
  search_keyword?: string  // 添加搜索关键字字段
  ownership_status?: OwnershipStatus
  usage_status?: UsageStatus
  property_nature?: PropertyNature
  business_category?: string  // 改为string类型以匹配使用
  tenant_type?: TenantType
  contract_status?: ContractStatus
  audit_status?: AuditStatus
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  // 面积范围筛选
  min_area?: number
  max_area?: number
  // 租金范围筛选
  min_rent?: number
  max_rent?: number
  // 日期范围筛选
  start_date?: string
  end_date?: string
  // 新增字段以匹配AnalyticsFilters的使用
  operation_status?: string
  ownership_entity?: string
  // 添加索引签名以支持动态字段访问
  [key: string]: any
}

// 创建资产请求
export interface AssetCreateRequest extends Omit<Asset, 'id' | 'created_at' | 'updated_at' | 'unrented_area' | 'occupancy_rate' | 'net_income'> {}

// 更新资产请求
export interface AssetUpdateRequest extends Partial<AssetCreateRequest> {}

// 资产历史记录 - 增强版
export interface AssetHistory {
  id: string
  asset_id: string
  operation_type: string
  change_type?: string  // 添加change_type字段
  field_name?: string
  old_value?: string
  new_value?: string
  operator?: string
  operation_time: string
  description?: string
  changed_fields?: string[]  // 添加changed_fields字段
  // 新增审计字段
  change_reason?: string
  ip_address?: string
  user_agent?: string
  session_id?: string
}

// 资产文档
export interface AssetDocument {
  id: string
  asset_id: string
  document_name: string
  document_type: string
  file_path?: string
  file_size?: number
  mime_type?: string
  upload_time: string
  uploader?: string
  description?: string
}

// 数据验证规则
export interface FieldValidationRule {
  required?: boolean
  min?: number
  max?: number
  pattern?: string
  message?: string
}

// 数值精度处理工具 - 处理前后端Decimal/number类型转换
export const DecimalUtils = {
  // 将后端Decimal字符串转换为前端number，处理精度
  parseDecimal: (decimalStr: string | number | null | undefined): number | undefined => {
    if (decimalStr === null || decimalStr === undefined || decimalStr === '') {
      return undefined
    }

    // 如果已经是number，直接返回
    if (typeof decimalStr === 'number') {
      return decimalStr
    }

    // 转换字符串为number，处理精度
    const num = parseFloat(decimalStr.toString())
    return isNaN(num) ? undefined : num
  },

  // 将前端number转换为后端Decimal字符串
  formatDecimal: (num: number | null | undefined): string | undefined => {
    if (num === null || num === undefined || isNaN(num)) {
      return undefined
    }

    // 保持精度，使用toFixed避免精度丢失
    return num.toString()
  },

  // 安全的数值运算，避免浮点精度问题
  safeAdd: (a: number | undefined, b: number | undefined): number => {
    const numA = a || 0
    const numB = b || 0
    return Math.round((numA + numB) * 100) / 100
  },

  safeSubtract: (a: number | undefined, b: number | undefined): number => {
    const numA = a || 0
    const numB = b || 0
    return Math.round((numA - numB) * 100) / 100
  },

  safeMultiply: (a: number | undefined, b: number | undefined): number => {
    const numA = a || 0
    const numB = b || 0
    return Math.round((numA * numB) * 100) / 100
  },

  safeDivide: (a: number | undefined, b: number | undefined): number => {
    const numA = a || 0
    const numB = b || 0
    if (numB === 0) return 0
    return Math.round((numA / numB) * 100) / 100
  }
}

export interface AssetValidationRules {
  [fieldName: string]: FieldValidationRule
}

// 字段配置
export interface FieldConfig {
  label: string
  type: 'input' | 'textarea' | 'select' | 'number' | 'date' | 'switch' | 'upload' | 'tags'
  required?: boolean
  readonly?: boolean
  placeholder?: string
  options?: Array<{ label: string; value: string | number | boolean }>
  min?: number
  max?: number
  precision?: number
  maxLength?: number
  tooltip?: string
  defaultValue?: any
}

export interface AssetFieldGroups {
  [groupName: string]: {
    label: string
    fields: { [fieldName: string]: FieldConfig }
  }
}

// 导出/导入相关
export interface ExportOptions {
  format: 'excel' | 'csv' | 'pdf'
  fields?: string[]
  filters?: AssetSearchParams
  includeHistory?: boolean
  includeDocuments?: boolean
}

export interface ImportResult {
  success: number
  failed: number
  errors: Array<{
    row: number
    field: string
    message: string
  }>
}

// 统计分析相关
export interface AssetStatistics {
  overview: AssetSummary
  byOwnershipStatus: Record<string, number>
  byUsageStatus: Record<string, number>
  byPropertyNature: Record<string, number>
  byBusinessCategory: Record<string, number>
  occupancyTrend: Array<{
    date: string
    rate: number
  }>
  financialSummary: {
    totalIncome: number
    totalExpense: number
    netIncome: number
    averageRent: number
  }
}

// 批量操作
export interface BatchOperation {
  action: 'update' | 'delete' | 'export' | 'audit'
  assetIds: string[]
  data?: Partial<Asset>
  reason?: string
}

export interface BatchOperationResult {
  success: number
  failed: number
  errors: Array<{
    assetId: string
    message: string
  }>
}