/** Party domain types (Phase 3). */

export type PartyType = 'organization' | 'legal_entity' | 'individual';
export type PartyReviewStatus = 'draft' | 'pending' | 'approved' | 'reversed';

export interface Party {
  id: string;
  party_type: PartyType;
  name: string;
  code: string;
  external_ref?: string | null;
  status: string;
  metadata?: Record<string, unknown>;
  review_status?: PartyReviewStatus | null;
  review_by?: string | null;
  reviewed_at?: string | null;
  review_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export type CustomerType = 'internal' | 'external';
export type CustomerSubjectNature = 'enterprise' | 'individual';
export type CustomerContractRole =
  | 'upstream_lease'
  | 'downstream_sublease'
  | 'entrusted_operation';
export type CustomerRiskTagSource = 'manual' | 'rule';

export interface CustomerRiskTag {
  tag: string;
  source: CustomerRiskTagSource;
  updated_at?: string | null;
}

export interface CustomerContractSummary {
  contract_id: string;
  contract_number: string;
  group_code: string;
  revenue_mode: string;
  group_relation_type: string;
  status: string;
  effective_from?: string | null;
  effective_to?: string | null;
}

export interface CustomerProfile {
  customer_party_id: string;
  customer_name: string;
  customer_type: CustomerType;
  subject_nature: CustomerSubjectNature;
  binding_type: 'owner' | 'manager' | 'all';
  contract_role: CustomerContractRole;
  contact_name?: string | null;
  contact_phone?: string | null;
  identifier_type?: string | null;
  unified_identifier?: string | null;
  address?: string | null;
  status: string;
  historical_contract_count: number;
  risk_tags: string[];
  risk_tag_items: CustomerRiskTag[];
  payment_term_preference?: string | null;
  contracts: CustomerContractSummary[];
}

export interface PartyListParams {
  party_type?: PartyType;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface FrontendPartyHierarchyEdge {
  id: string;
  parent_party_id: string;
  child_party_id: string;
}

export interface PartyContact {
  id: string;
  party_id: string;
  contact_name: string;
  contact_phone?: string | null;
  contact_email?: string | null;
  notes?: string | null;
  is_primary: boolean;
  created_at?: string;
  updated_at?: string;
}

export type CertificatePartyRelationRole = 'owner' | 'co_owner' | 'issuer' | 'custodian';

export interface CertificatePartyRelation {
  id: string;
  certificate_id: string;
  party_id: string;
  relation_role: CertificatePartyRelationRole;
  is_primary: boolean;
  share_ratio?: number | null;
  valid_from?: string | null;
  valid_to?: string | null;
  party?: Party;
}
