export type RevenueMode = 'lease' | 'agency';
export type ContractDirection = 'LESSOR' | 'LESSEE';
export type GroupRelationType = 'UPSTREAM' | 'DOWNSTREAM' | 'ENTRUSTED' | 'DIRECT_LEASE';
export type ContractLifecycleStatus = 'DRAFT' | 'ACTIVE' | 'TERMINATED';

export interface LeaseDetailCreate {
  total_deposit?: string | number;
  rent_amount: string | number;
  monthly_rent_base?: string | number | null;
  payment_cycle?: string;
  payment_terms?: string | null;
  tenant_name?: string | null;
  tenant_contact?: string | null;
  tenant_phone?: string | null;
  tenant_address?: string | null;
  tenant_usage?: string | null;
  owner_name?: string | null;
  owner_contact?: string | null;
  owner_phone?: string | null;
}

export interface AgencyDetailCreate {
  service_fee_ratio: string | number;
  fee_calculation_base?: string;
  agency_scope?: string | null;
}

export interface SettlementRule {
  version: string;
  cycle: string;
  settlement_mode: string;
  amount_rule: Record<string, unknown>;
  payment_rule: Record<string, unknown>;
}

export interface ContractGroupSummaryContract {
  contract_id: string;
  contract_number: string;
  contract_direction: ContractDirection | string;
  group_relation_type: GroupRelationType | string;
  lessor_party_id: string;
  lessee_party_id: string;
  lessor_name_snapshot?: string | null;
  lessee_name_snapshot?: string | null;
  effective_from: string;
  effective_to?: string | null;
  status: ContractLifecycleStatus | string;
}

export interface ContractCreate {
  contract_group_id: string;
  contract_number: string;
  contract_direction: ContractDirection;
  group_relation_type: GroupRelationType;
  lessor_party_id: string;
  lessee_party_id: string;
  sign_date?: string | null;
  effective_from: string;
  effective_to?: string | null;
  currency_code?: string;
  tax_rate?: string | number | null;
  is_tax_included?: boolean;
  status?: ContractLifecycleStatus;
  contract_notes?: string | null;
  source_session_id?: string | null;
  asset_ids: string[];
  lease_detail?: LeaseDetailCreate | null;
  agency_detail?: AgencyDetailCreate | null;
}

export interface ContractDetail extends ContractGroupSummaryContract {
  contract_group_id: string;
  sign_date?: string | null;
  currency_code: string;
  tax_rate?: string | number | null;
  is_tax_included: boolean;
  contract_notes?: string | null;
  data_status: string;
  created_at: string;
  updated_at: string;
  lease_detail?: LeaseDetailCreate | null;
  agency_detail?: AgencyDetailCreate | null;
}

export interface ContractGroupListItem {
  contract_group_id: string;
  project_id?: string | null;
  project_name?: string | null;
  group_code: string;
  revenue_mode: RevenueMode;
  contract_role_counts?: Partial<Record<GroupRelationType, number>>;
  operator_party_id: string;
  owner_party_id: string;
  effective_from: string;
  effective_to?: string | null;
  derived_status: string;
  data_status: string;
  created_at: string;
  updated_at: string;
}

export interface ContractGroupDetail extends ContractGroupListItem {
  settlement_rule?: SettlementRule | null;
  revenue_attribution_rule?: Record<string, unknown> | null;
  revenue_share_rule?: Record<string, unknown> | null;
  risk_tags?: string[] | null;
  upstream_contract_ids: string[];
  downstream_contract_ids: string[];
  contracts: ContractGroupSummaryContract[];
}

export interface ContractGroupListParams {
  operator_party_id?: string;
  owner_party_id?: string;
  revenue_mode?: RevenueMode;
  offset?: number;
  limit?: number;
}

export interface ContractGroupListResponse {
  items: ContractGroupListItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface ContractGroupCreate {
  project_id: string;
  revenue_mode: RevenueMode;
  operator_party_id: string;
  owner_party_id: string;
  effective_from: string;
  effective_to?: string;
  settlement_rule?: SettlementRule | null;
  revenue_attribution_rule?: Record<string, unknown>;
  revenue_share_rule?: Record<string, unknown>;
  risk_tags?: string[];
  asset_ids: string[];
}

export interface ContractGroupUpdate {
  effective_to?: string | null;
  settlement_rule?: SettlementRule | null;
  revenue_attribution_rule?: Record<string, unknown> | null;
  revenue_share_rule?: Record<string, unknown> | null;
  risk_tags?: string[] | null;
  asset_ids?: string[];
}
