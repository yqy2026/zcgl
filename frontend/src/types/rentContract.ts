/**
 * 租金台账相关的TypeScript类型定义
 */

import { Asset } from './asset';
import { Ownership } from './ownership';

// 基础类型
export interface RentTerm {
  id: string;
  contract_id: string;
  start_date: string;
  end_date: string;
  monthly_rent: number;
  rent_description?: string;
  management_fee: number;
  other_fees: number;
  total_monthly_amount: number;
  created_at: string;
  updated_at: string;
}

export interface RentContract {
  id: string;
  contract_number: string;
  asset_id: string;
  ownership_id: string;
  tenant_name: string;
  tenant_contact?: string;
  tenant_phone?: string;
  tenant_address?: string;
  sign_date: string;
  start_date: string;
  end_date: string;
  total_deposit: number;
  monthly_rent_base?: number;
  contract_status: string;
  payment_terms?: string;
  contract_notes?: string;
  data_status: string;
  version: number;
  created_at: string;
  updated_at: string;
  tenant_id?: string;
  rent_terms: RentTerm[];
  // 关联数据
  asset?: Asset;
  ownership?: Ownership;
}

export interface RentLedger {
  id: string;
  contract_id: string;
  asset_id: string;
  ownership_id: string;
  year_month: string;
  due_date: string;
  due_amount: number;
  paid_amount: number;
  overdue_amount: number;
  payment_status: '未支付' | '部分支付' | '已支付' | '逾期';
  payment_date?: string;
  payment_method?: string;
  payment_reference?: string;
  late_fee: number;
  late_fee_days: number;
  notes?: string;
  data_status: string;
  version: number;
  created_at: string;
  updated_at: string;
  // 关联数据
  contract?: RentContract;
  asset?: Asset;
  ownership?: Ownership;
}

export interface RentContractHistory {
  id: string;
  contract_id: string;
  change_type: string;
  change_description?: string;
  old_data?: any;
  new_data?: any;
  operator?: string;
  operator_id?: string;
  created_at: string;
}

// 请求类型
export interface RentContractCreate {
  contract_number?: string;
  asset_id: string;
  ownership_id: string;
  tenant_name: string;
  tenant_contact?: string;
  tenant_phone?: string;
  tenant_address?: string;
  sign_date: string;
  start_date: string;
  end_date: string;
  total_deposit?: number;
  monthly_rent_base?: number;
  contract_status?: string;
  payment_terms?: string;
  contract_notes?: string;
  rent_terms: RentTermCreate[];
}

export interface RentContractUpdate {
  contract_number?: string;
  asset_id?: string;
  ownership_id?: string;
  tenant_name?: string;
  tenant_contact?: string;
  tenant_phone?: string;
  tenant_address?: string;
  sign_date?: string;
  start_date?: string;
  end_date?: string;
  total_deposit?: number;
  monthly_rent_base?: number;
  contract_status?: string;
  payment_terms?: string;
  contract_notes?: string;
  rent_terms?: RentTermUpdate[];
}

export interface RentTermCreate {
  start_date: string;
  end_date: string;
  monthly_rent: number;
  rent_description?: string;
  management_fee?: number;
  other_fees?: number;
  total_monthly_amount?: number;
}

export interface RentTermUpdate {
  start_date?: string;
  end_date?: string;
  monthly_rent?: number;
  rent_description?: string;
  management_fee?: number;
  other_fees?: number;
  total_monthly_amount?: number;
}

export interface RentLedgerCreate {
  contract_id: string;
  asset_id: string;
  ownership_id: string;
  year_month: string;
  due_date: string;
  due_amount: number;
  paid_amount?: number;
  overdue_amount?: number;
  payment_status?: '未支付' | '部分支付' | '已支付' | '逾期';
  payment_date?: string;
  payment_method?: string;
  payment_reference?: string;
  late_fee?: number;
  late_fee_days?: number;
  notes?: string;
}

export interface RentLedgerUpdate {
  paid_amount?: number;
  payment_status?: '未支付' | '部分支付' | '已支付' | '逾期';
  payment_date?: string;
  payment_method?: string;
  payment_reference?: string;
  late_fee?: number;
  late_fee_days?: number;
  notes?: string;
}

export interface RentLedgerBatchUpdate {
  ledger_ids: string[];
  payment_status: '未支付' | '部分支付' | '已支付' | '逾期';
  payment_date?: string;
  payment_method?: string;
  payment_reference?: string;
  notes?: string;
}

export interface GenerateLedgerRequest {
  contract_id: string;
  start_year_month?: string;
  end_year_month?: string;
}

// 统计相关类型
export interface OwnershipRentStatistics {
  ownership_id: string;
  ownership_name: string;
  ownership_short_name: string;
  contract_count: number;
  total_due_amount: number;
  total_paid_amount: number;
  total_overdue_amount: number;
  payment_rate: number;
}

export interface AssetRentStatistics {
  asset_id: string;
  asset_name: string;
  asset_address: string;
  contract_count: number;
  total_due_amount: number;
  total_paid_amount: number;
  total_overdue_amount: number;
  payment_rate: number;
}

export interface MonthlyRentStatistics {
  year_month: string;
  total_contracts: number;
  total_due_amount: number;
  total_paid_amount: number;
  total_overdue_amount: number;
  payment_rate: number;
}

export interface RentStatisticsQuery {
  start_date?: string;
  end_date?: string;
  ownership_ids?: string[];
  asset_ids?: string[];
}

// 查询参数类型
export interface RentContractQueryParams {
  page?: number;
  limit?: number;
  contract_number?: string;
  tenant_name?: string;
  asset_id?: string;
  ownership_id?: string;
  contract_status?: string;
  start_date?: string;
  end_date?: string;
}

export interface RentLedgerQueryParams {
  page?: number;
  limit?: number;
  contract_id?: string;
  asset_id?: string;
  ownership_id?: string;
  year_month?: string;
  payment_status?: string;
  start_date?: string;
  end_date?: string;
}


// 分页响应类型
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface RentContractListResponse extends PaginatedResponse<RentContract> {}
export interface RentLedgerListResponse extends PaginatedResponse<RentLedger> {}

// 统计响应类型
export interface RentStatisticsOverview {
  total_due: number;
  total_paid: number;
  total_overdue: number;
  total_records: number;
  payment_rate: number;
  status_breakdown: Array<{
    status: string;
    count: number;
    due_amount: number;
    paid_amount: number;
  }>;
  monthly_breakdown: Array<{
    year_month: string;
    due_amount: number;
    paid_amount: number;
    overdue_amount: number;
  }>;
}

// 表单数据类型
export interface RentContractFormData {
  basicInfo: {
    contract_number?: string;
    asset_id: string;
    ownership_id: string;
    tenant_name: string;
    tenant_contact?: string;
    tenant_phone?: string;
    tenant_address?: string;
    sign_date: string;
    start_date: string;
    end_date: string;
    total_deposit?: number;
    contract_status?: string;
    payment_terms?: string;
    contract_notes?: string;
  };
  rentTerms: RentTermCreate[];
}

export interface RentLedgerFormData {
  payment_status: '未支付' | '部分支付' | '已支付' | '逾期';
  paid_amount?: number;
  payment_date?: string;
  payment_method?: string;
  payment_reference?: string;
  late_fee?: number;
  late_fee_days?: number;
  notes?: string;
}

// 选项类型
export interface PaymentStatusOption {
  value: '未支付' | '部分支付' | '已支付' | '逾期';
  label: string;
  color?: string;
}

export interface ContractStatusOption {
  value: string;
  label: string;
  color?: string;
}

export interface PaymentMethodOption {
  value: string;
  label: string;
}

// 搜索和筛选类型
export interface RentContractSearchFilters {
  keyword?: string;
  asset_id?: string;
  ownership_id?: string;
  contract_status?: string;
  date_range?: [string, string];
}

export interface RentLedgerSearchFilters {
  keyword?: string;
  asset_id?: string;
  ownership_id?: string;
  contract_id?: string;
  payment_status?: string;
  year_month?: string;
  date_range?: [string, string];
}

// 导出相关类型
export interface ExportOptions {
  format: 'excel' | 'csv';
  includeHeaders: boolean;
  dateRange?: [string, string];
  filters?: Record<string, any>;
}

export interface RentLedgerExportData {
  year_month: string;
  contract_number: string;
  tenant_name: string;
  asset_name: string;
  ownership_name: string;
  due_amount: number;
  paid_amount: number;
  overdue_amount: number;
  payment_status: string;
  payment_date?: string;
  payment_method?: string;
  notes?: string;
}

// UI状态类型
export interface RentContractPageState {
  loading: boolean;
  contracts: RentContract[];
  pagination: {
    current: number;
    pageSize: number;
    total: number;
    pages?: number;
  };
  filters: RentContractSearchFilters;
  selectedContract?: RentContract;
  showModal: boolean;
  modalMode: 'create' | 'edit' | 'view';
}

export interface RentLedgerPageState {
  loading: boolean;
  ledgers: RentLedger[];
  pagination: {
    current: number;
    pageSize: number;
    total: number;
  };
  filters: RentLedgerSearchFilters;
  selectedLedgers: RentLedger[];
  showBatchModal: boolean;
  showGenerateModal: boolean;
  statistics?: RentStatisticsOverview;
}

// 错误类型
export interface RentContractError {
  field?: string;
  message: string;
  code?: string;
}

// 事件处理类型
export interface RentContractEventHandlers {
  onCreate: (data: RentContractCreate) => Promise<void>;
  onUpdate: (id: string, data: RentContractUpdate) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onView: (contract: RentContract) => void;
  onGenerateLedger: (contractId: string) => Promise<void>;
}

export interface RentLedgerEventHandlers {
  onUpdate: (id: string, data: RentLedgerUpdate) => Promise<void>;
  onBatchUpdate: (data: RentLedgerBatchUpdate) => Promise<void>;
  onExport: (options: ExportOptions) => Promise<void>;
  onGenerateMonthly: (request: GenerateLedgerRequest) => Promise<void>;
}