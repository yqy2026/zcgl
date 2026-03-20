/**
 * PDF导入服务 - 解析与工具函数
 * 从 pdfImportService.ts 拆分而来，包含类型守卫、规范化、结果构建等纯函数
 */

import { normalizeOptionalId } from '@/utils/normalize';

import type {
  ConfirmedContractData,
  SessionProgress,
  CompleteResult,
} from './pdfImportTypes';
import { legacyOwnerFilterField } from './pdfImportTypes';

// ============================================================
// 类型守卫
// ============================================================

/** 检查是否为 Error 对象 */
export function isError(error: unknown): error is Error {
  return error instanceof Error;
}

/** 检查是否为 AxiosError 兼容结构 */
export function isAxiosError(error: unknown): error is {
  response?: { data?: { detail?: string }; status?: number; statusText?: string };
  request?: unknown;
  code?: string;
  name?: string;
  message?: string;
} {
  return (
    typeof error === 'object' &&
    error !== null &&
    ('response' in error || 'request' in error || 'code' in error)
  );
}

// ============================================================
// 错误处理辅助
// ============================================================

/**
 * 从 axios 风格的 error 中提取用户可读的错误信息。
 * `fallback` 用于既不是 AxiosError 也不是 Error 时的兜底文案。
 */
export function extractErrorDetail(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    return error.response?.data?.detail ?? error.message ?? fallback;
  }
  if (isError(error)) {
    return error.message;
  }
  return fallback;
}

/**
 * 从 axios 风格的 error 中提取技术性错误代码/消息。
 */
export function extractErrorCode(error: unknown): string {
  if (isAxiosError(error)) {
    return error.response?.data?.detail ?? error.message ?? 'Unknown error';
  }
  if (isError(error)) {
    return error.message;
  }
  return 'Unknown error';
}

// ============================================================
// 数据规范化
// ============================================================

/** 规范化确认导入数据中的可选 ID 字段 */
export function normalizeConfirmedContractData(
  payload: ConfirmedContractData
): ConfirmedContractData {
  const normalizedPayload: ConfirmedContractData = { ...payload };
  const normalizedAssetId = normalizeOptionalId(payload.asset_id);
  const normalizedOwnerPartyId = normalizeOptionalId(payload.owner_party_id);
  const normalizedOwnershipId = normalizeOptionalId(payload[legacyOwnerFilterField]);
  normalizedPayload.operator_party_id = payload.operator_party_id.trim();
  normalizedPayload.lessor_party_id = payload.lessor_party_id.trim();
  normalizedPayload.lessee_party_id = payload.lessee_party_id.trim();

  if (normalizedAssetId != null) {
    normalizedPayload.asset_id = normalizedAssetId;
  } else if ('asset_id' in normalizedPayload) {
    delete normalizedPayload.asset_id;
  }

  if (normalizedOwnerPartyId != null) {
    normalizedPayload.owner_party_id = normalizedOwnerPartyId;
  } else if ('owner_party_id' in normalizedPayload) {
    delete normalizedPayload.owner_party_id;
  }

  if (normalizedOwnershipId != null) {
    normalizedPayload[legacyOwnerFilterField] = normalizedOwnershipId;
  } else if (legacyOwnerFilterField in normalizedPayload) {
    delete normalizedPayload[legacyOwnerFilterField];
  }

  return normalizedPayload;
}

// ============================================================
// 结果构建
// ============================================================

/**
 * 从 SessionProgress 构建完整的 CompleteResult 对象。
 * 原始逻辑来自 PDFImportService.getPdfImportResult 内部。
 */
export function buildCompleteResult(
  sessionId: string,
  session: SessionProgress
): CompleteResult {
  const processingStatus = session.processing_status;
  const processingStatusRecord =
    processingStatus != null && typeof processingStatus === 'object'
      ? (processingStatus as Record<string, unknown>)
      : undefined;
  const finalResultsRecord =
    processingStatusRecord?.final_results != null &&
    typeof processingStatusRecord.final_results === 'object'
      ? (processingStatusRecord.final_results as Record<string, unknown>)
      : undefined;
  const fieldEvidence =
    (processingStatusRecord?.field_evidence as Record<string, unknown> | undefined) ??
    (finalResultsRecord?.field_evidence as Record<string, unknown> | undefined);
  const fieldSources =
    (processingStatusRecord?.field_sources as Record<string, unknown> | undefined) ??
    (finalResultsRecord?.field_sources as Record<string, unknown> | undefined);
  const extractionWarnings = (() => {
    const rawWarnings =
      processingStatusRecord?.warnings ?? finalResultsRecord?.warnings ?? undefined;
    return Array.isArray(rawWarnings) ? rawWarnings : undefined;
  })();

  return {
    success: true,
    session_id: sessionId,
    file_info: {
      filename: session.file_name ?? 'unknown.pdf',
      size: session.file_size ?? 0,
      content_type: 'application/pdf',
    },
    extraction_result: {
      success: true,
      data: processingStatus?.final_fields ?? {},
      confidence_score:
        processingStatus?.final_results?.extraction_quality?.overall_quality ?? 0.8,
      extraction_method: 'multi_engine',
      processed_fields: Object.keys(processingStatus?.final_fields ?? {}).length,
      total_fields: 58,
      warnings: extractionWarnings,
      field_evidence: fieldEvidence,
      field_sources: fieldSources,
    },
    validation_result: {
      success: true,
      errors: [],
      warnings: [],
      validated_data: processingStatus?.final_fields ?? {},
      validation_score: processingStatus?.final_results?.validation_score ?? 0.8,
      processed_fields: Object.keys(processingStatus?.final_fields ?? {}).length,
      required_fields_count: 10,
      missing_required_fields: [],
    },
    matching_result: {
      matched_assets: [],
      matched_ownerships: [],
      duplicate_contracts: [],
      recommendations: {},
      match_confidence: processingStatus?.final_results?.match_confidence ?? 0.7,
    },
    semantic_validation: processingStatus?.semantic_validation ?? {
      total_fields: 0,
      valid_fields: 0,
      error_fields: 0,
      warning_fields: 0,
      overall_confidence: 0.0,
      field_results: {},
      semantic_analysis: {},
      summary: '',
      recommendations: [],
    },
    processing_summary: {
      total_processing_time: '60-90秒',
      extraction_method: 'multi_engine',
      engines_used: processingStatus?.final_results?.processing_summary?.engines_used ?? [],
      processing_steps: [],
      performance_metrics: {
        total_processing_time: 0,
        memory_usage: 0,
        cpu_usage: 0,
      },
      quality_assessment: {
        text_quality_score: 0.0,
        structure_quality_score: 0.0,
        data_completeness_score: 0.0,
        semantic_accuracy_score: 0.0,
        overall_quality_score: 0.0,
        improvement_suggestions: [],
      },
    },
    summary: {
      extraction_confidence:
        processingStatus?.final_results?.extraction_quality?.overall_quality ?? 0.8,
      validation_score: processingStatus?.final_results?.validation_score ?? 0.8,
      match_confidence: processingStatus?.final_results?.match_confidence ?? 0.7,
      semantic_confidence: processingStatus?.semantic_validation?.overall_confidence ?? 0.8,
      fusion_confidence: processingStatus?.fusion_results?.confidence ?? 0.8,
      overall_quality:
        processingStatus?.final_results?.extraction_quality?.overall_quality ?? 0.8,
      total_confidence: 0.8,
    },
    recommendations: processingStatus?.semantic_validation?.recommendations ?? [],
    ready_for_import: true,
    quality_metrics: {
      extraction_quality:
        processingStatus?.final_results?.extraction_quality?.overall_quality ?? 0.8,
      validation_quality: processingStatus?.final_results?.validation_score ?? 0.8,
      matching_quality: processingStatus?.final_results?.match_confidence ?? 0.7,
      semantic_quality: processingStatus?.semantic_validation?.overall_confidence ?? 0.8,
      processing_efficiency: 0.8,
      overall_score: 0.8,
    },
  };
}

// ============================================================
// 纯工具函数
// ============================================================

/** 文件大小格式化 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/** 验证文件类型 */
export function validateFileType(file: File): boolean {
  const allowedTypes = ['application/pdf'];
  const allowedExtensions = ['.pdf'];

  return (
    allowedTypes.includes(file.type) ||
    allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext))
  );
}

/** 验证文件大小 */
export function validateFileSize(file: File, maxSizeMB: number = 50): boolean {
  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  return file.size <= maxSizeBytes;
}

/** 计算预计处理时间（基础模式） */
export function estimateProcessingTime(fileSize: number): string {
  const sizeMB = fileSize / (1024 * 1024);

  if (sizeMB < 1) return '10-20秒';
  if (sizeMB < 5) return '20-40秒';
  if (sizeMB < 10) return '30-60秒';
  if (sizeMB < 20) return '45-90秒';

  return '60-120秒';
}

/** 计算预计处理时间（多引擎模式，耗时更长但更准确） */
export function estimatePdfImportProcessingTime(fileSize: number): string {
  const sizeMB = fileSize / (1024 * 1024);

  if (sizeMB < 1) return '30-45秒';
  if (sizeMB < 5) return '45-75秒';
  if (sizeMB < 10) return '60-90秒';
  if (sizeMB < 20) return '90-150秒';

  return '120-240秒';
}

// ============================================================
// getSystemInfo 备用/默认数据常量
// ============================================================

import type { SystemCapabilities, SystemInfoResponse } from './pdfImportTypes';

/** 默认系统能力（后端未返回时的兜底） */
export const DEFAULT_SYSTEM_CAPABILITIES: SystemCapabilities = {
  pdfplumber_available: true,
  pymupdf_available: true,
  spacy_available: true,
  vision_available: true,
  supported_formats: ['.pdf', '.jpg', '.jpeg', '.png'],
  max_file_size_mb: 50,
  estimated_processing_time: '30-60秒',
};

/** 多引擎增强能力附加字段 */
export const ENHANCED_CAPABILITY_FLAGS: SystemCapabilities = {
  enhanced_extraction: true,
  intelligent_matching: true,
  multi_engine_support: true,
  chinese_optimized: true,
  real_time_validation: true,
};

/** 备用模式系统信息（404 降级） */
export const FALLBACK_SYSTEM_INFO: SystemInfoResponse = {
  success: true,
  message: 'PDF智能导入系统（备用模式）',
  capabilities: {
    pdfplumber_available: true,
    pymupdf_available: true,
    spacy_available: false,
    vision_available: false,
    supported_formats: ['.pdf'],
    max_file_size_mb: 10,
    estimated_processing_time: '30-60秒',
    enhanced_extraction: false,
    intelligent_matching: false,
    multi_engine_support: false,
    chinese_optimized: false,
    real_time_validation: false,
  },
  extractor_summary: { method: 'basic', description: '基础PDF处理模式', engines: ['PDFPlumber'], features: ['基础文本提取'] },
  validator_summary: { enabled: false, description: '数据验证功能暂时不可用', features: [], accuracy_improvement: '0%' },
};

/** 失败状态系统信息 */
export const FAILED_SYSTEM_INFO: SystemInfoResponse = {
  success: false,
  message: '系统信息获取失败',
  capabilities: {
    pdfplumber_available: false,
    pymupdf_available: false,
    spacy_available: false,
    vision_available: false,
    supported_formats: [],
    max_file_size_mb: 0,
    estimated_processing_time: '未知',
  },
  extractor_summary: { method: 'unavailable' },
  validator_summary: { enabled: false },
};

/** 系统信息接口的默认 extractor_summary */
export const DEFAULT_EXTRACTOR_SUMMARY = {
  method: 'multi_engine',
  description: '多引擎PDF处理，支持智能引擎选择和质量评估',
  engines: ['PyMuPDF', 'PDFPlumber', 'LLM Vision'],
  features: ['智能预处理', '多引擎字段提取', '实时验证', '优化匹配算法'],
} as const;

/** 系统信息接口的默认 validator_summary */
export const DEFAULT_VALIDATOR_SUMMARY = {
  enabled: true,
  description: '多引擎数据验证和智能匹配功能',
  features: ['多维度验证', '智能模糊匹配', '重复检测', '置信度评估'],
  accuracy_improvement: '15-20%',
} as const;

// ============================================================
// 上传错误处理
// ============================================================

import type { FileUploadResponse } from './pdfImportTypes';

/**
 * 处理上传类 API 的 catch 分支，返回统一的 FileUploadResponse 错误。
 * 若为用户主动取消则 throw Error('canceled')。
 */
export function handleUploadError(error: unknown): FileUploadResponse {
  if (isAxiosError(error)) {
    if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
      throw new Error('canceled');
    }
    if (error.code === 'ECONNABORTED') {
      return { success: false, message: '上传超时，请检查文件大小或网络连接后重试', error: 'Upload timeout' };
    }
    if (error.response) {
      const errorMessage = error.response.data?.detail ?? error.response.statusText ?? '服务器处理失败';
      return { success: false, message: errorMessage, error: errorMessage };
    }
    if (error.request != null) {
      return { success: false, message: '网络连接失败，请检查网络连接', error: 'Network connection failed' };
    }
  }
  return {
    success: false,
    message: isError(error) ? error.message : '上传失败',
    error: isError(error) ? error.message : 'Unknown error',
  };
}
