import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import type { ExtractResult } from '@/types/apiResponse';
import { abTestingReportService } from '../abTestingReportService';

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

describe('abTestingReportService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('reportEvent 应调用事件上报端点', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(createResult({}));

    const payload = {
      eventType: 'variant_assigned',
      data: { testId: 'dashboard_layout_v2', variantId: 'new_layout' },
      timestamp: '2026-02-07T12:10:00.000Z',
    };

    await expect(abTestingReportService.reportEvent(payload)).resolves.toBeUndefined();

    expect(apiClient.post).toHaveBeenCalledWith('/analytics/abtest-events', payload, {
      retry: false,
      smartExtract: false,
    });
  });

  it('reportEvent 在失败时应抛出业务错误', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(
      createResult({
        success: false,
        error: 'request timeout',
      })
    );

    const payload = {
      eventType: 'variant_assigned',
      data: {},
      timestamp: '2026-02-07T12:10:00.000Z',
    };

    await expect(abTestingReportService.reportEvent(payload)).rejects.toThrow(
      'A/B 事件上报失败: request timeout'
    );
  });

  it('reportConversion 应调用转化上报端点', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(createResult({}));

    const payload = {
      testId: 'asset_list_density',
      metric: 'click',
      value: { element: 'asset_list' },
      userId: 'user-001',
      timestamp: '2026-02-07T12:11:00.000Z',
    };

    await expect(abTestingReportService.reportConversion(payload)).resolves.toBeUndefined();

    expect(apiClient.post).toHaveBeenCalledWith('/analytics/abtest-conversions', payload, {
      retry: false,
      smartExtract: false,
    });
  });

  it('reportConversion 在失败时应抛出业务错误', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(
      createResult({
        success: false,
        error: 'service unavailable',
      })
    );

    const payload = {
      testId: 'asset_list_density',
      metric: 'engagement_time',
      value: 12.5,
      userId: 'user-001',
      timestamp: '2026-02-07T12:11:00.000Z',
    };

    await expect(abTestingReportService.reportConversion(payload)).rejects.toThrow(
      'A/B 转化上报失败: service unavailable'
    );
  });
});
