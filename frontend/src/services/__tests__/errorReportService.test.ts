import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import type { ExtractResult } from '@/types/apiResponse';
import { errorReportService } from '../errorReportService';

vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

const createResult = (overrides: Partial<ExtractResult<unknown>>): ExtractResult<unknown> => ({
  success: true,
  data: null,
  rawResponse: {} as ExtractResult<unknown>['rawResponse'],
  ...overrides,
});

describe('errorReportService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('report 应使用 apiClient.post 上报错误', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(createResult({}));

    const payload = {
      error: 'Test error',
      stack: 'stack trace',
      componentStack: 'component stack',
      timestamp: '2026-02-07T12:00:00.000Z',
      userAgent: 'Mozilla/5.0',
      url: 'http://localhost:5173/dashboard',
      retryCount: 1,
    };

    await expect(errorReportService.report(payload)).resolves.toBeUndefined();

    expect(apiClient.post).toHaveBeenCalledWith('/errors/report', payload, {
      retry: false,
      smartExtract: false,
    });
  });

  it('report 在 API 失败时应抛出可读错误', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(
      createResult({
        success: false,
        error: 'network unavailable',
      })
    );

    const payload = {
      error: 'Test error',
      stack: '',
      componentStack: '',
      timestamp: '2026-02-07T12:00:00.000Z',
      userAgent: 'Mozilla/5.0',
      url: 'http://localhost:5173/dashboard',
      retryCount: 0,
    };

    await expect(errorReportService.report(payload)).rejects.toThrow(
      '错误上报失败: network unavailable'
    );
  });
});
