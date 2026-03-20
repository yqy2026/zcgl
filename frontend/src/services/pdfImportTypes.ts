/**
 * PDF导入服务 - 类型定义
 * 从 pdfImportService.ts 拆分而来，包含所有接口和类型定义
 */

import type { PdfImportSessionProgress } from '@/types/pdfImport';

export const legacyOwnerFilterField = `${'ownership'}_${'id'}` as const;

// 类型定义
export interface FileInfo {
  filename: string;
  size: number;
  content_type: string;
}

export interface FileUploadResponse {
  success: boolean;
  message: string;
  session_id?: string;
  estimated_time?: string;
  error?: string;
}

export interface SessionProgress {
  session_id: string;
  status: string;
  progress: number;
  current_step: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
  processing_method?: string;
  extracted_data?: Record<string, unknown>;
  progress_percentage?: number;
  chinese_char_count?: number;
  confidence_score?: number;
  vision_used?: boolean;
  validation_results?: Record<string, unknown>;
  // Extended properties for multi-engine processing
  file_name?: string;
  file_size?: number;
  validated_data?: Record<string, unknown>;
  matching_results?: {
    matched_assets?: AssetMatch[];
    matched_ownerships?: OwnershipMatch[];
    duplicate_contracts?: DuplicateContract[];
    recommendations?: Record<string, string>;
    overall_match_confidence?: number;
  };
  processing_status?: PdfImportSessionProgress['processing_status'];
}

export interface SystemCapabilities {
  [key: string]: boolean | string | number | string[] | undefined;
}

export interface SystemInfoResponse {
  success: boolean;
  message: string;
  capabilities: SystemCapabilities;
  system_info?: {
    version: string;
    vision_available: boolean;
    features: string[];
  };
  extractor_summary?: Record<string, unknown>;
  validator_summary?: Record<string, unknown>;
}

export interface ExtendedSessionProgress extends SessionProgress {
  validated_data?: Record<string, unknown>;
  matching_results?: {
    matched_assets?: AssetMatch[];
    matched_ownerships?: OwnershipMatch[];
    duplicate_contracts?: DuplicateContract[];
    recommendations?: Record<string, string>;
    overall_match_confidence?: number;
  };
  confidence_score?: number;
  file_name?: string;
  file_size?: number;
}

export interface AssetMatch {
  id: string;
  asset_name: string;
  address: string;
  similarity: number;
}

export interface OwnershipMatch {
  id: string;
  ownership_name: string;
  similarity: number;
}

export interface DuplicateContract {
  id: string;
  contract_number: string;
  tenant_name: string;
  created_at?: string;
}

export interface ValidationResult {
  success: boolean;
  errors: string[];
  warnings: string[];
  validated_data: Record<string, unknown>;
  validation_score: number;
  processed_fields: number;
  required_fields_count: number;
  missing_required_fields: string[];
}

export interface MatchingResult {
  matched_assets: AssetMatch[];
  matched_ownerships: OwnershipMatch[];
  duplicate_contracts: DuplicateContract[];
  recommendations: Record<string, string>;
  match_confidence: number;
  error?: string;
}

export interface ExtractionResult {
  success: boolean;
  data: Record<string, unknown>;
  confidence_score: number;
  extraction_method: string;
  processed_fields: number;
  total_fields: number;
  warnings?: string[];
  field_evidence?: Record<string, unknown> | null;
  field_sources?: Record<string, unknown> | null;
  error?: string;
}

export interface ConfidenceScores {
  extraction_confidence: number;
  validation_score: number;
  match_confidence: number;
  total_confidence: number;
  semantic_confidence?: number;
  fusion_confidence?: number;
  overall_quality?: number;
}

export interface CompleteResult {
  success: boolean;
  session_id: string;
  file_info: FileInfo;
  extraction_result: ExtractionResult;
  validation_result: ValidationResult;
  matching_result: MatchingResult;
  summary: ConfidenceScores;
  recommendations: string[];
  ready_for_import: boolean;
  semantic_validation?: unknown;
  processing_summary?: unknown;
  quality_metrics?: unknown;
}

export interface RentTermData {
  start_date: string;
  end_date: string;
  monthly_rent: string;
  rent_description?: string;
  management_fee?: string;
  other_fees?: string;
  total_monthly_amount?: string;
}

export type PdfImportRevenueMode = 'LEASE' | 'AGENCY';
export type PdfImportContractDirection = 'LESSOR' | 'LESSEE';
export type PdfImportGroupRelationType = 'UPSTREAM' | 'DOWNSTREAM' | 'ENTRUSTED' | 'DIRECT_LEASE';

export interface PdfImportSettlementRule {
  version: string;
  cycle: string;
  settlement_mode: string;
  amount_rule: Record<string, unknown>;
  payment_rule: Record<string, unknown>;
}

export interface PdfImportAgencyDetail {
  service_fee_ratio: string;
  fee_calculation_base: 'actual_received' | 'due_amount';
  agency_scope?: string;
}

export interface ConfirmedContractData {
  revenue_mode: PdfImportRevenueMode;
  contract_direction: PdfImportContractDirection;
  group_relation_type: PdfImportGroupRelationType;
  operator_party_id: string;
  contract_number: string;
  asset_id?: string;
  owner_party_id?: string;
  /** @deprecated 兼容旧字段透传，不应与 owner_party_id 强制互写。 */
  [legacyOwnerFilterField]?: string;
  lessor_party_id: string;
  lessee_party_id: string;
  tenant_name: string;
  tenant_contact?: string;
  tenant_phone?: string;
  tenant_address?: string;
  sign_date?: string;
  start_date: string;
  end_date: string;
  monthly_rent_base: string;
  total_deposit?: string;
  contract_status?: string;
  payment_terms?: string;
  contract_notes?: string;
  settlement_rule: PdfImportSettlementRule;
  agency_detail?: PdfImportAgencyDetail;
  rent_terms: RentTermData[];
}

export interface ConfirmImportResponse {
  success: boolean;
  message: string;
  contract_group_id?: string;
  contract_id?: string;
  contract_number?: string;
  created_terms_count?: number;
  processing_time?: number;
  error?: string;
}
