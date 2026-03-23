export type RevenueMode = 'LEASE' | 'AGENCY';

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
  contract_direction: string;
  group_relation_type: string;
  lessor_party_id: string;
  lessee_party_id: string;
  effective_from: string;
  effective_to?: string | null;
  status: string;
  review_status: string;
}

export interface ContractGroupListItem {
  contract_group_id: string;
  group_code: string;
  revenue_mode: RevenueMode;
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
  settlement_rule: SettlementRule;
  revenue_attribution_rule?: Record<string, unknown> | null;
  revenue_share_rule?: Record<string, unknown> | null;
  risk_tags?: string[] | null;
  predecessor_group_id?: string | null;
  version: number;
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
  revenue_mode: RevenueMode;
  operator_party_id: string;
  owner_party_id: string;
  effective_from: string;
  effective_to?: string;
  settlement_rule: SettlementRule;
  revenue_attribution_rule?: Record<string, unknown>;
  revenue_share_rule?: Record<string, unknown>;
  risk_tags?: string[];
  predecessor_group_id?: string;
  asset_ids: string[];
}

export interface ContractGroupUpdate {
  effective_to?: string | null;
  settlement_rule?: SettlementRule;
  revenue_attribution_rule?: Record<string, unknown> | null;
  revenue_share_rule?: Record<string, unknown> | null;
  risk_tags?: string[] | null;
  asset_ids?: string[];
}
