/**
 * 增强版PDF导入相关类型定义
 * 对应后端新的中文合同识别优化组件
 */

import type { CompleteResult } from '@/services/pdfImportService';

// 引擎类型枚举
export enum EngineType {
  PADDLE_OCR = 'paddle_ocr',
  TESSERACT = 'tesseract',
  EASY_OCR = 'easy_ocr',
  PYMUPDF = 'pymupdf',
  PDFPLUMBER = 'pdfplumber',
  CUSTOM_NLP = 'custom_nlp',
  VISION_AI = 'vision_ai',
}

// 字段类型枚举
export enum FieldType {
  TEXT = 'text',
  NUMBER = 'number',
  DECIMAL = 'decimal',
  DATE = 'date',
  PHONE = 'phone',
  ADDRESS = 'address',
  PERSON_NAME = 'person_name',
  ORGANIZATION = 'organization',
  ID_CARD = 'id_card',
  EMAIL = 'email',
  URL = 'url',
  BOOLEAN = 'boolean',
  ENUM = 'enum',
}

// 验证级别枚举
export enum ValidationLevel {
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
  SUCCESS = 'success',
}

// 引擎结果接口
export interface EngineResult {
  engine_type: EngineType;
  text: string;
  confidence: number;
  bbox?: [number, number, number, number];
  processing_time: number;
  metadata: Record<string, unknown>;
  quality_score: number;
}

// 融合结果接口
export interface FusionResult {
  text: string;
  confidence: number;
  contributing_engines: EngineType[];
  fusion_method: string;
  quality_indicators: Record<string, number>;
  processing_stats: Record<string, unknown>;
}

// 语义分析结果接口
export interface SemanticAnalysisResult {
  field_name: string;
  field_type: FieldType;
  semantic_meaning: string;
  context_relevance: number;
  confidence: number;
  extracted_entities: Record<string, unknown>;
  relationships: Record<string, string>;
  validation_result?: ValidationResult;
}

// 验证结果接口
export interface ValidationResult {
  field_name: string;
  original_value: string;
  normalized_value: unknown;
  validation_level: ValidationLevel;
  confidence: number;
  error_messages: string[];
  warning_messages: string[];
  info_messages: string[];
  suggestions: string[];
  metadata: Record<string, unknown>;
}

// 合同验证报告接口
export interface ContractValidationReport {
  contract_id?: string;
  total_fields: number;
  valid_fields: number;
  error_fields: number;
  warning_fields: number;
  overall_confidence: number;
  field_results: Record<string, ValidationResult>;
  semantic_analysis: Record<string, SemanticAnalysisResult>;
  summary: string;
  recommendations: string[];
}

// 表格分析结果接口
export interface TableAnalysisResult {
  table_count: number;
  tables: TableInfo[];
  structured_data: Record<string, unknown>;
}

export interface TableInfo {
  data: unknown[][];
  metadata: {
    rows: number;
    columns: number;
    header_row: number;
    confidence: number;
    table_type: string;
  };
}

// OCR结果接口
export interface OCRResult {
  success: boolean;
  text: string;
  confidence: number;
  processing_method: string;
  engine_results: Record<string, EngineResult>;
  fusion_result?: FusionResult;
  metadata: {
    page_count: number;
    ocr_used: boolean;
    processing_time: number;
    quality_score: number;
  };
}

// 印章检测结果接口
export interface SealDetectionResult {
  success: boolean;
  seals: SealInfo[];
  signatures: SignatureInfo[];
  summary: {
    seal_count: number;
    signature_count: number;
    confidence_average: number;
  };
}

export interface SealInfo {
  type: 'circular' | 'oval' | 'square';
  position: [number, number, number, number];
  confidence: number;
  clarity: number;
  color_analysis: {
    dominant_color: string;
    red_ratio: number;
  };
}

export interface SignatureInfo {
  position: [number, number, number, number];
  confidence: number;
  stroke_analysis: {
    continuity: number;
    complexity: number;
  };
}

// 模板学习结果接口
export interface TemplateLearningResult {
  success: boolean;
  template_id?: string;
  template_name?: string;
  confidence: number;
  extracted_fields: Record<string, unknown>;
  pattern_matches: PatternMatch[];
  learning_updates: {
    new_templates_created: number;
    existing_templates_updated: number;
  };
}

export interface PatternMatch {
  field_name: string;
  pattern: string;
  confidence: number;
  position: [number, number];
}

// 处理选项接口
export interface ProcessingOptions {
  prefer_ocr?: boolean;
  enable_chinese_optimization?: boolean;
  enable_table_detection?: boolean;
  enable_seal_detection?: boolean;
  confidence_threshold?: number;
  use_template_learning?: boolean;
  enable_multi_engine_fusion?: boolean;
  enable_semantic_validation?: boolean;
}

// 增强版会话状态接口
export interface EnhancedSessionProgress {
  success: boolean;
  session_id: string;
  status: string;
  progress: number;
  current_step: string;
  created_at: string;
  updated_at: string;
  error_message?: string;

  // Flattened properties used in EnhancedProcessingStatus
  processing_method?: string;
  chinese_char_count?: number;
  extracted_data?: Record<string, unknown>;
  validation_results?: Record<string, unknown> | boolean;
  progress_percentage?: number;
  confidence_score?: number;
  ocr_used?: boolean;
  warnings?: string[];

  // 增强版状态信息
  enhanced_status?: {
    extraction_results?: {
      methods_used: string[];
      has_chinese_ocr: boolean;
      has_tables: boolean;

      has_seals: boolean;
    };
    document_analysis?: {
      document_type?: string;
      quality_score?: number;
      recommendations?: string[];
    };
    table_analysis?: TableAnalysisResult;
    fusion_results?: {
      method: string;
      confidence: number;
      engines_used: EngineType[];
      quality_indicators: Record<string, number>;
    };
    semantic_validation?: {
      total_fields: number;
      valid_fields: number;
      error_fields: number;
      warning_fields: number;
      overall_confidence: number;
      summary: string;
      recommendations: string[];
    };
    final_results?: {
      extraction_quality: {
        extraction_methods: number;
        fusion_confidence: number;
        semantic_confidence: number;
        error_rate: number;
        completeness: number;

        overall_quality: number;
        processing_methods?: string[];
      };
      processing_summary: {
        processing_methods: string[];
        engines_used: string[];
        table_count: number;
        seal_count: number;
        template_used?: string;
        fusion_method?: string;
      };
      validation_score: number;
      match_confidence: number;
    };
    final_fields?: Record<string, unknown>;
  };
}

// 增强版文件上传响应接口
export interface EnhancedFileUploadResponse {
  success: boolean;
  message: string;
  session_id?: string;
  estimated_time?: string;
  processing_options?: ProcessingOptions;
  error?: string;
  enhanced_status?: EnhancedSessionProgress['enhanced_status'];
}

// 增强版完整结果接口
export interface EnhancedCompleteResult {
  session_id: string;
  file_info: FileInfo;
  extraction_result: EnhancedExtractionResult;
  validation_result: EnhancedValidationResult;
  matching_result: MatchingResult;
  semantic_validation: ContractValidationReport;
  processing_summary: EnhancedProcessingSummary;
  summary: EnhancedConfidenceScores;
  recommendations: string[];
  ready_for_import: boolean;
  quality_metrics: QualityMetrics;
}

// 增强版提取结果接口
export interface EnhancedExtractionResult {
  success: boolean;
  data: Record<string, unknown>;
  confidence_score: number;
  extraction_method: string;
  processed_fields: number;
  total_fields: number;
  ocr_result?: OCRResult;
  table_analysis?: TableAnalysisResult;
  seal_detection?: SealDetectionResult;
  template_learning?: TemplateLearningResult;
  multi_engine_fusion?: FusionResult;
  extraction_quality: {
    text_quality: number;
    structure_quality: number;
    completeness_score: number;
  };
  error?: string;
}

// 增强版验证结果接口
export interface EnhancedValidationResult {
  success: boolean;
  errors: string[];
  warnings: string[];
  validated_data: Record<string, unknown>;
  validation_score: number;
  processed_fields: number;
  required_fields_count: number;
  missing_required_fields: string[];
  semantic_validation: ContractValidationReport;
  field_validations: Record<string, ValidationResult>;
  business_rule_validations: Record<string, BusinessRuleResult>;
}

// 业务规则验证结果接口
export interface BusinessRuleResult {
  status: 'pass' | 'warning' | 'error';
  message: string;
  fields?: string[];
  details?: Record<string, unknown>;
}

// 增强版置信度分数接口
export interface EnhancedConfidenceScores {
  extraction_confidence: number;
  validation_score: number;
  match_confidence: number;
  semantic_confidence: number;
  fusion_confidence: number;
  overall_quality: number;
  total_confidence: number;
}

// 增强版处理摘要接口
export interface EnhancedProcessingSummary {
  total_processing_time: string;
  extraction_method: string;
  engines_used: string[];
  processing_steps: ProcessingStepResult[];
  performance_metrics: PerformanceMetrics;
  quality_assessment: QualityAssessment;
}

// 处理步骤结果接口
export interface ProcessingStepResult {
  step_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  duration: number;
  confidence?: number;
  details?: Record<string, unknown>;
}

// 性能指标接口
export interface PerformanceMetrics {
  total_processing_time: number;
  ocr_processing_time?: number;
  table_analysis_time?: number;
  fusion_processing_time?: number;
  validation_processing_time?: number;
  memory_usage?: number;
  cpu_usage?: number;
}

// 质量评估接口
export interface QualityAssessment {
  text_quality_score: number;
  structure_quality_score: number;
  data_completeness_score: number;
  semantic_accuracy_score: number;
  overall_quality_score: number;
  improvement_suggestions: string[];
}

// 质量指标接口
export interface QualityMetrics {
  extraction_quality: number;
  validation_quality: number;
  matching_quality: number;
  semantic_quality: number;
  processing_efficiency: number;
  overall_score: number;
}

// 系统能力增强接口
export interface EnhancedSystemCapabilities {
  pdfplumber_available: boolean;
  pymupdf_available: boolean;
  spacy_available: boolean;
  ocr_available: boolean;
  enhanced_extraction: boolean;
  intelligent_matching: boolean;
  multi_engine_support: boolean;
  chinese_optimized: boolean;
  real_time_validation: boolean;
  table_detection: boolean;
  seal_detection: boolean;
  template_learning: boolean;
  semantic_validation: boolean;
  supported_formats: string[];
  max_file_size_mb: number;
  estimated_processing_time: string;
}

// 增强版系统信息响应接口
export interface EnhancedSystemInfoResponse {
  success: boolean;
  message: string;
  capabilities: EnhancedSystemCapabilities;
  extractor_summary?: {
    method: string;
    description: string;
    engines: string[];
    features: string[];
  };
  validator_summary?: {
    enabled: boolean;
    description: string;
    features: string[];
    accuracy_improvement: string;
  };
  performance_stats?: {
    avg_processing_time: string;
    success_rate: number;
    accuracy_improvement: string;
    supported_languages: string[];
  };
}

// 错误处理增强接口
export interface EnhancedErrorInfo {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  suggestions?: string[];
  recovery_options?: RecoveryOption[];
}

export interface RecoveryOption {
  action: string;
  description: string;
  auto_recover: boolean;
}

// 文件信息接口（复用原有）
export interface FileInfo {
  filename: string;
  size: number;
  content_type: string;
}

// 资产匹配接口（复用原有）
export interface AssetMatch {
  id: string;
  property_name: string;
  address: string;
  similarity: number;
}

// 权属匹配接口（复用原有）
export interface OwnershipMatch {
  id: string;
  ownership_name: string;
  similarity: number;
}

// 重复合同接口（复用原有）
export interface DuplicateContract {
  id: string;
  contract_number: string;
  tenant_name: string;
  created_at?: string;
}

// 匹配结果接口（复用原有）
export interface MatchingResult {
  matched_assets: AssetMatch[];
  matched_ownerships: OwnershipMatch[];
  duplicate_contracts: DuplicateContract[];
  recommendations: Record<string, string>;
  match_confidence: number;
  error?: string;
}

// 租金条款数据接口（复用原有）
export interface RentTermData {
  start_date: string;
  end_date: string;
  monthly_rent: string;
  rent_description?: string;
  management_fee?: string;
  other_fees?: string;
  total_monthly_amount?: string;
}

// 确认合同数据接口（复用原有）
export interface ConfirmedContractData {
  contract_number: string;
  asset_id?: string;
  ownership_id?: string;
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
  rent_terms: RentTermData[];
}

// 确认导入响应接口（复用原有）
export interface ConfirmImportResponse {
  success: boolean;
  message: string;
  contract_id?: string;
  contract_number?: string;
  created_terms_count?: number;
  processing_time?: number;
  error?: string;
}

// ==================== 会话管理类型 ====================

// 导入自 antd UploadFile 类型（避免直接导入）
export type UploadFileStatus = 'uploading' | 'done' | 'error' | 'removed';

export interface UploadFileInfo {
  uid: string;
  name: string;
  status?: UploadFileStatus;
  size?: number;
  type?: string;
}

// PDF导入会话状态
export type SessionStatus = 'uploading' | 'processing' | 'ready' | 'completed' | 'failed';

// PDF导入会话接口
export interface ProcessingSession {
  sessionId: string;
  fileInfo: UploadFileInfo;
  status: SessionStatus;
  progress: number;
  result?: CompleteResult;
  error?: string;
}
