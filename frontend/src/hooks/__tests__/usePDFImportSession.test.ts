/**
 * usePDFImportSession Hook 测试
 * 测试 PDF 导入会话管理 Hook 的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// Mock dependencies
vi.mock('@/services/pdfImportService', () => ({
  pdfImportService: {
    getActiveSessions: vi.fn(),
    uploadPDFFile: vi.fn(),
    getProgress: vi.fn(),
    getResult: vi.fn(),
    confirmImport: vi.fn(),
    cancelSession: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    loading: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

import { usePDFImportSession } from '../usePDFImportSession';
import { pdfImportService } from '@/services/pdfImportService';
import { MessageManager } from '@/utils/messageManager';

describe('usePDFImportSession', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('初始化', () => {
    it('应该返回初始状态', () => {
      const { result } = renderHook(() => usePDFImportSession());

      expect(result.current.currentSession).toBeNull();
      expect(result.current.sessionHistory).toEqual([]);
      expect(result.current.loading).toBe(false);
    });

    it('应该提供必要的方法', () => {
      const { result } = renderHook(() => usePDFImportSession());

      expect(typeof result.current.loadSessionHistory).toBe('function');
      expect(typeof result.current.startUpload).toBe('function');
      expect(typeof result.current.cancelCurrentSession).toBe('function');
    });
  });

  describe('loadSessionHistory', () => {
    it('应该加载会话历史', async () => {
      vi.mocked(pdfImportService.getActiveSessions).mockResolvedValue({
        success: true,
        active_sessions: [
          {
            session_id: 's1',
            status: 'ready_for_review',
            progress: 100,
            current_step: '完成',
            created_at: '2026-01-30',
            file_name: 'test.pdf',
          },
        ],
        total_count: 1,
      });

      const { result } = renderHook(() => usePDFImportSession());

      await act(async () => {
        await result.current.loadSessionHistory();
      });

      expect(pdfImportService.getActiveSessions).toHaveBeenCalled();
    });

    it('应该处理加载失败', async () => {
      vi.mocked(pdfImportService.getActiveSessions).mockRejectedValue(
        new Error('Network error')
      );

      const { result } = renderHook(() => usePDFImportSession());

      await act(async () => {
        await result.current.loadSessionHistory();
      });

      expect(result.current.sessionHistory).toEqual([]);
    });
  });

  describe('startUpload', () => {
    it('应该开始上传文件', async () => {
      vi.mocked(pdfImportService.uploadPDFFile).mockResolvedValue({
        success: true,
        message: '上传成功',
        session_id: 'session-123',
      });

      const { result } = renderHook(() => usePDFImportSession());
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      await act(async () => {
        await result.current.startUpload(mockFile);
      });

      expect(pdfImportService.uploadPDFFile).toHaveBeenCalled();
    });

    it('应该处理上传失败', async () => {
      vi.mocked(pdfImportService.uploadPDFFile).mockResolvedValue({
        success: false,
        message: '上传失败',
        error: '文件格式错误',
      });

      const { result } = renderHook(() => usePDFImportSession());
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      await act(async () => {
        await result.current.startUpload(mockFile);
      });

      expect(MessageManager.error).toHaveBeenCalled();
    });

    it('应该设置 loading 状态', async () => {
      vi.mocked(pdfImportService.uploadPDFFile).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({
          success: true,
          message: '上传成功',
          session_id: 'session-123',
        }), 100))
      );

      const { result } = renderHook(() => usePDFImportSession());
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      act(() => {
        result.current.startUpload(mockFile);
      });

      expect(result.current.loading).toBe(true);
    });
  });

  describe('cancelCurrentSession', () => {
    it('应该取消当前会话', async () => {
      vi.mocked(pdfImportService.cancelSession).mockResolvedValue({
        success: true,
        message: '已取消',
      });

      const { result } = renderHook(() => usePDFImportSession());

      // 模拟有当前会话
      await act(async () => {
        // 先设置会话
        vi.mocked(pdfImportService.uploadPDFFile).mockResolvedValue({
          success: true,
          message: '上传成功',
          session_id: 'session-123',
        });
        const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
        await result.current.startUpload(mockFile);
      });

      await act(async () => {
        await result.current.cancelCurrentSession();
      });

      expect(pdfImportService.cancelSession).toHaveBeenCalled();
    });

    it('无当前会话时不应调用取消', async () => {
      const { result } = renderHook(() => usePDFImportSession());

      await act(async () => {
        await result.current.cancelCurrentSession();
      });

      expect(pdfImportService.cancelSession).not.toHaveBeenCalled();
    });
  });

  describe('confirmImport', () => {
    it('应该确认导入', async () => {
      vi.mocked(pdfImportService.confirmImport).mockResolvedValue({
        success: true,
        message: '导入成功',
        contract_id: 'contract-123',
      });

      const { result } = renderHook(() => usePDFImportSession());

      const confirmedData = {
        contract_number: 'HT-001',
        tenant_name: '测试租户',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        monthly_rent_base: '10000',
        rent_terms: [],
      };

      await act(async () => {
        await result.current.confirmImport('session-123', confirmedData);
      });

      expect(pdfImportService.confirmImport).toHaveBeenCalledWith(
        'session-123',
        confirmedData
      );
    });

    it('应该处理导入失败', async () => {
      vi.mocked(pdfImportService.confirmImport).mockResolvedValue({
        success: false,
        message: '导入失败',
        error: '合同编号重复',
      });

      const { result } = renderHook(() => usePDFImportSession());

      await act(async () => {
        await result.current.confirmImport('session-123', {} as Record<string, unknown>);
      });

      expect(MessageManager.error).toHaveBeenCalled();
    });
  });

  describe('getSessionResult', () => {
    it('应该获取会话结果', async () => {
      vi.mocked(pdfImportService.getResult).mockResolvedValue({
        success: true,
        result: {
          success: true,
          session_id: 'session-123',
          extraction_result: { data: {} },
        } as unknown as Awaited<ReturnType<typeof pdfImportService.getResult>>,
      });

      const { result } = renderHook(() => usePDFImportSession());

      await act(async () => {
        const sessionResult = await result.current.getSessionResult('session-123');
        expect(sessionResult).toBeDefined();
      });

      expect(pdfImportService.getResult).toHaveBeenCalledWith('session-123');
    });
  });

  describe('状态管理', () => {
    it('上传成功后应设置当前会话', async () => {
      vi.mocked(pdfImportService.uploadPDFFile).mockResolvedValue({
        success: true,
        message: '上传成功',
        session_id: 'session-123',
      });

      const { result } = renderHook(() => usePDFImportSession());
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      await act(async () => {
        await result.current.startUpload(mockFile);
      });

      expect(result.current.currentSession).not.toBeNull();
    });

    it('取消会话后应清空当前会话', async () => {
      vi.mocked(pdfImportService.uploadPDFFile).mockResolvedValue({
        success: true,
        message: '上传成功',
        session_id: 'session-123',
      });
      vi.mocked(pdfImportService.cancelSession).mockResolvedValue({
        success: true,
        message: '已取消',
      });

      const { result } = renderHook(() => usePDFImportSession());
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      await act(async () => {
        await result.current.startUpload(mockFile);
      });

      await act(async () => {
        await result.current.cancelCurrentSession();
      });

      expect(result.current.currentSession).toBeNull();
    });
  });
});
