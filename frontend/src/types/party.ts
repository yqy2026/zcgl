/** Party domain types (Phase 3). */

export type PartyType = 'legal_entity' | 'individual';
export type LegalEntityIdentifierType =
  | 'unified_social_credit_code'
  | 'legal_registration_number'
  | 'foreign_registration_number';
export type IndividualIdentifierType = 'national_id' | 'passport';
export type PartyIdentifierType = LegalEntityIdentifierType | IndividualIdentifierType;
export type PartyReviewStatus = 'draft' | 'pending' | 'approved' | 'rejected';
export type PartyBusinessRole = 'owner' | 'operator' | 'terminal_tenant';

export interface Party {
  id: string;
  business_roles: PartyBusinessRole[];
  party_type: PartyType;
  name: string;
  code: string;
  identifier_type?: PartyIdentifierType | null;
  identifier_display?: string | null;
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

export type PartyLifecycleOperation = 'deactivate' | 'reactivate';

export interface PartyLifecycleState {
  party_id: string;
  status: string;
  review_status: string;
  available_for_new_references: boolean;
}

export interface PartyLifecycleImpact {
  represented_organization_count: number;
  potentially_affected_organization_count: number;
  current_user_binding_count: number;
  affected_user_count: number;
  user_scope_change_count: number;
  asset_reference_count: number;
  project_reference_count: number;
  contract_group_reference_count: number;
  contract_reference_count: number;
}

export interface PartyLifecyclePreviewRequest {
  operation: PartyLifecycleOperation;
}

export interface PartyLifecyclePreviewResponse {
  party_id: string;
  operation: PartyLifecycleOperation;
  before_state: PartyLifecycleState;
  after_state: PartyLifecycleState;
  impact: PartyLifecycleImpact;
  preview_token: string;
  expires_at: string;
}

export interface PartyLifecycleCommitRequest {
  preview_token: string;
  reason: string;
  idempotency_key: string;
}

export interface PartyLifecycleCommitResponse {
  party: Party;
  operation: PartyLifecycleOperation;
  before_state: PartyLifecycleState;
  after_state: PartyLifecycleState;
  impact: PartyLifecycleImpact;
  committed_at: string;
  idempotent: boolean;
}
export type CustomerType = 'internal' | 'external';
export type CustomerSubjectNature = 'enterprise' | 'individual';
export type CustomerContractRole = 'downstream_sublease' | 'direct_lease';
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
  identifier_display?: string | null;
  address?: string | null;
  status: string;
  historical_contract_count: number;
  risk_tags: string[];
  risk_tag_items: CustomerRiskTag[];
  payment_term_preference?: string | null;
  contracts: CustomerContractSummary[];
}

export interface PartyListParams {
  business_role?: PartyBusinessRole;
  party_type?: PartyType;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
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
