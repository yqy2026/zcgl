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
  
  // 面积相关字段 - 使用number类型，前端处理精度
  land_area?: number
  actual_property_area?: number
  rentable_area?: number
  rented_area?: number
  unrented_area?: number  // 自动计算字段
  non_commercial_area?: number
  occupancy_rate?: number  // 自动计算字段，0-100
  include_in_occupancy_rate?: boolean
  
  // 用途相关字段
  certificated_usage?: string
  actual_usage?: string
  
  // 租户相关字段
  tenant_name?: string
  tenant_contact?: string
  tenant_type?: TenantType
  
  // 合同相关字段
  lease_contract_number?: string
  contract_start_date?: string
  contract_end_date?: string
  contract_status?: ContractStatus
  monthly_rent?: number  // 金额字段
  deposit?: number       // 金额字段
  is_sublease?: boolean
  sublease_notes?: string
  
  // 管理相关字段
  manager_name?: string
  business_model?: BusinessModel  // 接收模式
  operation_status?: OperationStatus
  
  // 财务相关字段
  annual_income?: number   // 金额字段
  annual_expense?: number  // 金额字段
  net_income?: number      // 自动计算字段
  
  // 接收相关字段
  operation_agreement_start_date?: string
  operation_agreement_end_date?: string
  operation_agreement_attachments?: string
  
  // 项目相关字段已移至基本信息部分
  
  // 系统字段
  data_status?: DataStatus
  created_by?: string
  updated_by?: string
  version?: number
  tags?: string
  
  // 审核相关字段
  last_audit_date?: string
  audit_status?: AuditStatus
  auditor?: string
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
  PARTIAL = '部分确权'
}

export enum PropertyNature {
  COMMERCIAL = '经营性',
  NON_COMMERCIAL = '非经营性'
}

export enum UsageStatus {
  RENTED = '出租',
  VACANT = '空置',
  SELF_USED = '自用',
  PUBLIC_HOUSING = '公房',
  PENDING_TRANSFER = '待移交',
  PENDING_DISPOSAL = '待处置',
  OTHER = '其他'
}

export enum TenantType {
  INDIVIDUAL = '个人',
  ENTERPRISE = '企业',
  GOVERNMENT = '政府机构',
  OTHER = '其他'
}

export enum ContractStatus {
  ACTIVE = '生效中',
  EXPIRED = '已到期',
  TERMINATED = '已终止',
  PENDING = '待签署'
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
  ownership_status?: OwnershipStatus
  usage_status?: UsageStatus
  property_nature?: PropertyNature
  business_category?: BusinessCategory
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
  field_name?: string
  old_value?: string
  new_value?: string
  operator?: string
  operation_time: string
  description?: string
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