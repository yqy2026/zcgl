import { apiClient } from '@/api/client';
import { ERROR_REPORTING_API } from '@/constants/api';
import type { ExtractResult } from '@/types/apiResponse';

export interface FrontendErrorReportPayload {
  error: string;
  stack: string;
  componentStack: string;
  timestamp: string;
  userAgent: string;
  url: string;
  retryCount: number;
}

class ErrorReportService {
  private readonly endpoint = ERROR_REPORTING_API.REPORT;

  private ensureSuccess(result: ExtractResult<unknown>): void {
    if (!result.success) {
      throw new Error(`错误上报失败: ${result.error ?? '未知错误'}`);
    }
  }

  async report(errorReport: FrontendErrorReportPayload): Promise<void> {
    const result = await apiClient.post(this.endpoint, errorReport, {
      retry: false,
      smartExtract: false,
    });
    this.ensureSuccess(result);
  }
}

export const errorReportService = new ErrorReportService();
