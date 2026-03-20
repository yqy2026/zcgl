/**
 * PDF导入服务
 * 处理PDF文件上传、转换、信息提取等API调用
 * 支持多引擎中文合同识别功能
 *
 * 重导出中心 — 实际类型定义见 pdfImportTypes.ts，
 * 解析/工具函数见 pdfImportParser.ts。
 */

import { apiClient } from '@/api/client';
import type { ProcessingOptions, PdfImportFileUploadResponse } from '@/types/pdfImport';
import { createLogger } from '@/utils/logger';
import { PDF_API } from '@/constants/api';

import type {
  SessionProgress,
  SystemCapabilities,
  SystemInfoResponse,
  CompleteResult,
  ConfirmedContractData,
  ConfirmImportResponse,
} from './pdfImportTypes';

import {
  isError,
  isAxiosError,
  extractErrorDetail,
  extractErrorCode,
  normalizeConfirmedContractData,
  buildCompleteResult,
  handleUploadError,
  formatFileSize as _formatFileSize,
  validateFileType as _validateFileType,
  validateFileSize as _validateFileSize,
  estimateProcessingTime as _estimateProcessingTime,
  estimatePdfImportProcessingTime as _estimatePdfImportProcessingTime,
  DEFAULT_SYSTEM_CAPABILITIES,
  ENHANCED_CAPABILITY_FLAGS,
  FALLBACK_SYSTEM_INFO,
  FAILED_SYSTEM_INFO,
  DEFAULT_EXTRACTOR_SUMMARY,
  DEFAULT_VALIDATOR_SUMMARY,
} from './pdfImportParser';

// ── Re-export everything from sub-modules for backward compatibility ──
export type {
  FileInfo,
  FileUploadResponse,
  SessionProgress,
  SystemCapabilities,
  SystemInfoResponse,
  ExtendedSessionProgress,
  AssetMatch,
  OwnershipMatch,
  DuplicateContract,
  ValidationResult,
  MatchingResult,
  ExtractionResult,
  ConfidenceScores,
  CompleteResult,
  RentTermData,
  PdfImportRevenueMode,
  PdfImportContractDirection,
  PdfImportGroupRelationType,
  PdfImportSettlementRule,
  PdfImportAgencyDetail,
  ConfirmedContractData,
  ConfirmImportResponse,
} from './pdfImportTypes';

export {
  isError,
  isAxiosError,
  extractErrorDetail,
  extractErrorCode,
  normalizeConfirmedContractData,
  buildCompleteResult,
  handleUploadError,
  formatFileSize as formatFileSizeUtil,
  validateFileType as validateFileTypeUtil,
  validateFileSize as validateFileSizeUtil,
  estimateProcessingTime as estimateProcessingTimeUtil,
  estimatePdfImportProcessingTime as estimatePdfImportProcessingTimeUtil,
} from './pdfImportParser';

// ── Internal constants ──
const logger = createLogger('PDFImportService');
const API_BASE_URL = PDF_API.INFO.replace('/info', '');
const PROCESSING_API_BASE = `${API_BASE_URL}/enhanced`;

// ── Service class ──
export class PDFImportService {
  /** 上传PDF文件 */
  async uploadPDFFile(
    file: File,
    preferMarkitdown: boolean = true,
    signal?: AbortSignal
  ): Promise<import('./pdfImportTypes').FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('prefer_markitdown', preferMarkitdown.toString());
    try {
      const response = await apiClient.post<import('./pdfImportTypes').FileUploadResponse>(
        `${API_BASE_URL}/upload`, formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 300000,
          onUploadProgress: progressEvent => {
            if (progressEvent.total != null && progressEvent.total > 0) {
              Math.round((progressEvent.loaded * 100) / progressEvent.total);
            }
          },
          signal,
        }
      );
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      logger.error('PDF上传失败:', error as Error);
      return handleUploadError(error);
    }
  }

  /** 获取处理进度 */
  async getProgress(sessionId: string): Promise<{
    success: boolean; session_status?: SessionProgress; error?: string;
  }> {
    return this.getPdfImportProgress(sessionId);
  }

  /** 获取处理结果 */
  async getResult(sessionId: string): Promise<{
    success: boolean; result?: CompleteResult;
    processing_summary?: Record<string, unknown>; error?: string;
  }> {
    const result = await this.getPdfImportResult(sessionId);
    if (result.success) {
      return {
        success: true, result: result.result,
        processing_summary: result.result?.processing_summary as Record<string, unknown> | undefined,
      };
    }
    return { success: false, error: result.error ?? '获取进度失败' };
  }

  /** 确认导入合同 */
  async confirmImport(
    sessionId: string, confirmedData: ConfirmedContractData
  ): Promise<ConfirmImportResponse> {
    try {
      const normalized = normalizeConfirmedContractData(confirmedData);
      const response = await apiClient.post<ConfirmImportResponse>(PDF_API.CONFIRM_IMPORT, {
        session_id: sessionId,
        confirmed_data: { ...normalized, contract_data: normalized },
      });
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      logger.error('确认导入失败:', error as Error);
      return { success: false, message: extractErrorDetail(error, '导入失败'), error: extractErrorCode(error) };
    }
  }

  /** 取消导入会话 */
  async cancelSession(sessionId: string): Promise<{
    success: boolean; message: string; error?: string;
  }> {
    try {
      const response = await apiClient.delete<{ success: boolean; message: string; error?: string }>(
        `${API_BASE_URL}/session/${sessionId}`
      );
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      logger.error('取消会话失败:', error as Error);
      return { success: false, message: extractErrorDetail(error, '取消失败'), error: extractErrorCode(error) };
    }
  }

  /** 获取活跃会话列表 */
  async getActiveSessions(): Promise<{
    success: boolean;
    active_sessions: Array<{
      session_id: string; status: string; progress: number;
      current_step: string; created_at: string; file_name: string;
    }>;
    total_count: number; error?: string;
  }> {
    try {
      const response = await apiClient.get<{
        success: boolean;
        active_sessions: Array<{
          session_id: string; status: string; progress: number;
          current_step: string; created_at: string; file_name: string;
        }>;
        total_count: number; error?: string;
      }>(PDF_API.SESSIONS);
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      logger.error('获取会话列表失败:', error as Error);
      if (isAxiosError(error) && error.response?.status === 404) {
        logger.warn('PDF sessions API端点不存在，返回空会话列表');
        return { success: true, active_sessions: [], total_count: 0 };
      }
      return { success: false, active_sessions: [], total_count: 0, error: extractErrorCode(error) };
    }
  }

  /** 获取系统信息 - 多引擎版本 */
  async getSystemInfo(): Promise<SystemInfoResponse> {
    try {
      const response = await apiClient.get<{
        success: boolean; message: string; capabilities: SystemCapabilities;
        system_info?: { version: string; vision_available: boolean; features: string[] };
        extractor_summary?: Record<string, unknown>;
        validator_summary?: Record<string, unknown>;
      }>(PDF_API.INFO);
      if (!response.data) throw new Error('Empty response');

      const capabilities: SystemCapabilities =
        response.data.capabilities ?? DEFAULT_SYSTEM_CAPABILITIES;
      return {
        success: true,
        message: response.data.message ?? '多引擎PDF导入系统运行正常',
        capabilities: { ...capabilities, ...ENHANCED_CAPABILITY_FLAGS },
        extractor_summary: { ...DEFAULT_EXTRACTOR_SUMMARY },
        validator_summary: { ...DEFAULT_VALIDATOR_SUMMARY },
      };
    } catch (error: unknown) {
      logger.error('获取系统信息失败:', error as Error);
      if (isAxiosError(error) && error.response?.status === 404) {
        logger.warn('PDF API端点不存在，使用备用系统信息');
        return FALLBACK_SYSTEM_INFO;
      }
      return FAILED_SYSTEM_INFO;
    }
  }

  /** 获取系统能力信息 */
  static async getSystemCapabilities(): Promise<{
    spacy_available: boolean; vision_available: boolean; supported_formats: string[];
    max_file_size_mb: number; estimated_processing_time: string;
    extractor_summary?: Record<string, unknown>; validator_summary?: Record<string, unknown>;
  }> {
    try {
      const response = await apiClient.get<{
        extractor_summary?: Record<string, unknown>; validator_summary?: Record<string, unknown>;
      }>(`${API_BASE_URL}/capabilities`);
      if (!response.data) throw new Error('Empty response');
      return {
        spacy_available: true, vision_available: true,
        supported_formats: ['.pdf', '.jpg', '.jpeg', '.png'],
        max_file_size_mb: 50, estimated_processing_time: '30-60秒',
        extractor_summary: response.data.extractor_summary,
        validator_summary: response.data.validator_summary,
      };
    } catch (error: unknown) {
      logger.error('获取系统信息失败:', error as Error);
      throw new Error(extractErrorCode(error));
    }
  }

  /** 测试转换功能 */
  async testConversion(): Promise<{
    success: boolean; message: string;
    test_result?: Record<string, unknown>; system_ready?: boolean;
  }> {
    try {
      const response = await apiClient.get<{ message: string; features?: Record<string, unknown> }>(
        `${API_BASE_URL}/info`
      );
      if (!response.data) throw new Error('Empty response');
      return { success: true, message: response.data.message, test_result: response.data.features, system_ready: true };
    } catch (error: unknown) {
      logger.error('测试转换失败:', error as Error);
      return { success: false, message: extractErrorDetail(error, 'Unknown error'), system_ready: false };
    }
  }

  /** 健康检查 */
  async healthCheck(): Promise<{
    status: string; components: Record<string, boolean>; timestamp: string;
  }> {
    try {
      await apiClient.get(`${API_BASE_URL}/info`);
      return {
        status: 'healthy',
        components: { pdf_import: true, text_extraction: true, contract_validation: true },
        timestamp: new Date().toISOString(),
      };
    } catch (error: unknown) {
      logger.error('健康检查失败:', error as Error);
      return { status: 'unhealthy', components: {}, timestamp: new Date().toISOString() };
    }
  }

  /** 轮询进度 */
  async pollProgress(
    sessionId: string, onProgress: (progress: SessionProgress) => void, interval: number = 2000
  ): Promise<void> {
    const poll = async () => {
      try {
        const result = await this.getPdfImportProgress(sessionId);
        if (result.success && result.session_status) {
          onProgress(result.session_status);
          if (
            result.session_status.status !== 'ready_for_review' &&
            result.session_status.status !== 'failed' &&
            result.session_status.status !== 'cancelled'
          ) { setTimeout(poll, interval); }
        }
      } catch (error: unknown) { logger.error('轮询进度失败:', error as Error); }
    };
    poll();
  }

  formatFileSize(bytes: number): string { return _formatFileSize(bytes); }
  validateFileType(file: File): boolean { return _validateFileType(file); }
  validateFileSize(file: File, maxSizeMB: number = 50): boolean { return _validateFileSize(file, maxSizeMB); }
  estimateProcessingTime(fileSize: number): string { return _estimateProcessingTime(fileSize); }

  // === PDF导入扩展功能 ===

  /** 获取系统信息 */
  async getPdfImportSystemInfo(): Promise<SystemInfoResponse> {
    try {
      const response = await apiClient.get<SystemInfoResponse>(`${PROCESSING_API_BASE}/info`);
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      logger.error('获取系统信息失败:', error as Error);
      return { success: false, message: '获取系统信息失败', capabilities: {
        pdfplumber_available: false, pymupdf_available: false, spacy_available: false,
        vision_available: false, supported_formats: [], max_file_size_mb: 0,
        estimated_processing_time: '未知',
      } };
    }
  }

  /** 上传PDF文件并开始处理 */
  async uploadPdfFileWithOptions(
    file: File, processingOptions: Partial<ProcessingOptions> = {}, signal?: AbortSignal
  ): Promise<PdfImportFileUploadResponse> {
    const defaultOptions: ProcessingOptions = {
      force_method: 'smart', enable_chinese_optimization: true,
      enable_table_detection: true, enable_seal_detection: true,
      confidence_threshold: 0.7, use_template_learning: true,
      enable_multi_engine_fusion: true, enable_semantic_validation: true,
      ...processingOptions,
    } as ProcessingOptions;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_options', JSON.stringify(defaultOptions));
    if (defaultOptions.force_method != null) formData.append('force_method', defaultOptions.force_method);

    try {
      const response = await apiClient.post<PdfImportFileUploadResponse>(
        `${PROCESSING_API_BASE}/upload`, formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 600000,
          onUploadProgress: progressEvent => {
            if (progressEvent.total != null && progressEvent.total > 0) {
              Math.round((progressEvent.loaded * 100) / progressEvent.total);
            }
          },
          signal,
        }
      );
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      logger.error('PDF上传失败:', error as Error);
      return handleUploadError(error);
    }
  }

  /** 获取会话处理进度 */
  async getPdfImportProgress(sessionId: string): Promise<{
    success: boolean; session_status?: SessionProgress; error?: string;
  }> {
    try {
      const response = await apiClient.get<{
        success: boolean; session_status?: SessionProgress; error?: string;
      }>(`${PROCESSING_API_BASE}/progress/${sessionId}`);
      if (!response.data) throw new Error('Empty response');
      return { ...response.data };
    } catch (error: unknown) {
      logger.error('获取进度失败:', error as Error);
      return { success: false, error: extractErrorCode(error) };
    }
  }

  /** 取消会话处理 */
  async cancelPdfImportSession(
    sessionId: string, reason: string = '用户取消处理'
  ): Promise<{ success: boolean; message: string; error?: string }> {
    try {
      const response = await apiClient.delete<{ success: boolean; message: string; error?: string }>(
        `${PROCESSING_API_BASE}/session/${sessionId}`, { params: { reason } }
      );
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      logger.error('取消会话失败:', error as Error);
      return { success: false, message: extractErrorDetail(error, '取消失败'), error: extractErrorCode(error) };
    }
  }

  /** 轮询进度（多引擎） */
  async pollPdfImportProgress(
    sessionId: string, onProgress: (progress: SessionProgress) => void, interval: number = 3000
  ): Promise<void> {
    const poll = async () => {
      try {
        const result = await this.getPdfImportProgress(sessionId);
        if (result.success && result.session_status) {
          onProgress(result.session_status);
          if (
            result.session_status.status !== 'ready_for_review' &&
            result.session_status.status !== 'failed' &&
            result.session_status.status !== 'cancelled'
          ) { setTimeout(poll, interval); }
        }
      } catch (error: unknown) { logger.error('轮询进度失败:', error as Error); }
    };
    poll();
  }

  /** 获取处理结果 */
  async getPdfImportResult(sessionId: string): Promise<{
    success: boolean; result?: CompleteResult; error?: string;
  }> {
    try {
      const progressResponse = await this.getPdfImportProgress(sessionId);
      if (progressResponse.success && progressResponse.session_status) {
        const session = progressResponse.session_status;
        if (session.status === 'ready_for_review' || session.status === 'completed') {
          return { success: true, result: buildCompleteResult(sessionId, session) };
        } else if (session.status === 'failed') {
          return { success: false, error: session.error_message ?? '处理失败' };
        }
        return { success: false, error: '处理尚未完成' };
      }
      return { success: false, error: progressResponse.error ?? '获取进度失败' };
    } catch (error: unknown) {
      console.error('获取处理结果失败:', error);
      return { success: false, error: extractErrorCode(error) };
    }
  }

  /** 测试功能 */
  async testPdfImportFeatures(): Promise<{
    success: boolean; message: string;
    test_results?: Array<{ name: string; status: string; message?: string; [key: string]: unknown }>;
    availability_rate?: number; system_ready?: boolean;
  }> {
    try {
      const response = await apiClient.get<{
        success: boolean; message: string;
        test_results?: Array<{ name: string; status: string; message?: string; [key: string]: unknown }>;
        availability_rate?: number; system_ready?: boolean;
      }>(`${PROCESSING_API_BASE}/test/all`);
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      console.error('测试功能失败:', error);
      return { success: false, message: extractErrorDetail(error, 'Unknown error'), system_ready: false };
    }
  }

  /** 健康检查（多引擎） */
  async pdfImportHealthCheck(): Promise<{
    status: string; components: Record<string, boolean>;
    health_score?: number; timestamp: string; error?: string;
  }> {
    try {
      const response = await apiClient.get<{
        status: string; components: Record<string, boolean>;
        health_score?: number; timestamp: string; error?: string;
      }>(`${PROCESSING_API_BASE}/health`);
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      console.error('健康检查失败:', error);
      return { status: 'unhealthy', components: {}, timestamp: new Date().toISOString(), error: extractErrorCode(error) };
    }
  }

  /** 获取性能摘要 */
  async getPerformanceSummary(): Promise<{
    success: boolean; message: string; data?: Record<string, unknown>;
  }> {
    try {
      const response = await apiClient.get<{
        success: boolean; message: string; data?: Record<string, unknown>;
      }>(`${PROCESSING_API_BASE}/performance/summary`);
      if (!response.data) throw new Error('Empty response');
      return response.data;
    } catch (error: unknown) {
      console.error('获取性能摘要失败:', error);
      return { success: false, message: extractErrorDetail(error, 'Unknown error'), data: undefined };
    }
  }

  estimatePdfImportProcessingTime(fileSize: number): string {
    return _estimatePdfImportProcessingTime(fileSize);
  }

  /** 检查功能可用性 */
  async checkPdfImportFeaturesAvailability(): Promise<{
    available: boolean; features: Record<string, boolean>; message: string;
  }> {
    try {
      const systemInfo = await this.getPdfImportSystemInfo();
      const features: Record<string, boolean> = {
        pdfplumber_available: Boolean(systemInfo.capabilities.pdfplumber_available),
        pymupdf_available: Boolean(systemInfo.capabilities.pymupdf_available),
        spacy_available: Boolean(systemInfo.capabilities.spacy_available),
        vision_available: Boolean(systemInfo.capabilities.vision_available),
      };
      const availableCount = Object.values(features).filter(Boolean).length;
      const available = availableCount >= Object.keys(features).length * 0.8;
      return { available, features, message: available ? '功能可用' : '部分功能不可用' };
    } catch (error: unknown) {
      console.error('检查功能可用性失败:', error);
      return { available: false, features: {}, message: '无法检查功能可用性' };
    }
  }
}

// 创建单例实例
export const pdfImportService = new PDFImportService();
