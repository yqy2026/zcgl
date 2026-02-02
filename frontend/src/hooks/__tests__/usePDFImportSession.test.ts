/**
 * usePDFImportSession Hook 测试
 * 测试 PDF 导入会话管理 Hook 的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@/test/utils/test-helpers';

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
    info: vi.fn(),
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
      expect(typeof result.current.handleUploadSuccess).toBe('function');
      expect(typeof result.current.handleUploadError).toBe('function');
      expect(typeof result.current.handleConfirmImport).toBe('function');
      expect(typeof result.current.handleCancel).toBe('function');
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

  describe('handleUpload', () => {
    it('应该设置当前会话', () => {
      const { result } = renderHook(() => usePDFImportSession());
      const fileInfo = {
        uid: 'file-1',
        name: 'test.pdf',
        status: 'done',
        size: 123,
        type: 'application/pdf',
      } as const;

      act(() => {
        result.current.handleUploadSuccess('session-123', fileInfo);
      });

      expect(result.current.currentSession?.sessionId).toBe('session-123');
    });

    it('应该处理上传失败', () => {
      const { result } = renderHook(() => usePDFImportSession());

      act(() => {
        result.current.handleUploadError(new Error('上传失败'));
      });

      expect(MessageManager.error).toHaveBeenCalled();
      expect(result.current.currentSession).toBeNull();
    });
  });

  describe('handleCancel', () => {
    it('应该取消当前会话', async () => {
      vi.mocked(pdfImportService.cancelSession).mockResolvedValue({
        success: true,
        message: '已取消',
      });

      const { result } = renderHook(() => usePDFImportSession());

      act(() => {
        result.current.handleUploadSuccess('session-123', {
          uid: 'session-123',
          name: 'test.pdf',
          status: 'done',
          size: 0,
          type: 'application/pdf',
        } as const);
      });

      await act(async () => {
        await result.current.handleCancel();
      });

      expect(pdfImportService.cancelSession).toHaveBeenCalled();
    });

    it('无当前会话时不应调用取消', async () => {
      const { result } = renderHook(() => usePDFImportSession());

      await act(async () => {
        await result.current.handleCancel();
      });

      expect(pdfImportService.cancelSession).not.toHaveBeenCalled();
    });
  });

  describe('handleConfirmImport', () => {
    it('应该确认导入', async () => {
      vi.mocked(pdfImportService.confirmImport).mockResolvedValue({
        success: true,
        message: '导入成功',
        contract_id: 'contract-123',
      });

      const { result } = renderHook(() => usePDFImportSession());

      act(() => {
        result.current.handleUploadSuccess('session-123', {
          uid: 'session-123',
          name: 'test.pdf',
          status: 'done',
          size: 0,
          type: 'application/pdf',
        } as const);
      });

      const confirmedData = {
        contract_number: 'HT-001',
        tenant_name: '测试租户',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        monthly_rent_base: '10000',
        rent_terms: [],
      };

      await act(async () => {
        await result.current.handleConfirmImport(confirmedData);
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

      act(() => {
        result.current.handleUploadSuccess('session-123', {
          uid: 'session-123',
          name: 'test.pdf',
          status: 'done',
          size: 0,
          type: 'application/pdf',
        } as const);
      });

      await act(async () => {
        await result.current.handleConfirmImport({} as Record<string, unknown>);
      });

      expect(MessageManager.success).not.toHaveBeenCalled();
    });
  });

  describe('状态管理', () => {
    it('上传成功后应设置当前会话', async () => {
      const { result } = renderHook(() => usePDFImportSession());

      act(() => {
        result.current.handleUploadSuccess('session-123', {
          uid: 'session-123',
          name: 'test.pdf',
          status: 'done',
          size: 0,
          type: 'application/pdf',
        } as const);
      });

      expect(result.current.currentSession).not.toBeNull();
    });

    it('取消会话后应清空当前会话', async () => {
      vi.mocked(pdfImportService.cancelSession).mockResolvedValue({
        success: true,
        message: '已取消',
      });

      const { result } = renderHook(() => usePDFImportSession());

      act(() => {
        result.current.handleUploadSuccess('session-123', {
          uid: 'session-123',
          name: 'test.pdf',
          status: 'done',
          size: 0,
          type: 'application/pdf',
        } as const);
      });

      await act(async () => {
        await result.current.handleCancel();
      });

      expect(result.current.currentSession).toBeNull();
    });
  });
});
