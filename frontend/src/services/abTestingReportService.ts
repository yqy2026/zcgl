import { apiClient } from '@/api/client';
import { AB_TESTING_API } from '@/constants/api';
import type { ExtractResult } from '@/types/apiResponse';

interface ABTestingEventPayload {
  eventType: string;
  data: Record<string, unknown>;
  timestamp: string;
}

interface ABTestingConversionPayload {
  testId: string;
  metric: string;
  value?: unknown;
  userId: string;
  timestamp: string;
}

class ABTestingReportService {
  private readonly eventEndpoint = AB_TESTING_API.EVENTS;
  private readonly conversionEndpoint = AB_TESTING_API.CONVERSIONS;

  private ensureSuccess(result: ExtractResult<unknown>, actionName: string): void {
    if (!result.success) {
      throw new Error(`${actionName}: ${result.error ?? '未知错误'}`);
    }
  }

  async reportEvent(payload: ABTestingEventPayload): Promise<void> {
    const result = await apiClient.post(this.eventEndpoint, payload, {
      retry: false,
      smartExtract: false,
    });
    this.ensureSuccess(result, 'A/B 事件上报失败');
  }

  async reportConversion(payload: ABTestingConversionPayload): Promise<void> {
    const result = await apiClient.post(this.conversionEndpoint, payload, {
      retry: false,
      smartExtract: false,
    });
    this.ensureSuccess(result, 'A/B 转化上报失败');
  }
}

export const abTestingReportService = new ABTestingReportService();
