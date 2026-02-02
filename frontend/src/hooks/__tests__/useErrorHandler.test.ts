/**
 * useErrorHandler Hook 测试
 * 测试错误处理 Hook 的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@/test/utils/test-helpers';

// Mock dependencies
const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('@/components/Feedback/SuccessNotification', () => ({
  default: {
    notify: vi.fn(),
    warning: {
      permission: vi.fn(),
    },
    error: {
      network: vi.fn(),
      server: vi.fn(),
      validation: vi.fn(),
    },
    success: vi.fn(),
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

import { useErrorHandler } from '../useErrorHandler';
import SuccessNotification from '@/components/Feedback/SuccessNotification';

describe('useErrorHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('初始化', () => {
    it('应该返回错误处理函数', () => {
      const { result } = renderHook(() => useErrorHandler());

      expect(result.current.handleApiError).toBeDefined();
      expect(typeof result.current.handleApiError).toBe('function');
    });

    it('应该接受自定义选项', () => {
      const { result } = renderHook(() =>
        useErrorHandler({
          showNotification: false,
          redirectOnError: true,
          logErrors: false,
        })
      );

      expect(result.current.handleApiError).toBeDefined();
    });
  });

  describe('handleApiError', () => {
    it('应该处理 400 错误', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 400,
            data: { message: '请求参数错误' },
          },
        });
      });

      expect(SuccessNotification.notify).toHaveBeenCalled();
    });

    it('应该处理 401 错误', () => {
      const { result } = renderHook(() =>
        useErrorHandler({ redirectOnError: true })
      );

      act(() => {
        result.current.handleApiError({
          response: {
            status: 401,
            data: {},
          },
        });
      });

      expect(SuccessNotification.warning.permission).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });

    it('应该处理 403 错误', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 403,
            data: {},
          },
        });
      });

      expect(SuccessNotification.notify).toHaveBeenCalled();
    });

    it('应该处理 404 错误', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 404,
            data: {},
          },
        });
      });

      expect(SuccessNotification.notify).toHaveBeenCalled();
    });

    it('应该处理 422 错误', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 422,
            data: { message: '数据验证失败' },
          },
        });
      });

      expect(SuccessNotification.notify).toHaveBeenCalled();
    });

    it('应该处理 429 错误', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 429,
            data: {},
          },
        });
      });

      expect(SuccessNotification.notify).toHaveBeenCalled();
    });

    it('应该处理 500 错误', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 500,
            data: {},
          },
        });
      });

      expect(SuccessNotification.error.server).toHaveBeenCalled();
    });

    it('应该处理 502 错误', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 502,
            data: {},
          },
        });
      });

      expect(SuccessNotification.error.server).toHaveBeenCalled();
    });

    it('应该处理 503 错误', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 503,
            data: {},
          },
        });
      });

      expect(SuccessNotification.error.server).toHaveBeenCalled();
    });

    it('应该处理网络错误（无响应）', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          request: {},
          message: 'Network Error',
        });
      });

      expect(SuccessNotification.error.network).toHaveBeenCalled();
    });

    it('应该处理未知错误', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          message: '未知错误',
        });
      });

      expect(SuccessNotification.notify).toHaveBeenCalled();
    });
  });

  describe('选项配置', () => {
    it('showNotification=false 时不显示通知', () => {
      const { result } = renderHook(() =>
        useErrorHandler({ showNotification: false })
      );

      act(() => {
        result.current.handleApiError({
          response: { status: 400, data: {} },
        });
      });

      expect(SuccessNotification.notify).not.toHaveBeenCalled();
    });

    it('redirectOnError=false 时不重定向', () => {
      const { result } = renderHook(() =>
        useErrorHandler({ redirectOnError: false })
      );

      act(() => {
        result.current.handleApiError({
          response: { status: 401, data: {} },
        });
      });

      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe('错误信息提取', () => {
    it('应该从响应中提取自定义错误消息', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 400,
            data: { message: '自定义错误消息' },
          },
        });
      });

      expect(SuccessNotification.notify).toHaveBeenCalledWith(
        expect.objectContaining({
          description: expect.stringContaining('自定义错误消息'),
        })
      );
    });

    it('应该从 error 字段提取错误消息', () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.handleApiError({
          response: {
            status: 400,
            data: { error: '错误字段消息' },
          },
        });
      });

      expect(SuccessNotification.notify).toHaveBeenCalled();
    });
  });
});
