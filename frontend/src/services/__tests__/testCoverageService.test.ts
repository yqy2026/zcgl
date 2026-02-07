import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import type { ExtractResult } from '@/types/apiResponse';
import {
  testCoverageService,
  type CoverageReport,
  type CoverageThreshold,
  type CoverageTrend,
  type CoverageMetrics,
  type QualityGateResult,
} from '../testCoverageService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const createResult = <T>(overrides: Partial<ExtractResult<T>>): ExtractResult<T> => ({
  success: true,
  data: undefined,
  rawResponse: {} as ExtractResult<T>['rawResponse'],
  ...overrides,
});

describe('testCoverageService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getCurrentCoverageReport 应调用 /test-coverage/report 并返回数据', async () => {
    const report: CoverageReport = {
      project_name: 'zcgl',
      total_coverage: 82.4,
      backend_coverage: 85.1,
      frontend_coverage: 79.6,
      module_metrics: [],
      total_tests: 120,
      passed_tests: 116,
      failed_tests: 2,
      skipped_tests: 2,
      generated_at: '2026-02-06T10:00:00Z',
    };

    vi.mocked(apiClient.get).mockResolvedValue(createResult<CoverageReport>({ data: report }));

    const result = await testCoverageService.getCurrentCoverageReport();

    expect(apiClient.get).toHaveBeenCalledWith('/test-coverage/report', { retry: false });
    expect(result).toEqual({ success: true, data: report });
  });

  it('getCoverageTrend 应传递 days 查询参数', async () => {
    const trend: CoverageTrend[] = [{ date: '2026-02-06', total_coverage: 81.3 }];

    vi.mocked(apiClient.get).mockResolvedValue(createResult<CoverageTrend[]>({ data: trend }));

    const result = await testCoverageService.getCoverageTrend(14);

    expect(apiClient.get).toHaveBeenCalledWith('/test-coverage/trend', {
      params: { days: 14 },
      retry: false,
    });
    expect(result.data).toEqual(trend);
  });

  it('getModuleCoverage 应传递 min/max 参数', async () => {
    const modules: CoverageMetrics[] = [
      {
        module_name: 'asset',
        coverage_percentage: 88,
        lines_covered: 44,
        lines_total: 50,
        branches_covered: 22,
        branches_total: 30,
        functions_covered: 10,
        functions_total: 12,
        last_updated: '2026-02-06T10:00:00Z',
        file_path: 'src/services/assetService.ts',
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue(createResult<CoverageMetrics[]>({ data: modules }));

    const result = await testCoverageService.getModuleCoverage(60, 95);

    expect(apiClient.get).toHaveBeenCalledWith('/test-coverage/modules', {
      params: {
        min_coverage: 60,
        max_coverage: 95,
      },
      retry: false,
    });
    expect(result.data).toEqual(modules);
  });

  it('getCoverageThresholds 在响应失败时应抛出业务错误', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(
      createResult<CoverageThreshold>({
        success: false,
        error: 'threshold query failed',
      })
    );

    await expect(testCoverageService.getCoverageThresholds()).rejects.toThrow(
      '获取覆盖率阈值失败: threshold query failed'
    );
  });

  it('updateCoverageThresholds 应调用 PUT 并返回更新结果', async () => {
    const thresholds: CoverageThreshold = {
      backend_threshold: 80,
      frontend_threshold: 75,
      total_threshold: 78,
    };

    vi.mocked(apiClient.put).mockResolvedValue(
      createResult<CoverageThreshold>({
        data: thresholds,
      })
    );

    const result = await testCoverageService.updateCoverageThresholds(thresholds);

    expect(apiClient.put).toHaveBeenCalledWith('/test-coverage/thresholds', thresholds, {
      retry: false,
    });
    expect(result).toEqual({ success: true, data: thresholds });
  });

  it('checkQualityGate 在缺失 data 时应抛出错误', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(
      createResult<QualityGateResult>({
        data: undefined,
      })
    );

    await expect(testCoverageService.checkQualityGate()).rejects.toThrow(
      '检查质量门禁失败: 未知错误'
    );
  });

  it('checkQualityGate 成功时应返回质量门禁结果', async () => {
    const qualityGate: QualityGateResult = {
      passed: true,
      thresholds: {
        backend: 80,
        frontend: 75,
        total: 78,
      },
      current_coverage: {
        backend: 82,
        frontend: 79,
        total: 80.5,
      },
      failed_checks: [],
    };

    vi.mocked(apiClient.get).mockResolvedValue(
      createResult<QualityGateResult>({
        data: qualityGate,
      })
    );

    const result = await testCoverageService.checkQualityGate();

    expect(apiClient.get).toHaveBeenCalledWith('/test-coverage/quality-gate', { retry: false });
    expect(result).toEqual({ success: true, data: qualityGate });
  });
});
