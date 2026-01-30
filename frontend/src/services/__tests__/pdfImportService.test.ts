/**
 * PDFImportService 单元测试
 *
 * 测试 PDF 导入服务的核心功能
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { pdfImportService, PDFImportService } from '../pdfImportService';

// Mock API client
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

import { apiClient } from '@/api/client';

describe('PDFImportService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==========================================================================
  // 文件上传测试
  // ==========================================================================

  describe('uploadPDFFile', () => {
    it('should upload PDF file successfully', async () => {
      const mockFile = new File(['test content'], 'test.pdf', {
        type: 'application/pdf',
      });

      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          success: true,
          message: '上传成功',
          session_id: 'session-123',
          estimated_time: '30-60秒',
        },
      });

      const result = await pdfImportService.uploadPDFFile(mockFile);

      expect(result.success).toBe(true);
      expect(result.session_id).toBe('session-123');
    });

    it('should handle upload timeout', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      const timeoutError = {
        code: 'ECONNABORTED',
        response: undefined,
        request: {},
      };

      vi.mocked(apiClient.post).mockRejectedValue(timeoutError);

      const result = await pdfImportService.uploadPDFFile(mockFile);

      expect(result.success).toBe(false);
      expect(result.message).toContain('超时');
    });

    it('should handle server error', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      vi.mocked(apiClient.post).mockRejectedValue({
        response: {
          data: { detail: '文件格式不支持' },
          status: 400,
        },
      });

      const result = await pdfImportService.uploadPDFFile(mockFile);

      expect(result.success).toBe(false);
      expect(result.message).toBe('文件格式不支持');
    });

    it('should handle network error', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      vi.mocked(apiClient.post).mockRejectedValue({
        request: {},
        response: undefined,
      });

      const result = await pdfImportService.uploadPDFFile(mockFile);

      expect(result.success).toBe(false);
      expect(result.message).toContain('网络');
    });

    it('should handle cancel error', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      vi.mocked(apiClient.post).mockRejectedValue({
        name: 'CanceledError',
        code: 'ERR_CANCELED',
      });

      await expect(pdfImportService.uploadPDFFile(mockFile)).rejects.toThrow('canceled');
    });
  });

  // ==========================================================================
  // 进度查询测试
  // ==========================================================================

  describe('getProgress', () => {
    it('should return session progress', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          success: true,
          session_status: {
            session_id: 'session-123',
            status: 'processing',
            progress: 50,
            current_step: '文本提取中',
          },
        },
      });

      const result = await pdfImportService.getProgress('session-123');

      expect(result.success).toBe(true);
      expect(result.session_status?.progress).toBe(50);
    });

    it('should handle error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      const result = await pdfImportService.getProgress('session-123');

      expect(result.success).toBe(false);
    });
  });

  // ==========================================================================
  // 结果获取测试
  // ==========================================================================

  describe('getResult', () => {
    it('should return completed result', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          success: true,
          session_status: {
            session_id: 'session-123',
            status: 'ready_for_review',
            progress: 100,
            file_name: 'contract.pdf',
            processing_status: {
              final_fields: {
                contract_number: 'HT-001',
                tenant_name: '测试租户',
              },
            },
          },
        },
      });

      const result = await pdfImportService.getResult('session-123');

      expect(result.success).toBe(true);
      expect(result.result).toBeDefined();
    });

    it('should handle failed status', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          success: true,
          session_status: {
            session_id: 'session-123',
            status: 'failed',
            error_message: '文件解析失败',
          },
        },
      });

      const result = await pdfImportService.getResult('session-123');

      expect(result.success).toBe(false);
      expect(result.error).toContain('失败');
    });
  });

  // ==========================================================================
  // 确认导入测试
  // ==========================================================================

  describe('confirmImport', () => {
    it('should confirm import successfully', async () => {
      const confirmedData = {
        contract_number: 'HT-001',
        tenant_name: '测试租户',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        monthly_rent_base: '10000',
        rent_terms: [],
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        data: {
          success: true,
          message: '导入成功',
          contract_id: 'contract-123',
          contract_number: 'HT-001',
        },
      });

      const result = await pdfImportService.confirmImport('session-123', confirmedData);

      expect(result.success).toBe(true);
      expect(result.contract_id).toBe('contract-123');
    });

    it('should handle import failure', async () => {
      vi.mocked(apiClient.post).mockRejectedValue({
        response: {
          data: { detail: '合同编号重复' },
        },
      });

      const result = await pdfImportService.confirmImport('session-123', {
        contract_number: 'HT-001',
        tenant_name: '测试',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        monthly_rent_base: '10000',
        rent_terms: [],
      });

      expect(result.success).toBe(false);
    });
  });

  // ==========================================================================
  // 会话管理测试
  // ==========================================================================

  describe('cancelSession', () => {
    it('should cancel session successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        data: {
          success: true,
          message: '会话已取消',
        },
      });

      const result = await pdfImportService.cancelSession('session-123');

      expect(result.success).toBe(true);
    });

    it('should handle cancel failure', async () => {
      vi.mocked(apiClient.delete).mockRejectedValue({
        response: {
          data: { detail: '会话不存在' },
        },
      });

      const result = await pdfImportService.cancelSession('session-999');

      expect(result.success).toBe(false);
    });
  });

  describe('getActiveSessions', () => {
    it('should return active sessions', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          success: true,
          active_sessions: [
            { session_id: 's1', status: 'processing', progress: 30 },
            { session_id: 's2', status: 'processing', progress: 60 },
          ],
          total_count: 2,
        },
      });

      const result = await pdfImportService.getActiveSessions();

      expect(result.success).toBe(true);
      expect(result.active_sessions).toHaveLength(2);
      expect(result.total_count).toBe(2);
    });

    it('should return empty list on 404', async () => {
      vi.mocked(apiClient.get).mockRejectedValue({
        response: { status: 404 },
      });

      const result = await pdfImportService.getActiveSessions();

      expect(result.success).toBe(true);
      expect(result.active_sessions).toEqual([]);
    });
  });

  // ==========================================================================
  // 系统信息测试
  // ==========================================================================

  describe('getSystemInfo', () => {
    it('should return system info', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          success: true,
          message: 'PDF导入系统运行正常',
          capabilities: {
            pdfplumber_available: true,
            pymupdf_available: true,
            ocr_available: true,
          },
        },
      });

      const result = await pdfImportService.getSystemInfo();

      expect(result.success).toBe(true);
      expect(result.capabilities.pdfplumber_available).toBe(true);
    });

    it('should return fallback info on 404', async () => {
      vi.mocked(apiClient.get).mockRejectedValue({
        response: { status: 404 },
      });

      const result = await pdfImportService.getSystemInfo();

      expect(result.success).toBe(true);
      expect(result.message).toContain('备用');
    });
  });

  // ==========================================================================
  // 健康检查测试
  // ==========================================================================

  describe('healthCheck', () => {
    it('should return healthy status', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { message: 'OK' },
      });

      const result = await pdfImportService.healthCheck();

      expect(result.status).toBe('healthy');
      expect(result.components.pdf_import).toBe(true);
    });

    it('should return unhealthy on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Service down'));

      const result = await pdfImportService.healthCheck();

      expect(result.status).toBe('unhealthy');
    });
  });

  // ==========================================================================
  // 工具方法测试
  // ==========================================================================

  describe('formatFileSize', () => {
    it('should format bytes correctly', () => {
      expect(pdfImportService.formatFileSize(0)).toBe('0 Bytes');
      expect(pdfImportService.formatFileSize(1024)).toBe('1 KB');
      expect(pdfImportService.formatFileSize(1048576)).toBe('1 MB');
      expect(pdfImportService.formatFileSize(1536000)).toBe('1.46 MB');
    });
  });

  describe('validateFileType', () => {
    it('should accept PDF files', () => {
      const pdfFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      expect(pdfImportService.validateFileType(pdfFile)).toBe(true);
    });

    it('should accept PDF by extension', () => {
      const pdfFile = new File(['test'], 'test.PDF', { type: '' });
      expect(pdfImportService.validateFileType(pdfFile)).toBe(true);
    });

    it('should reject non-PDF files', () => {
      const txtFile = new File(['test'], 'test.txt', { type: 'text/plain' });
      expect(pdfImportService.validateFileType(txtFile)).toBe(false);
    });
  });

  describe('validateFileSize', () => {
    it('should accept files within limit', () => {
      const smallFile = new File(['test'], 'test.pdf');
      Object.defineProperty(smallFile, 'size', { value: 10 * 1024 * 1024 }); // 10MB
      expect(pdfImportService.validateFileSize(smallFile, 50)).toBe(true);
    });

    it('should reject files exceeding limit', () => {
      const largeFile = new File(['test'], 'test.pdf');
      Object.defineProperty(largeFile, 'size', { value: 60 * 1024 * 1024 }); // 60MB
      expect(pdfImportService.validateFileSize(largeFile, 50)).toBe(false);
    });
  });

  describe('estimateProcessingTime', () => {
    it('should estimate time based on file size', () => {
      expect(pdfImportService.estimateProcessingTime(500000)).toBe('10-20秒'); // <1MB
      expect(pdfImportService.estimateProcessingTime(3 * 1024 * 1024)).toBe('20-40秒'); // 3MB
      expect(pdfImportService.estimateProcessingTime(7 * 1024 * 1024)).toBe('30-60秒'); // 7MB
      expect(pdfImportService.estimateProcessingTime(15 * 1024 * 1024)).toBe('45-90秒'); // 15MB
      expect(pdfImportService.estimateProcessingTime(30 * 1024 * 1024)).toBe('60-120秒'); // 30MB
    });
  });

  describe('estimatePdfImportProcessingTime', () => {
    it('should estimate multi-engine processing time', () => {
      expect(pdfImportService.estimatePdfImportProcessingTime(500000)).toBe('30-45秒');
      expect(pdfImportService.estimatePdfImportProcessingTime(3 * 1024 * 1024)).toBe('45-75秒');
      expect(pdfImportService.estimatePdfImportProcessingTime(25 * 1024 * 1024)).toBe('120-240秒');
    });
  });

  // ==========================================================================
  // 功能可用性检查测试
  // ==========================================================================

  describe('checkPdfImportFeaturesAvailability', () => {
    it('should return available when most features work', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          success: true,
          capabilities: {
            pdfplumber_available: true,
            pymupdf_available: true,
            spacy_available: true,
            ocr_available: true,
          },
        },
      });

      const result = await pdfImportService.checkPdfImportFeaturesAvailability();

      expect(result.available).toBe(true);
      expect(result.features.pdfplumber_available).toBe(true);
    });

    it('should return unavailable when features fail', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Service down'));

      const result = await pdfImportService.checkPdfImportFeaturesAvailability();

      expect(result.available).toBe(false);
    });
  });

  // ==========================================================================
  // 静态方法测试
  // ==========================================================================

  describe('getSystemCapabilities', () => {
    it('should return system capabilities', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          extractor_summary: { method: 'multi_engine' },
          validator_summary: { enabled: true },
        },
      });

      const result = await PDFImportService.getSystemCapabilities();

      expect(result.spacy_available).toBe(true);
      expect(result.ocr_available).toBe(true);
      expect(result.max_file_size_mb).toBe(50);
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockRejectedValue({
        response: {
          data: { detail: 'Service unavailable' },
        },
      });

      await expect(PDFImportService.getSystemCapabilities()).rejects.toThrow();
    });
  });
});
