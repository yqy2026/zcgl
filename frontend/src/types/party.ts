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
