/**
 * 项目类型定义
 */

import type { Asset } from '@/types/asset';

export interface ProjectPartyRelation {
  id?: string;
  project_id?: string;
  party_id: string;
  party_name?: string;
  relation_type: string;
  is_primary?: boolean;
  is_active?: boolean;
}

export interface Project {
  id: string;
  project_name: string;
  project_code: string;
  status: string;
  manager_party_id?: string;
  data_status: string;
  review_status: string;
  review_by?: string;
  reviewed_at?: string;
  review_reason?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  asset_count?: number;
  party_relations?: ProjectPartyRelation[];
}

export interface ProjectCreate {
  project_name: string;
  project_code?: string;
  status?: string;
  manager_party_id?: string;
  party_relations?: ProjectPartyRelation[];
}

export interface ProjectUpdate {
  project_name?: string;
  project_code?: string;
  status?: string;
  manager_party_id?: string;
  data_status?: string;
  party_relations?: ProjectPartyRelation[];
}

export type ProjectResponse = Project;

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ProjectDeleteResponse {
  message: string;
  deleted_id: string;
  affected_assets?: number;
}

export interface ProjectSearchRequest {
  keyword?: string;
  status?: string;
  owner_party_id?: string;
  page?: number;
  page_size?: number;
}

export interface ProjectStatisticsResponse {
  total_projects: number;
  active_projects: number;
}

export interface ProjectAssetSummary {
  total_assets: number;
  total_rentable_area: number;
  total_rented_area: number;
  occupancy_rate: number;
}

export interface ProjectActiveAssetsResponse {
  items: Asset[];
  total: number;
  summary: ProjectAssetSummary;
}

export type ProjectRevenueMode = 'lease' | 'agency';
export type ProjectContractRelationKind = 'lease_sublease' | 'agency_operation';

export interface ProjectContractRelation {
  contract_relation_id: string;
  project_id: string;
  display_name: string;
  revenue_mode: ProjectRevenueMode;
  relation_kind: ProjectContractRelationKind;
  owner_party_id: string;
  operator_party_id: string;
  asset_ids: string[];
  primary_contract_ids: string[];
  terminal_contract_ids: string[];
  derived_status: string;
  risk_tags?: string[] | null;
}

export interface ProjectContractRelationsResponse {
  items: ProjectContractRelation[];
  total: number;
}

export interface ProjectLedgerSummaryResponse {
  receivable_amount: string;
  payable_amount: string;
  received_amount: string;
  paid_amount: string;
  overdue_amount: string;
  service_fee_receivable: string;
  service_fee_received: string;
}

export interface ProjectRiskItem {
  risk_id: string;
  risk_type: string;
  severity: string;
  message: string;
  contract_relation_id?: string | null;
  display_name?: string | null;
}

export interface ProjectRisksResponse {
  items: ProjectRiskItem[];
  total: number;
}

export interface ProjectTenantSummaryItem {
  party_id: string;
  party_name: string;
  group_relation_type: string;
  contract_count: number;
}

export interface ProjectTenantSummaryResponse {
  items: ProjectTenantSummaryItem[];
  total: number;
}

export interface ProjectAnalysisModeSummary {
  relation_kind: ProjectContractRelationKind;
  label: string;
  contract_relation_count: number;
  asset_count: number;
  primary_contract_count: number;
  terminal_contract_count: number;
  customer_count: number | null;
  customer_contract_count: number | null;
  receivable_amount: string;
  payable_amount: string;
  received_amount: string;
  paid_amount: string;
  overdue_amount: string;
  risk_count: number;
}

export interface ProjectMonthlyTrendItem {
  period: string;
  receivable_amount: string;
  payable_amount: string;
  received_amount: string;
  paid_amount: string;
  overdue_amount: string;
}

export interface ProjectAnalyticsResponse {
  asset_summary: ProjectAssetSummary;
  contract_relation_count: number;
  tenant_count: number | null;
  customer_contract_count: number | null;
  customer_metrics_suppression_reason?: string | null;
  risk_count: number;
  high_risk_count: number;
  receivable_amount: string;
  payable_amount: string;
  received_amount: string;
  paid_amount: string;
  overdue_amount: string;
  service_fee_receivable: string;
  service_fee_received: string;
  mode_summaries: ProjectAnalysisModeSummary[];
  monthly_trends: ProjectMonthlyTrendItem[];
}

// 项目搜索参数类型
export interface ProjectSearchParams {
  keyword?: string;
  status?: string;
  owner_party_id?: string;
  page?: number;
  page_size?: number;
}

// 项目选项类型（用于下拉选择）
export interface ProjectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

// 项目统计类型
export interface ProjectStats {
  total: number;
  active: number;
}

// 项目下拉选项类型
export interface ProjectDropdownOption {
  id: string;
  project_name: string;
  project_code: string;
  status?: string;
}
