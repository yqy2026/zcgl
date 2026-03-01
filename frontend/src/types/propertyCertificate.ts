/**
 * Property Certificate Types
 * 产权证类型定义
 */

// Enums
export enum CertificateType {
  REAL_ESTATE = 'real_estate',
  HOUSE_OWNERSHIP = 'house_ownership',
  LAND_USE = 'land_use',
  OTHER = 'other',
}

export enum OwnerType {
  INDIVIDUAL = 'individual',
  ORGANIZATION = 'organization',
  JOINT = 'joint',
}

// Property Certificate
export interface PropertyCertificate {
  id: string;
  certificate_number: string;
  certificate_type: CertificateType;
  registration_date: string | null;
  property_address: string | null;
  property_type: string | null;
  building_area: string | null;
  land_area: string | null;
  floor_info: string | null;
  land_use_type: string | null;
  land_use_term_start: string | null;
  land_use_term_end: string | null;
  co_ownership: string | null;
  restrictions: string | null;
  remarks: string | null;
  extraction_confidence: number | null;
  extraction_source: string;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  owners: PropertyOwner[];
  asset_ids: string[];
}

// Property Owner
export interface PropertyOwner {
  id: string;
  owner_type: OwnerType;
  name: string;
  id_type: string | null;
  id_number: string | null;
  phone: string | null;
  address: string | null;
  party_id: string | null;
  created_at: string;
  updated_at: string;
}

// Extraction Result
export interface CertificateExtractionResult {
  session_id: string;
  certificate_type: CertificateType;
  extracted_data: Record<string, unknown>;
  confidence_score: number;
  asset_matches: AssetMatch[];
  validation_errors: string[];
  warnings: string[];
}

// Asset Match
export interface AssetMatch {
  asset_id: string;
  name: string;
  address: string;
  confidence: number;
  match_reasons: string[];
}

// Import Confirm
export interface CertificateImportConfirm {
  session_id: string;
  asset_ids: string[];
  extracted_data: Record<string, unknown>;
  asset_link_id: string | null;
  should_create_new_asset: boolean;
  owners: Record<string, unknown>[];
}

// Forms
export interface PropertyCertificateCreate {
  certificate_number: string;
  certificate_type: CertificateType;
  registration_date: string | null;
  property_address: string | null;
  property_type: string | null;
  building_area: string | null;
  land_area: string | null;
  floor_info: string | null;
  land_use_type: string | null;
  land_use_term_start: string | null;
  land_use_term_end: string | null;
  co_ownership: string | null;
  restrictions: string | null;
  remarks: string | null;
  asset_ids: string[];
  owner_ids: string[];
}

export interface PropertyCertificateUpdate {
  certificate_number?: string;
  certificate_type?: CertificateType;
  registration_date?: string | null;
  property_address?: string | null;
  building_area?: string | null;
  land_area?: string | null;
  floor_info?: string | null;
  land_use_type?: string | null;
  land_use_term_start?: string | null;
  land_use_term_end?: string | null;
  co_ownership?: string | null;
  restrictions?: string | null;
  remarks?: string | null;
  is_verified?: boolean;
  asset_ids?: string[];
}
