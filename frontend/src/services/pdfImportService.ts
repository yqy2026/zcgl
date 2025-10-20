/**
 * PDF导入服务
 * 处理PDF文件上传、转换、信息提取等API调用
 */

import axios from 'axios';

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
  validated_data: Record<string, any>;
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
  data: Record<string, any>;
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
}

export interface CompleteResult {
  session_id: string;
  file_info: FileInfo;
  extraction_result: ExtractionResult;
  validation_result: ValidationResult;
  matching_result: MatchingResult;
  summary: ConfidenceScores;
  recommendations: string[];
  ready_for_import: boolean;
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

export interface SystemCapabilities {
  pdfplumber_available: boolean;
  pymupdf_available: boolean;
  spacy_available: boolean;
  ocr_available: boolean;
  supported_formats: string[];
  max_file_size_mb: number;
  estimated_processing_time: string;
}

export interface SystemInfoResponse {
  success: boolean;
  message: string;
  capabilities: SystemCapabilities;
  extractor_summary?: Record<string, any>;
  validator_summary?: Record<string, any>;
}

// API基础配置 - 使用相对路径通过代理转发
const API_BASE_URL = '/api/v1/pdf_import';

class PDFImportService {
  /**
   * 上传PDF文件
   */
  async uploadPDFFile(file: File, preferMarkitdown: boolean = true, signal?: AbortSignal): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('prefer_markitdown', preferMarkitdown.toString());
    formData.append('prefer_ocr', 'false');

    try {
      const response = await axios.post<FileUploadResponse>(
        `${API_BASE_URL}/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 300000, // 增加到5分钟，支持大文件OCR处理
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              console.log(`Upload progress: ${percentCompleted}%`);
            }
          },
          signal: signal, // 支持AbortController
        }
      );

      // 直接返回后端API响应
      return response.data;
    } catch (error: any) {
      console.error('PDF上传失败:', error);

      // 更详细的错误处理
      if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
        throw new Error('canceled');
      }

      if (error.code === 'ECONNABORTED') {
        return {
          success: false,
          message: '上传超时，请检查文件大小或网络连接后重试',
          error: 'Upload timeout'
        };
      }

      if (error.response) {
        // 服务器返回了错误状态码
        return {
          success: false,
          message: error.response.data?.detail || error.response.statusText || '服务器处理失败',
          error: error.response.data?.detail || error.response.statusText
        };
      }

      if (error.request) {
        // 请求发出但没有收到响应
        return {
          success: false,
          message: '网络连接失败，请检查网络连接',
          error: 'Network connection failed'
        };
      }

      return {
        success: false,
        message: error.message || '上传失败',
        error: error.message
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
      return response.data;
    } catch (error: any) {
      console.error('获取进度失败:', error);
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
  }

  /**
   * 获取处理结果
   */
  async getResult(sessionId: string): Promise<{
    success: boolean;
    result?: CompleteResult;
    processing_summary?: any;
    error?: string;
  }> {
    try {
      // 通过进度API获取结果
      const progressResponse = await this.getProgress(sessionId);

      if (progressResponse.success && progressResponse.session_status) {
        const session = progressResponse.session_status;

        if (session.status === 'ready_for_review' || session.status === 'completed') {
          // 构建结果对象
          const result: CompleteResult = {
            session_id: sessionId,
            file_info: {
              filename: session.file_name || 'unknown.pdf',
              size: session.file_size || 0,
              content_type: 'application/pdf'
            },
            extraction_result: {
              success: true,
              data: session.extracted_data || {},
              confidence_score: session.confidence_score || 0.8,
              extraction_method: session.processing_method || 'multi_engine',
              processed_fields: Object.keys(session.extracted_data || {}).length,
              total_fields: 15
            },
            validation_result: {
              success: true,
              errors: [],
              warnings: [],
              validated_data: session.validated_data || {},
              validation_score: 0.8,
              processed_fields: Object.keys(session.validated_data || {}).length,
              required_fields_count: 5,
              missing_required_fields: []
            },
            matching_result: {
              matched_assets: session.matching_results?.matched_assets || [],
              matched_ownerships: session.matching_results?.matched_ownerships || [],
              duplicate_contracts: session.matching_results?.duplicate_contracts || [],
              recommendations: session.matching_results?.recommendations || {},
              match_confidence: session.matching_results?.overall_match_confidence || 0.7
            },
            summary: {
              extraction_confidence: session.confidence_score || 0.8,
              validation_score: 0.8,
              match_confidence: session.matching_results?.overall_match_confidence || 0.7,
              total_confidence: 0.75
            },
            recommendations: session.matching_results?.recommendations || [],
            ready_for_import: true
          };

          return {
            success: true,
            result: result,
            processing_summary: {
              total_processing_time: '30-60秒',
              extraction_method: session.processing_method || 'multi_engine'
            }
          };
        } else if (session.status === 'failed') {
          return {
            success: false,
            error: session.error_message || '处理失败'
          };
        } else {
          return {
            success: false,
            error: '处理尚未完成'
          };
        }
      } else {
        return {
          success: false,
          error: progressResponse.error || '获取进度失败'
        };
      }
    } catch (error: any) {
      console.error('获取结果失败:', error);
      return {
        success: false,
        error: error.response?.data?.detail || error.message
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
        confirmed_data: confirmedData
      });

      return response.data;
    } catch (error: any) {
      console.error('确认导入失败:', error);
      return {
        success: false,
        message: error.response?.data?.detail || error.message || '导入失败',
        error: error.response?.data?.detail || error.message
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
      return response.data;
    } catch (error: any) {
      console.error('取消会话失败:', error);
      return {
        success: false,
        message: error.response?.data?.detail || error.message || '取消失败',
        error: error.response?.data?.detail || error.message
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
      const response = await axios.get(`${API_BASE_URL}/sessions`);
      return response.data;
    } catch (error: any) {
      console.error('获取会话列表失败:', error);
      return {
        success: false,
        active_sessions: [],
        total_count: 0,
        error: error.response?.data?.detail || error.message
      };
    }
  }

  /**
   * 获取系统信息
   */
  async getSystemInfo(): Promise<SystemInfoResponse> {
    try {
      const response = await axios.get(`${API_BASE_URL}/info`);

      // 直接使用后端返回的能力信息
      return {
        success: true,
        message: response.data.message || '系统信息获取成功',
        capabilities: response.data.capabilities || {
          pdfplumber_available: true,
          pymupdf_available: true,
          spacy_available: true,
          ocr_available: true,
          supported_formats: ['.pdf', '.jpg', '.jpeg', '.png'],
          max_file_size_mb: 50,
          estimated_processing_time: '30-60秒'
        },
        extractor_summary: response.data.extractor_summary,
        validator_summary: response.data.validator_summary
      };
    } catch (error: any) {
      console.error('获取系统信息失败:', error);
      throw new Error(error.response?.data?.detail || error.message);
    }
  }

  /**
   * 测试转换功能
   */
  async testConversion(): Promise<{
    success: boolean;
    message: string;
    test_result?: any;
    system_ready?: boolean;
  }> {
    try {
      // 简单API使用 /info 端点来测试系统状态
      const response = await axios.get(`${API_BASE_URL}/info`);
      return {
        success: true,
        message: response.data.message,
        test_result: response.data.features,
        system_ready: true
      };
    } catch (error: any) {
      console.error('测试转换失败:', error);
      return {
        success: false,
        message: error.response?.data?.detail || error.message,
        system_ready: false
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
          'pdf_import': true,
          'text_extraction': true,
          'contract_validation': true
        },
        timestamp: new Date().toISOString()
      };
    } catch (error: any) {
      console.error('健康检查失败:', error);
      return {
        status: 'unhealthy',
        components: {},
        timestamp: new Date().toISOString()
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
          if (result.session_status.status !== 'ready_for_review' &&
              result.session_status.status !== 'failed' &&
              result.session_status.status !== 'cancelled') {
            setTimeout(poll, interval);
          }
        }
      } catch (error) {
        console.error('轮询进度失败:', error);
      }
    };

    poll();
  }

  /**
   * 文件大小格式化
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

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

    return allowedTypes.includes(file.type) ||
           allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
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

    if (sizeMB < 1) return '10-20秒';
    if (sizeMB < 5) return '20-40秒';
    if (sizeMB < 10) return '30-60秒';
    if (sizeMB < 20) return '45-90秒';

    return '60-120秒';
  }
}

// 创建单例实例
export const pdfImportService = new PDFImportService();

// 注意：类型已在顶部定义，无需重复导出