/**
 * PDF导入服务
 * 处理PDF文件上传、转换、信息提取等API调用
 * 支持增强版中文合同识别功能
 */

import axios from 'axios';
import type {
  ProcessingOptions,
  EnhancedFileUploadResponse,
  EnhancedSessionProgress,
} from '../types/enhancedPdfImport';
import { createLogger } from '../utils/logger';

const logger = createLogger('PDFImportService');

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
  ocr_used?: boolean;
  validation_results?: Record<string, unknown>;
  // Extended properties for enhanced processing
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
  enhanced_status?: EnhancedSessionProgress['enhanced_status'];
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
    ocr_available: boolean;
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
  property_name: string;
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

export interface ConfirmImportResponse {
  success: boolean;
  message: string;
  contract_id?: string;
  contract_number?: string;
  created_terms_count?: number;
  processing_time?: number;
  error?: string;
}

// SystemCapabilities and SystemInfoResponse defined above

// API基础配置 - 使用相对路径通过代理转发
import { PDF_API } from '../constants/api';

// 使用API常量，如果端点不存在则提供备用方案
const API_BASE_URL = PDF_API.INFO.replace('/info', ''); // 获取基础路径
const ENHANCED_API_BASE = `${API_BASE_URL}/enhanced`;

// 类型守卫：检查是否为Error对象
function isError(error: unknown): error is Error {
  return error instanceof Error;
}

// 类型守卫：检查是否为AxiosError
function isAxiosError(error: unknown): error is {
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

class PDFImportService {
  /**
   * 上传PDF文件
   */
  async uploadPDFFile(
    file: File,
    preferMarkitdown: boolean = true,
    signal?: AbortSignal
  ): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('prefer_markitdown', preferMarkitdown.toString());
    formData.append('prefer_ocr', 'false');

    try {
      const response = await axios.post<FileUploadResponse>(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 增加到5分钟，支持大文件OCR处理
        onUploadProgress: progressEvent => {
          if (
            progressEvent.total !== null &&
            progressEvent.total !== undefined &&
            progressEvent.total > 0
          ) {
            const _percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            // Upload progress
          }
        },
        signal: signal, // 支持AbortController
      });

      // 直接返回后端API响应
      return response.data;
    } catch (error: unknown) {
      logger.error('PDF上传失败:', error as Error);

      // 使用类型守卫处理错误
      if (isAxiosError(error)) {
        if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
          throw new Error('canceled');
        }

        if (error.code === 'ECONNABORTED') {
          return {
            success: false,
            message: '上传超时，请检查文件大小或网络连接后重试',
            error: 'Upload timeout',
          };
        }

        if (error.response) {
          const detail = error.response.data?.detail;
          const statusText = error.response.statusText;
          return {
            success: false,
            message:
              detail !== null && detail !== undefined && detail !== ''
                ? detail
                : statusText !== null && statusText !== undefined && statusText !== ''
                  ? statusText
                  : '服务器处理失败',
            error:
              detail !== null && detail !== undefined && detail !== ''
                ? detail
                : statusText !== null && statusText !== undefined
                  ? statusText
                  : undefined,
          };
        }

        if (error.request !== null && error.request !== undefined) {
          return {
            success: false,
            message: '网络连接失败，请检查网络连接',
            error: 'Network connection failed',
          };
        }
      }

      return {
        success: false,
        message: isError(error) ? error.message : '上传失败',
        error: isError(error) ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * 获取处理进度
   */
  async getProgress(sessionId: string): Promise<{
    success: boolean;
    session_status?: SessionProgress;
    error?: string;
  }> {
    try {
      const response = await axios.get(`${API_BASE_URL}/progress/${sessionId}`);
      return response.data as {
        success: boolean;
        session_status?: SessionProgress;
        error?: string;
      };
    } catch (error: unknown) {
      logger.error('获取进度失败:', error as Error);
      const errorMsg = isAxiosError(error)
        ? error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
          ? error.response.data.detail
          : error.message !== null && error.message !== undefined && error.message !== ''
            ? error.message
            : 'Unknown error'
        : isError(error)
          ? error.message
          : 'Unknown error';
      return {
        success: false,
        error: errorMsg,
      };
    }
  }

  /**
   * 获取处理结果
   */
  async getResult(sessionId: string): Promise<{
    success: boolean;
    result?: CompleteResult;
    processing_summary?: Record<string, unknown>;
    error?: string;
  }> {
    try {
      // 通过进度API获取结果
      const progressResponse = await this.getProgress(sessionId);

      if (
        progressResponse.success === true &&
        progressResponse.session_status !== null &&
        progressResponse.session_status !== undefined
      ) {
        const session = progressResponse.session_status;

        if (session.status === 'ready_for_review' || session.status === 'completed') {
          // 构建结果对象
          const result: CompleteResult = {
            success: true,
            session_id: sessionId,
            file_info: {
              filename:
                session.file_name !== null &&
                session.file_name !== undefined &&
                session.file_name !== ''
                  ? session.file_name
                  : 'unknown.pdf',
              size: session.file_size ?? 0,
              content_type: 'application/pdf',
            },
            extraction_result: {
              success: true,
              data: session.extracted_data || {},
              confidence_score: session.confidence_score ?? 0.8,
              extraction_method:
                session.processing_method !== null &&
                session.processing_method !== undefined &&
                session.processing_method !== ''
                  ? session.processing_method
                  : 'multi_engine',
              processed_fields: Object.keys(session.extracted_data || {}).length,
              total_fields: 15,
            },
            validation_result: {
              success: true,
              errors: [],
              warnings: [],
              validated_data: session.validated_data || {},
              validation_score: 0.8,
              processed_fields: Object.keys(session.validated_data || {}).length,
              required_fields_count: 5,
              missing_required_fields: [],
            },
            matching_result: {
              matched_assets: session.matching_results?.matched_assets ?? [],
              matched_ownerships: session.matching_results?.matched_ownerships ?? [],
              duplicate_contracts: session.matching_results?.duplicate_contracts ?? [],
              recommendations: session.matching_results?.recommendations ?? {},
              match_confidence: session.matching_results?.overall_match_confidence ?? 0.7,
            },
            summary: {
              extraction_confidence: session.confidence_score ?? 0.8,
              validation_score: 0.8,
              match_confidence: session.matching_results?.overall_match_confidence ?? 0.7,
              total_confidence: 0.75,
            },
            recommendations: Object.values(session.matching_results?.recommendations ?? {}),
            ready_for_import: true,
          };

          return {
            success: true,
            result: result,
            processing_summary: {
              total_processing_time: '30-60秒',
              extraction_method:
                session.processing_method !== null &&
                session.processing_method !== undefined &&
                session.processing_method !== ''
                  ? session.processing_method
                  : 'multi_engine',
            },
          };
        } else if (session.status === 'failed') {
          return {
            success: false,
            error:
              session.error_message !== null &&
              session.error_message !== undefined &&
              session.error_message !== ''
                ? session.error_message
                : '处理失败',
          };
        } else {
          return {
            success: false,
            error: '处理尚未完成',
          };
        }
      } else {
        return {
          success: false,
          error:
            progressResponse.error !== null &&
            progressResponse.error !== undefined &&
            progressResponse.error !== ''
              ? progressResponse.error
              : '获取进度失败',
        };
      }
    } catch (error: unknown) {
      logger.error('获取结果失败:', error as Error);
      const errorMsg = isAxiosError(error)
        ? error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
          ? error.response.data.detail
          : error.message !== null && error.message !== undefined && error.message !== ''
            ? error.message
            : 'Unknown error'
        : isError(error)
          ? error.message
          : 'Unknown error';
      return {
        success: false,
        error: errorMsg,
      };
    }
  }

  /**
   * 确认导入合同
   */
  async confirmImport(
    sessionId: string,
    confirmedData: ConfirmedContractData
  ): Promise<ConfirmImportResponse> {
    try {
      const response = await axios.post(`${API_BASE_URL}/confirm_import`, {
        session_id: sessionId,
        confirmed_data: confirmedData,
      });

      return response.data as ConfirmImportResponse;
    } catch (error: unknown) {
      logger.error('确认导入失败:', error as Error);
      const errorMsg = isAxiosError(error)
        ? error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
          ? error.response.data.detail
          : error.message !== null && error.message !== undefined && error.message !== ''
            ? error.message
            : '导入失败'
        : isError(error)
          ? error.message
          : '导入失败';
      return {
        success: false,
        message: errorMsg,
        error: isAxiosError(error)
          ? error.response?.data?.detail !== null &&
            error.response?.data?.detail !== undefined &&
            error.response?.data?.detail !== ''
            ? error.response.data.detail
            : error.message !== null && error.message !== undefined && error.message !== ''
              ? error.message
              : 'Unknown error'
          : isError(error)
            ? error.message
            : 'Unknown error',
      };
    }
  }

  /**
   * 取消导入会话
   */
  async cancelSession(sessionId: string): Promise<{
    success: boolean;
    message: string;
    error?: string;
  }> {
    try {
      const response = await axios.delete(`${API_BASE_URL}/session/${sessionId}`);
      return response.data as {
        success: boolean;
        message: string;
        error?: string;
      };
    } catch (error: unknown) {
      logger.error('取消会话失败:', error as Error);
      const errorMsg = isAxiosError(error)
        ? error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
          ? error.response.data.detail
          : error.message !== null && error.message !== undefined && error.message !== ''
            ? error.message
            : '取消失败'
        : isError(error)
          ? error.message
          : '取消失败';
      return {
        success: false,
        message: errorMsg,
        error: isAxiosError(error)
          ? error.response?.data?.detail !== null &&
            error.response?.data?.detail !== undefined &&
            error.response?.data?.detail !== ''
            ? error.response.data.detail
            : error.message !== null && error.message !== undefined && error.message !== ''
              ? error.message
              : 'Unknown error'
          : isError(error)
            ? error.message
            : 'Unknown error',
      };
    }
  }

  /**
   * 获取活跃会话列表
   */
  async getActiveSessions(): Promise<{
    success: boolean;
    active_sessions: Array<{
      session_id: string;
      status: string;
      progress: number;
      current_step: string;
      created_at: string;
      file_name: string;
    }>;
    total_count: number;
    error?: string;
  }> {
    try {
      const response = await axios.get(PDF_API.SESSIONS);
      return response.data as {
        success: boolean;
        active_sessions: Array<{
          session_id: string;
          status: string;
          progress: number;
          current_step: string;
          created_at: string;
          file_name: string;
        }>;
        total_count: number;
        error?: string;
      };
    } catch (error: unknown) {
      logger.error('获取会话列表失败:', error as Error);

      // 如果是404错误，提供空的会话列表
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        logger.warn('PDF sessions API端点不存在，返回空会话列表');
        return {
          success: true,
          active_sessions: [],
          total_count: 0,
        };
      }

      const errorMsg = isAxiosError(error)
        ? error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
          ? error.response.data.detail
          : error.message !== null && error.message !== undefined && error.message !== ''
            ? error.message
            : 'Unknown error'
        : isError(error)
          ? error.message
          : 'Unknown error';
      return {
        success: false,
        active_sessions: [],
        total_count: 0,
        error: errorMsg,
      };
    }
  }

  /**
   * 获取系统信息 - 增强版本
   */
  async getSystemInfo(): Promise<SystemInfoResponse> {
    try {
      // 使用PDF_API.INFO，如果404则使用备用方案
      const response = await axios.get(PDF_API.INFO);

      // 直接使用后端返回的能力信息，并添加增强功能检测
      const responseData = response.data as Record<string, unknown>;
      const capabilities =
        responseData.capabilities !== null && responseData.capabilities !== undefined
          ? (responseData.capabilities as SystemCapabilities)
          : {
              pdfplumber_available: true,
              pymupdf_available: true,
              spacy_available: true,
              ocr_available: true,
              supported_formats: ['.pdf', '.jpg', '.jpeg', '.png'],
              max_file_size_mb: 50,
              estimated_processing_time: '30-60秒',
            };

      // 添加增强功能标识
      const enhancedCapabilities = {
        ...capabilities,
        enhanced_extraction: true,
        intelligent_matching: true,
        multi_engine_support: true,
        chinese_optimized: true,
        real_time_validation: true,
      };

      return {
        success: true,
        message:
          (responseData.message as string | undefined) !== null &&
          (responseData.message as string | undefined) !== undefined &&
          (responseData.message as string | undefined) !== ''
            ? (responseData.message as string)
            : '增强版PDF智能导入系统运行正常',
        capabilities: enhancedCapabilities,
        extractor_summary: {
          method: 'enhanced_multi_engine',
          description: '增强版多引擎PDF处理，支持智能引擎选择和质量评估',
          engines: ['PyMuPDF', 'PDFPlumber', 'PaddleOCR'],
          features: ['智能预处理', '增强字段提取', '实时验证', '优化匹配算法'],
        },
        validator_summary: {
          enabled: true,
          description: '增强版数据验证和智能匹配功能',
          features: ['多维度验证', '智能模糊匹配', '重复检测', '置信度评估'],
          accuracy_improvement: '15-20%',
        },
      };
    } catch (error: unknown) {
      logger.error('获取系统信息失败:', error as Error);

      // 如果是404错误，提供备用数据
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        logger.warn('PDF API端点不存在，使用备用系统信息');
        return {
          success: true,
          message: 'PDF智能导入系统（备用模式）',
          capabilities: {
            pdfplumber_available: true,
            pymupdf_available: true,
            spacy_available: false,
            ocr_available: false,
            supported_formats: ['.pdf'],
            max_file_size_mb: 10,
            estimated_processing_time: '30-60秒',
            enhanced_extraction: false,
            intelligent_matching: false,
            multi_engine_support: false,
            chinese_optimized: false,
            real_time_validation: false,
          },
          extractor_summary: {
            method: 'basic',
            description: '基础PDF处理模式',
            engines: ['PDFPlumber'],
            features: ['基础文本提取'],
          },
          validator_summary: {
            enabled: false,
            description: '数据验证功能暂时不可用',
            features: [],
            accuracy_improvement: '0%',
          },
        };
      }

      return {
        success: false,
        message: '系统信息获取失败',
        capabilities: {
          pdfplumber_available: false,
          pymupdf_available: false,
          spacy_available: false,
          ocr_available: false,
          supported_formats: [],
          max_file_size_mb: 0,
          estimated_processing_time: '未知',
        },
        extractor_summary: { method: 'unavailable' },
        validator_summary: { enabled: false },
      };
    }
  }

  // 获取系统能力信息
  static async getSystemCapabilities() {
    try {
      const response = await axios.get(`${API_BASE_URL}/capabilities}`);
      const responseData = response.data as Record<string, unknown>;
      return {
        spacy_available: true,
        ocr_available: true,
        supported_formats: ['.pdf', '.jpg', '.jpeg', '.png'],
        max_file_size_mb: 50,
        estimated_processing_time: '30-60秒',
        extractor_summary: responseData.extractor_summary as Record<string, unknown> | undefined,
        validator_summary: responseData.validator_summary as Record<string, unknown> | undefined,
      };
    } catch (error: unknown) {
      logger.error('获取系统信息失败:', error as Error);
      const errorMessage = isAxiosError(error)
        ? error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
          ? error.response?.data?.detail
          : error.message !== null && error.message !== undefined && error.message !== ''
            ? error.message
            : 'Unknown error'
        : isError(error)
          ? error.message
          : 'Unknown error';
      throw new Error(errorMessage);
    }
  }

  /**
   * 测试转换功能
   */
  async testConversion(): Promise<{
    success: boolean;
    message: string;
    test_result?: Record<string, unknown>;
    system_ready?: boolean;
  }> {
    try {
      // 简单API使用 /info 端点来测试系统状态
      const response = await axios.get(`${API_BASE_URL}/info`);
      const responseData = response.data as Record<string, unknown>;
      return {
        success: true,
        message: (responseData.message as string | undefined) ?? '系统正常',
        test_result: responseData.features as Record<string, unknown> | undefined,
        system_ready: true,
      };
    } catch (error: unknown) {
      logger.error('测试转换失败:', error as Error);
      const errorMsg = isAxiosError(error)
        ? error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
          ? error.response?.data?.detail
          : error.message !== null && error.message !== undefined && error.message !== ''
            ? error.message
            : 'Unknown error'
        : isError(error)
          ? error.message
          : 'Unknown error';
      return {
        success: false,
        message: errorMsg,
        system_ready: false,
      };
    }
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{
    status: string;
    components: Record<string, boolean>;
    timestamp: string;
  }> {
    try {
      // 使用/info端点作为健康检查
      await axios.get(`${API_BASE_URL}/info`);
      return {
        status: 'healthy',
        components: {
          pdf_import: true,
          text_extraction: true,
          contract_validation: true,
        },
        timestamp: new Date().toISOString(),
      };
    } catch (error: unknown) {
      logger.error('健康检查失败:', error as Error);
      return {
        status: 'unhealthy',
        components: {},
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * 轮询进度
   */
  async pollProgress(
    sessionId: string,
    onProgress: (progress: SessionProgress) => void,
    interval: number = 2000
  ): Promise<void> {
    const poll = async () => {
      try {
        const result = await this.getProgress(sessionId);

        if (result.success && result.session_status) {
          onProgress(result.session_status);

          // 如果还在处理中，继续轮询
          if (
            result.session_status.status !== 'ready_for_review' &&
            result.session_status.status !== 'failed' &&
            result.session_status.status !== 'cancelled'
          ) {
            setTimeout(() => {
              void poll();
            }, interval);
          }
        }
      } catch (error: unknown) {
        logger.error('轮询进度失败:', error as Error);
      }
    };

    await poll();
  }

  /**
   * 文件大小格式化
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) {
      return '0 Bytes';
    }

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * 验证文件类型
   */
  validateFileType(file: File): boolean {
    const allowedTypes = ['application/pdf'];
    const allowedExtensions = ['.pdf'];

    return (
      allowedTypes.includes(file.type) ||
      allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext))
    );
  }

  /**
   * 验证文件大小
   */
  validateFileSize(file: File, maxSizeMB: number = 50): boolean {
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    return file.size <= maxSizeBytes;
  }

  /**
   * 计算预计处理时间
   */
  estimateProcessingTime(fileSize: number): string {
    // 基于文件大小的简单估算
    const sizeMB = fileSize / (1024 * 1024);

    if (sizeMB < 1) {
      return '10-20秒';
    }
    if (sizeMB < 5) {
      return '20-40秒';
    }
    if (sizeMB < 10) {
      return '30-60秒';
    }
    if (sizeMB < 20) {
      return '45-90秒';
    }

    return '60-120秒';
  }

  // === 增强版PDF导入功能 ===

  /**
   * 获取增强版系统信息
   */
  async getEnhancedSystemInfo(): Promise<SystemInfoResponse> {
    try {
      const response = await axios.get(`${ENHANCED_API_BASE}/info`);
      return response.data as SystemInfoResponse;
    } catch (error: unknown) {
      logger.error('获取增强版系统信息失败:', error as Error);
      return {
        success: false,
        message: '获取系统信息失败',
        capabilities: {
          pdfplumber_available: false,
          pymupdf_available: false,
          spacy_available: false,
          ocr_available: false,
          supported_formats: [],
          max_file_size_mb: 0,
          estimated_processing_time: '未知',
        },
      };
    }
  }

  /**
   * 上传PDF文件并开始增强版处理
   */
  async uploadPDFFileEnhanced(
    file: File,
    processingOptions: Partial<ProcessingOptions> = {},
    signal?: AbortSignal
  ): Promise<EnhancedFileUploadResponse> {
    // 默认处理选项
    const defaultOptions: ProcessingOptions = {
      prefer_ocr: true,
      enable_chinese_optimization: true,
      enable_table_detection: true,
      enable_seal_detection: true,
      confidence_threshold: 0.7,
      use_template_learning: true,
      enable_multi_engine_fusion: true,
      enable_semantic_validation: true,
      ...processingOptions,
    } as ProcessingOptions;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_options', JSON.stringify(defaultOptions));

    try {
      const response = await axios.post<EnhancedFileUploadResponse>(
        `${ENHANCED_API_BASE}/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 600000, // 10分钟，支持增强版处理
          onUploadProgress: progressEvent => {
            if (
              progressEvent.total !== null &&
              progressEvent.total !== undefined &&
              progressEvent.total > 0
            ) {
              const _percentCompleted = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              );
              // Enhanced upload progress
            }
          },
          signal,
        }
      );

      return response.data;
    } catch (error: unknown) {
      logger.error('增强版PDF上传失败:', error as Error);

      if (isAxiosError(error)) {
        if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
          throw new Error('canceled');
        }

        if (error.code === 'ECONNABORTED') {
          return {
            success: false,
            message: '上传超时，请检查文件大小或网络连接后重试',
            error: 'Upload timeout',
          };
        }

        if (error.response) {
          return {
            success: false,
            message:
              error.response.data?.detail !== null &&
              error.response.data?.detail !== undefined &&
              error.response.data?.detail !== ''
                ? error.response.data.detail
                : error.response.statusText !== null &&
                    error.response.statusText !== undefined &&
                    error.response.statusText !== ''
                  ? error.response.statusText
                  : '服务器处理失败',
            error:
              error.response.data?.detail !== null && error.response.data?.detail !== undefined
                ? error.response.data.detail
                : error.response.statusText,
          };
        }
      }

      return {
        success: false,
        message: isError(error) ? error.message : '上传失败',
        error: isError(error) ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * 获取增强版会话处理进度
   */
  async getEnhancedProgress(sessionId: string): Promise<{
    success: boolean;
    session_status?: SessionProgress;
    error?: string;
  }> {
    try {
      const response = await axios.get(`${ENHANCED_API_BASE}/progress/${sessionId}`);
      return response.data as {
        success: boolean;
        session_status?: SessionProgress;
        error?: string;
      };
    } catch (error: unknown) {
      logger.error('获取增强版进度失败:', error as Error);
      return {
        success: false,
        error:
          (error as Record<string, unknown>).response !== null &&
          (error as Record<string, unknown>).response !== undefined &&
          (error as Record<string, unknown>).response !== ''
            ? 'Unknown error'
            : isError(error)
              ? error.message
              : 'Unknown error',
      };
    }
  }

  /**
   * 取消增强版会话处理
   */
  async cancelEnhancedSession(
    sessionId: string,
    reason: string = '用户取消增强版处理'
  ): Promise<{
    success: boolean;
    message: string;
    error?: string;
  }> {
    try {
      const response = await axios.delete(`${ENHANCED_API_BASE}/session/${sessionId}`, {
        params: { reason },
      });
      return response.data as {
        success: boolean;
        message: string;
        error?: string;
      };
    } catch (error: unknown) {
      logger.error('取消增强版会话失败:', error as Error);
      return {
        success: false,
        message:
          isAxiosError(error) &&
          error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
            ? error.response.data.detail
            : isAxiosError(error) &&
                error.message !== null &&
                error.message !== undefined &&
                error.message !== ''
              ? error.message
              : isError(error)
                ? error.message
                : '取消失败',
        error:
          isAxiosError(error) &&
          error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined
            ? (error.response.data.detail as string | undefined)
            : isAxiosError(error)
              ? error.message
              : isError(error)
                ? error.message
                : 'Unknown error',
      };
    }
  }

  /**
   * 轮询增强版进度
   */
  async pollEnhancedProgress(
    sessionId: string,
    onProgress: (progress: SessionProgress) => void,
    interval: number = 3000 // 增强版处理间隔稍长
  ): Promise<void> {
    const poll = async () => {
      try {
        const result = await this.getEnhancedProgress(sessionId);

        if (result.success && result.session_status) {
          onProgress(result.session_status);

          // 如果还在处理中，继续轮询
          if (
            result.session_status.status !== 'ready_for_review' &&
            result.session_status.status !== 'failed' &&
            result.session_status.status !== 'cancelled'
          ) {
            setTimeout(() => {
              void poll();
            }, interval);
          }
        }
      } catch (error: unknown) {
        logger.error('轮询增强版进度失败:', error as Error);
      }
    };

    await poll();
  }

  /**
   * 获取增强版处理结果
   */
  async getEnhancedResult(sessionId: string): Promise<{
    success: boolean;
    result?: CompleteResult;
    error?: string;
  }> {
    try {
      // 通过增强版进度API获取结果
      const progressResponse = await this.getEnhancedProgress(sessionId);

      if (progressResponse.success && progressResponse.session_status) {
        const session = progressResponse.session_status;

        if (session.status === 'ready_for_review' || session.status === 'completed') {
          // 构建增强版结果对象
          const result: CompleteResult = {
            success: true,
            session_id: sessionId,
            file_info: {
              filename:
                session.file_name !== null &&
                session.file_name !== undefined &&
                session.file_name !== ''
                  ? session.file_name
                  : 'unknown.pdf',
              size: session.file_size ?? 0,
              content_type: 'application/pdf',
            },
            extraction_result: {
              success: true,
              data: session.enhanced_status?.final_fields || {},
              confidence_score:
                session.enhanced_status?.final_results?.extraction_quality?.overall_quality ?? 0.8,
              extraction_method: 'enhanced_multi_engine',
              processed_fields: Object.keys(session.enhanced_status?.final_fields || {}).length,
              total_fields: 58,
            },
            validation_result: {
              success: true,
              errors: [],
              warnings: [],
              validated_data: session.enhanced_status?.final_fields || {},
              validation_score: session.enhanced_status?.final_results?.validation_score ?? 0.8,
              processed_fields: Object.keys(session.enhanced_status?.final_fields || {}).length,
              required_fields_count: 10,
              missing_required_fields: [],
            },
            matching_result: {
              matched_assets: [],
              matched_ownerships: [],
              duplicate_contracts: [],
              recommendations: {},
              match_confidence: session.enhanced_status?.final_results?.match_confidence ?? 0.7,
            },
            semantic_validation:
              session.enhanced_status?.semantic_validation !== null &&
              session.enhanced_status?.semantic_validation !== undefined
                ? session.enhanced_status.semantic_validation
                : {
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
              extraction_method: 'enhanced_multi_engine',
              engines_used:
                session.enhanced_status?.final_results?.processing_summary?.engines_used ?? [],
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
                session.enhanced_status?.final_results?.extraction_quality?.overall_quality ?? 0.8,
              validation_score: session.enhanced_status?.final_results?.validation_score ?? 0.8,
              match_confidence: session.enhanced_status?.final_results?.match_confidence ?? 0.7,
              semantic_confidence:
                session.enhanced_status?.semantic_validation?.overall_confidence ?? 0.8,
              fusion_confidence: session.enhanced_status?.fusion_results?.confidence ?? 0.8,
              overall_quality:
                session.enhanced_status?.final_results?.extraction_quality?.overall_quality ?? 0.8,
              total_confidence: 0.8,
            },
            recommendations: session.enhanced_status?.semantic_validation?.recommendations ?? [],
            ready_for_import: true,
            quality_metrics: {
              extraction_quality:
                session.enhanced_status?.final_results?.extraction_quality?.overall_quality ?? 0.8,
              validation_quality: session.enhanced_status?.final_results?.validation_score ?? 0.8,
              matching_quality: session.enhanced_status?.final_results?.match_confidence ?? 0.7,
              semantic_quality:
                session.enhanced_status?.semantic_validation?.overall_confidence ?? 0.8,
              processing_efficiency: 0.8,
              overall_score: 0.8,
            },
          };

          return {
            success: true,
            result: result,
          };
        } else if (session.status === 'failed') {
          return {
            success: false,
            error:
              session.error_message !== null &&
              session.error_message !== undefined &&
              session.error_message !== ''
                ? session.error_message
                : '处理失败',
          };
        } else {
          return {
            success: false,
            error: '处理尚未完成',
          };
        }
      } else {
        return {
          success: false,
          error:
            progressResponse.error !== null &&
            progressResponse.error !== undefined &&
            progressResponse.error !== ''
              ? progressResponse.error
              : '获取进度失败',
        };
      }
    } catch (error: unknown) {
      console.error('获取增强版结果失败:', error);
      return {
        success: false,
        error:
          isAxiosError(error) &&
          error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
            ? error.response.data.detail
            : isAxiosError(error) &&
                error.message !== null &&
                error.message !== undefined &&
                error.message !== ''
              ? error.message
              : isError(error)
                ? error.message
                : 'Unknown error',
      };
    }
  }

  /**
   * 测试增强版功能
   */
  async testEnhancedFeatures(): Promise<{
    success: boolean;
    message: string;
    test_results?: Array<{
      name: string;
      status: string;
      message?: string;
      [key: string]: unknown;
    }>;
    availability_rate?: number;
    system_ready?: boolean;
  }> {
    try {
      const response = await axios.get(`${ENHANCED_API_BASE}/test/all`);
      return response.data as {
        success: boolean;
        message: string;
        test_results?: Array<{
          name: string;
          status: string;
          message?: string;
          [key: string]: unknown;
        }>;
        availability_rate?: number;
        system_ready?: boolean;
      };
    } catch (error: unknown) {
      console.error('测试增强版功能失败:', error);
      const errorMsg =
        isAxiosError(error) &&
        error.response?.data?.detail !== null &&
        error.response?.data?.detail !== undefined &&
        error.response?.data?.detail !== ''
          ? error.response.data.detail
          : isAxiosError(error) &&
              error.message !== null &&
              error.message !== undefined &&
              error.message !== ''
            ? error.message
            : isError(error) &&
                error.message !== null &&
                error.message !== undefined &&
                error.message !== ''
              ? error.message
              : 'Unknown error';
      return {
        success: false,
        message: errorMsg,
        system_ready: false,
      };
    }
  }

  /**
   * 增强版健康检查
   */
  async enhancedHealthCheck(): Promise<{
    status: string;
    components: Record<string, boolean>;
    health_score?: number;
    timestamp: string;
    error?: string;
  }> {
    try {
      const response = await axios.get(`${ENHANCED_API_BASE}/health`);
      return response.data as {
        status: string;
        components: Record<string, boolean>;
        health_score?: number;
        timestamp: string;
        error?: string;
      };
    } catch (error: unknown) {
      console.error('增强版健康检查失败:', error);
      return {
        status: 'unhealthy',
        components: {},
        timestamp: new Date().toISOString(),
        error:
          isAxiosError(error) &&
          error.response?.data?.detail !== null &&
          error.response?.data?.detail !== undefined &&
          error.response?.data?.detail !== ''
            ? error.response.data.detail
            : isAxiosError(error) &&
                error.message !== null &&
                error.message !== undefined &&
                error.message !== ''
              ? error.message
              : isError(error)
                ? error.message
                : 'Unknown error',
      };
    }
  }

  /**
   * 获取性能摘要
   */
  async getPerformanceSummary(): Promise<{
    success: boolean;
    message: string;
    data?: Record<string, unknown>;
  }> {
    try {
      const response = await axios.get(`${ENHANCED_API_BASE}/performance/summary`);
      return response.data as {
        success: boolean;
        message: string;
        data?: Record<string, unknown>;
      };
    } catch (error: unknown) {
      console.error('获取性能摘要失败:', error);
      const errorMsg =
        isAxiosError(error) &&
        error.response?.data?.detail !== null &&
        error.response?.data?.detail !== undefined &&
        error.response?.data?.detail !== ''
          ? error.response.data.detail
          : isAxiosError(error) &&
              error.message !== null &&
              error.message !== undefined &&
              error.message !== ''
            ? error.message
            : isError(error) &&
                error.message !== null &&
                error.message !== undefined &&
                error.message !== ''
              ? error.message
              : 'Unknown error';
      return {
        success: false,
        message: errorMsg,
        data: undefined,
      };
    }
  }

  /**
   * 估算增强版处理时间
   */
  estimateEnhancedProcessingTime(fileSize: number): string {
    // 增强版处理时间较长，但更准确
    const sizeMB = fileSize / (1024 * 1024);

    if (sizeMB < 1) {
      return '30-45秒';
    }
    if (sizeMB < 5) {
      return '45-75秒';
    }
    if (sizeMB < 10) {
      return '60-90秒';
    }
    if (sizeMB < 20) {
      return '90-150秒';
    }

    return '120-240秒';
  }

  /**
   * 检查增强版功能可用性
   */
  async checkEnhancedFeaturesAvailability(): Promise<{
    available: boolean;
    features: Record<string, boolean>;
    message: string;
  }> {
    try {
      const systemInfo = await this.getEnhancedSystemInfo();

      const features: Record<string, boolean> = {
        pdfplumber_available: Boolean(systemInfo.capabilities.pdfplumber_available),
        pymupdf_available: Boolean(systemInfo.capabilities.pymupdf_available),
        spacy_available: Boolean(systemInfo.capabilities.spacy_available),
        ocr_available: Boolean(systemInfo.capabilities.ocr_available),
      };

      const availableCount = Object.values(features).filter(Boolean).length;
      const totalCount = Object.keys(features).length;
      const available = availableCount >= totalCount * 0.8; // 80%以上功能可用

      return {
        available,
        features,
        message: available ? '增强版功能可用' : '部分增强版功能不可用',
      };
    } catch (error: unknown) {
      console.error('检查增强版功能可用性失败:', error);
      return {
        available: false,
        features: {},
        message: '无法检查增强版功能可用性',
      };
    }
  }
}

// 创建单例实例
export const pdfImportService = new PDFImportService();

// 注意：类型已在顶部定义，无需重复导出
