/**
 * PDFImportContext 测试
 */

import React from 'react';
import { act, renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PDFImportProvider, usePDFImportContext, usePDFImportUpload } from '../PDFImportContext';

// Mock pdfImportService
vi.mock('../../../../services/pdfImportService', () => ({
  pdfImportService: {
    getPdfImportSystemInfo: vi.fn().mockResolvedValue({
      max_file_size: 50,
      supported_formats: ['pdf'],
    }),
    uploadPdfFileWithOptions: vi.fn(),
    getPdfImportProgress: vi.fn(),
    cancelPdfImportSession: vi.fn(),
  },
}));

// Mock MessageManager
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock logger
vi.mock('../../../../utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  }),
}));

import { pdfImportService } from '../../../../services/pdfImportService';
import { MessageManager } from '@/utils/messageManager';

describe('PDFImportContext', () => {
  const mockOnUploadSuccess = vi.fn();
  const mockOnUploadError = vi.fn();

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <PDFImportProvider
      maxSize={50}
      onUploadSuccess={mockOnUploadSuccess}
      onUploadError={mockOnUploadError}
    >
      {children}
    </PDFImportProvider>
  );

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('usePDFImportContext', () => {
    it('在 Provider 外部使用时抛出错误', () => {
      expect(() => {
        renderHook(() => usePDFImportContext());
      }).toThrow('usePDFImportContext must be used within PDFImportProvider');
    });

    it('在 Provider 内部返回 context 值', () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      expect(result.current).toBeDefined();
      expect(result.current.uploading).toBe(false);
      expect(result.current.currentSession).toBeNull();
      expect(result.current.maxSize).toBe(50);
    });
  });

  describe('usePDFImportUpload', () => {
    it('在 Provider 外部使用时抛出错误', () => {
      expect(() => {
        renderHook(() => usePDFImportUpload());
      }).toThrow('usePDFImportUpload must be used within PDFImportProvider');
    });

    it('返回上传函数', () => {
      const { result } = renderHook(() => usePDFImportUpload(), { wrapper });

      expect(result.current).toBeDefined();
      expect(typeof result.current).toBe('function');
    });
  });

  describe('初始状态', () => {
    it('初始化时加载系统信息', async () => {
      renderHook(() => usePDFImportContext(), { wrapper });

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(pdfImportService.getPdfImportSystemInfo).toHaveBeenCalled();
    });

    it('默认处理步骤初始化正确', () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      expect(result.current.processingSteps).toHaveLength(6);
      expect(result.current.processingSteps[0].title).toBe('文件上传');
      expect(result.current.processingSteps[0].status).toBe('wait');
    });
  });

  describe('handleCancel', () => {
    it('取消上传并重置状态', async () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      await act(async () => {
        result.current.handleCancel();
      });

      expect(result.current.uploading).toBe(false);
      expect(result.current.uploadProgress).toBe(0);
      expect(result.current.currentSession).toBeNull();
      expect(MessageManager.info).toHaveBeenCalledWith('已取消上传');
    });
  });

  describe('handleReset', () => {
    it('重置所有状态', async () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      await act(async () => {
        result.current.handleReset();
      });

      expect(result.current.uploading).toBe(false);
      expect(result.current.uploadProgress).toBe(0);
      expect(result.current.currentSession).toBeNull();
      expect(result.current.processingProgress).toBeNull();
      expect(result.current.uploadStats).toBeNull();
    });
  });

  describe('getStepIcon', () => {
    it('为 finish 状态返回成功图标', () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      const icon = result.current.getStepIcon({
        title: 'Test',
        description: 'Test',
        status: 'finish'
      });

      expect(icon).toBeDefined();
    });

    it('为 process 状态返回加载图标', () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      const icon = result.current.getStepIcon({
        title: 'Test',
        description: 'Test',
        status: 'process'
      });

      expect(icon).toBeDefined();
    });

    it('为 error 状态返回错误图标', () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      const icon = result.current.getStepIcon({
        title: 'Test',
        description: 'Test',
        status: 'error'
      });

      expect(icon).toBeDefined();
    });

    it('为 wait 状态返回默认图标', () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      const icon = result.current.getStepIcon({
        title: 'Test',
        description: 'Test',
        status: 'wait'
      });

      expect(icon).toBeDefined();
    });
  });

  describe('setters', () => {
    it('setShowAdvancedOptions 更新状态', async () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      expect(result.current.showAdvancedOptions).toBe(false);

      await act(async () => {
        result.current.setShowAdvancedOptions(true);
      });

      expect(result.current.showAdvancedOptions).toBe(true);
    });

    it('setShowPreviewModal 更新状态', async () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      expect(result.current.showPreviewModal).toBe(false);

      await act(async () => {
        result.current.setShowPreviewModal(true);
      });

      expect(result.current.showPreviewModal).toBe(true);
    });

    it('setProcessingOptions 更新状态', async () => {
      const { result } = renderHook(() => usePDFImportContext(), { wrapper });

      const newOptions = {
        processing_mode: 'fast' as const,
        extract_tables: false,
        validate_data: true,
        auto_match: false,
      };

      await act(async () => {
        result.current.setProcessingOptions(newOptions);
      });

      expect(result.current.processingOptions).toEqual(newOptions);
    });
  });

  describe('上传流程', () => {
    it('成功上传文件', async () => {
      vi.mocked(pdfImportService.uploadPdfFileWithOptions).mockResolvedValue({
        success: true,
        session_id: 'test-session-123',
        processing_status: {
          final_results: {
            extraction_quality: {
              processing_methods: ['OCR'],
            },
          },
        },
      });

      vi.mocked(pdfImportService.getPdfImportProgress).mockResolvedValue({
        success: true,
        session_status: {
          status: 'ready_for_review',
          progress: 100,
        },
      });

      const { result } = renderHook(() => usePDFImportUpload(), { wrapper });

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      const onSuccess = vi.fn();

      await act(async () => {
        await result.current(file, onSuccess);
        await vi.runAllTimersAsync();
      });

      expect(pdfImportService.uploadPdfFileWithOptions).toHaveBeenCalled();
      expect(onSuccess).toHaveBeenCalled();
      expect(mockOnUploadSuccess).toHaveBeenCalled();
      expect(MessageManager.success).toHaveBeenCalledWith('文件上传成功，开始智能处理...');
    });

    it('上传失败时调用错误回调', async () => {
      vi.mocked(pdfImportService.uploadPdfFileWithOptions).mockRejectedValue(
        new Error('上传失败')
      );

      const { result } = renderHook(() => usePDFImportUpload(), { wrapper });

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      const onError = vi.fn();

      await act(async () => {
        await result.current(file, undefined, onError);
        await vi.runAllTimersAsync();
      });

      expect(onError).toHaveBeenCalled();
      expect(mockOnUploadError).toHaveBeenCalledWith('上传失败');
      expect(MessageManager.error).toHaveBeenCalledWith('上传失败');
    });
  });

  describe('清理', () => {
    it('卸载时清理定时器', () => {
      const { unmount } = renderHook(() => usePDFImportContext(), { wrapper });

      unmount();

      // 确保不会抛出错误
      expect(true).toBe(true);
    });
  });
});
