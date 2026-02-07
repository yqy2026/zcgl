import type { AssetSearchParams } from '@/types/asset';

export interface ExportOptions {
  format: 'xlsx' | 'csv';
  includeHeaders: boolean;
  selectedFields: string[];
  filters?: AssetSearchParams;
}

export interface ExportFormValues {
  format?: 'xlsx' | 'csv';
  includeHeaders?: boolean;
  selectedFields?: string[];
}

export interface ExportFieldOption {
  key: string;
  label: string;
  required?: boolean;
}

// 导出任务字段（与后端接口保持一致）
export interface ExportTaskWithApiFields {
  id: string;
  status: 'pending' | 'running' | 'processing' | 'completed' | 'failed';
  progress: number;
  download_url?: string;
  filename?: string;
  total_records?: number;
  file_size?: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export const AVAILABLE_EXPORT_FIELDS: ExportFieldOption[] = [
  { key: 'property_name', label: '物业名称', required: true },
  { key: 'ownership_entity', label: '权属方', required: true },
  { key: 'management_entity', label: '经营管理方' },
  { key: 'address', label: '所在地址', required: true },
  { key: 'land_area', label: '土地面积' },
  { key: 'actual_property_area', label: '实际房产面积' },
  { key: 'rentable_area', label: '可出租面积' },
  { key: 'rented_area', label: '已出租面积' },
  { key: 'unrented_area', label: '未出租面积' },
  { key: 'non_commercial_area', label: '非经营物业面积' },
  { key: 'ownership_status', label: '确权状态', required: true },
  { key: 'property_nature', label: '物业性质', required: true },
  { key: 'usage_status', label: '使用状态', required: true },
  { key: 'certificated_usage', label: '证载用途' },
  { key: 'actual_usage', label: '实际用途' },
  { key: 'business_category', label: '业态类别' },
  { key: 'business_model', label: '接收模式' },
  { key: 'occupancy_rate', label: '出租率' },
  { key: 'tenant_name', label: '租户名称' },
  { key: 'lease_contract_number', label: '租赁合同编号' },
  { key: 'contract_start_date', label: '合同开始日期' },
  { key: 'contract_end_date', label: '合同结束日期' },
  { key: 'is_litigated', label: '是否涉诉' },
  { key: 'include_in_occupancy_rate', label: '是否计入出租率' },
  { key: 'project_name', label: '项目名称' },
  { key: 'operation_agreement_start_date', label: '接收协议开始日期' },
  { key: 'operation_agreement_end_date', label: '接收协议结束日期' },
  { key: 'terminal_contract_files', label: '终端合同文件' },
  { key: 'notes', label: '其他备注' },
  { key: 'created_at', label: '创建时间' },
  { key: 'updated_at', label: '更新时间' },
];
