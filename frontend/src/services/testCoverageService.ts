/**
 * 测试覆盖率监控服务
 * 提供测试覆盖率数据的API调用封装
 */

import { apiClient } from '@/api/client';
import type { StandardApiResponse, ExtractResult } from '@/types/apiResponse';

// 类型定义
export interface CoverageMetrics {
  module_name: string;
  coverage_percentage: number;
  lines_covered: number;
  lines_total: number;
  branches_covered: number;
  branches_total: number;
  functions_covered: number;
  functions_total: number;
  last_updated: string;
  file_path: string;
}

export interface CoverageReport {
  project_name: string;
  total_coverage: number;
  backend_coverage?: number;
  frontend_coverage?: number;
  module_metrics: CoverageMetrics[];
  test_execution_time?: number;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  generated_at: string;
}

export interface CoverageTrend {
  date: string;
  backend_coverage?: number;
  frontend_coverage?: number;
  total_coverage: number;
}

export interface CoverageThreshold {
  backend_threshold: number;
  frontend_threshold: number;
  total_threshold: number;
}

export interface QualityGateResult {
  passed: boolean;
  thresholds: {
    backend: number;
    frontend: number;
    total: number;
  };
  current_coverage: {
    backend?: number;
    frontend?: number;
    total: number;
  };
  failed_checks: string[];
}

export interface TestPerformanceMetrics {
  module_name: string;
  test_name: string;
  execution_time: number;
  status: 'passed' | 'failed' | 'skipped';
  error_message?: string;
  memory_usage?: number;
  cpu_usage?: number;
}

export interface TestExecutionReport {
  execution_id: string;
  start_time: string;
  end_time: string;
  total_duration: number;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  performance_metrics: TestPerformanceMetrics[];
  environment_info: {
    node_version: string;
    python_version: string;
    os: string;
    hardware: {
      cpu_cores: number;
      memory_gb: number;
    };
  };
}

export interface DefectReport {
  defect_id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  priority: 'low' | 'medium' | 'high';
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  category: 'functional' | 'performance' | 'security' | 'usability' | 'compatibility';
  module: string;
  reproduction_steps: string[];
  expected_behavior: string;
  actual_behavior: string;
  created_at: string;
  updated_at: string;
  assigned_to?: string;
  reporter: string;
  fix_version?: string;
  test_coverage_impact?: {
    module_name: string;
    coverage_before: number;
    coverage_after: number;
  };
}

/**
 * 测试覆盖率API服务类
 */
class TestCoverageService {
  private readonly baseUrl = '/test-coverage';

  private unwrapResult<T>(result: ExtractResult<T>, actionName: string): T {
    if (!result.success || result.data == null) {
      throw new Error(`${actionName}: ${result.error ?? '未知错误'}`);
    }
    return result.data;
  }

  private ensureSuccess(result: ExtractResult<unknown>, actionName: string): void {
    if (!result.success) {
      throw new Error(`${actionName}: ${result.error ?? '未知错误'}`);
    }
  }

  /**
   * 获取当前测试覆盖率报告
   */
  async getCurrentCoverageReport(): Promise<StandardApiResponse<CoverageReport>> {
    const result = await apiClient.get<CoverageReport>(`${this.baseUrl}/report`, {
      retry: false,
    });
    const data = this.unwrapResult(result, '获取覆盖率报告失败');
    return { success: true, data };
  }

  /**
   * 获取覆盖率趋势数据
   */
  async getCoverageTrend(days: number = 30): Promise<StandardApiResponse<CoverageTrend[]>> {
    const result = await apiClient.get<CoverageTrend[]>(`${this.baseUrl}/trend`, {
      params: { days },
      retry: false,
    });
    const data = this.unwrapResult(result, '获取覆盖率趋势失败');
    return { success: true, data };
  }

  /**
   * 获取模块覆盖率列表
   */
  async getModuleCoverage(
    minCoverage: number = 0,
    maxCoverage: number = 100
  ): Promise<StandardApiResponse<CoverageMetrics[]>> {
    const result = await apiClient.get<CoverageMetrics[]>(`${this.baseUrl}/modules`, {
      params: {
        min_coverage: minCoverage,
        max_coverage: maxCoverage,
      },
      retry: false,
    });
    const data = this.unwrapResult(result, '获取模块覆盖率失败');
    return { success: true, data };
  }

  /**
   * 获取覆盖率阈值配置
   */
  async getCoverageThresholds(): Promise<StandardApiResponse<CoverageThreshold>> {
    const result = await apiClient.get<CoverageThreshold>(`${this.baseUrl}/thresholds`, {
      retry: false,
    });
    const data = this.unwrapResult(result, '获取覆盖率阈值失败');
    return { success: true, data };
  }

  /**
   * 更新覆盖率阈值配置
   */
  async updateCoverageThresholds(
    thresholds: CoverageThreshold
  ): Promise<StandardApiResponse<CoverageThreshold>> {
    const result = await apiClient.put<CoverageThreshold>(
      `${this.baseUrl}/thresholds`,
      thresholds,
      {
        retry: false,
      }
    );
    const data = this.unwrapResult(result, '更新覆盖率阈值失败');
    return { success: true, data };
  }

  /**
   * 检查质量门禁状态
   */
  async checkQualityGate(): Promise<StandardApiResponse<QualityGateResult>> {
    const result = await apiClient.get<QualityGateResult>(`${this.baseUrl}/quality-gate`, {
      retry: false,
    });
    const data = this.unwrapResult(result, '检查质量门禁失败');
    return { success: true, data };
  }

  /**
   * 创建新的覆盖率报告
   */
  async createCoverageReport(
    report: Omit<CoverageReport, 'generated_at'>
  ): Promise<StandardApiResponse<{ report_id: number }>> {
    const result = await apiClient.post<{ report_id: number }>(`${this.baseUrl}/report`, report, {
      retry: false,
    });
    const data = this.unwrapResult(result, '创建覆盖率报告失败');
    return { success: true, data };
  }

  /**
   * 删除覆盖率报告
   */
  async deleteCoverageReport(reportId: number): Promise<StandardApiResponse<null>> {
    const result = await apiClient.delete(`${this.baseUrl}/reports/${reportId}`, {
      retry: false,
    });
    this.ensureSuccess(result, '删除覆盖率报告失败');
    return {
      success: true,
      data: null,
    };
  }

  /**
   * 获取测试执行报告
   */
  async getTestExecutionReport(
    executionId?: string
  ): Promise<StandardApiResponse<TestExecutionReport[]>> {
    const url =
      executionId !== null && executionId !== undefined && executionId !== ''
        ? `${this.baseUrl}/test-execution/${executionId}`
        : `${this.baseUrl}/test-execution`;
    const result = await apiClient.get<TestExecutionReport[]>(url, {
      retry: false,
    });
    const data = this.unwrapResult(result, '获取测试执行报告失败');
    return { success: true, data };
  }

  /**
   * 获取缺陷报告列表
   */
  async getDefectReports(params?: {
    severity?: string;
    status?: string;
    category?: string;
    module?: string;
    page_size?: number;
    offset?: number;
  }): Promise<StandardApiResponse<{ defects: DefectReport[]; total: number }>> {
    const result = await apiClient.get<{ defects: DefectReport[]; total: number }>(
      `${this.baseUrl}/defects`,
      {
        params,
        retry: false,
      }
    );
    const data = this.unwrapResult(result, '获取缺陷报告失败');
    return { success: true, data };
  }

  /**
   * 创建缺陷报告
   */
  async createDefectReport(
    defect: Omit<DefectReport, 'defect_id' | 'created_at' | 'updated_at'>
  ): Promise<StandardApiResponse<DefectReport>> {
    const result = await apiClient.post<DefectReport>(`${this.baseUrl}/defects`, defect, {
      retry: false,
    });
    const data = this.unwrapResult(result, '创建缺陷报告失败');
    return { success: true, data };
  }

  /**
   * 更新缺陷报告
   */
  async updateDefectReport(
    defectId: string,
    updates: Partial<DefectReport>
  ): Promise<StandardApiResponse<DefectReport>> {
    const result = await apiClient.put<DefectReport>(
      `${this.baseUrl}/defects/${defectId}`,
      updates,
      {
        retry: false,
      }
    );
    const data = this.unwrapResult(result, '更新缺陷报告失败');
    return { success: true, data };
  }

  /**
   * 获取测试覆盖率统计摘要
   */
  async getCoverageSummary(): Promise<
    StandardApiResponse<{
      overall_coverage: number;
      backend_coverage: number;
      frontend_coverage: number;
      total_modules: number;
      modules_above_threshold: number;
      modules_below_threshold: number;
      total_tests: number;
      pass_rate: number;
      average_execution_time: number;
      trend_direction: 'improving' | 'declining' | 'stable';
    }>
  > {
    const result = await apiClient.get<{
      overall_coverage: number;
      backend_coverage: number;
      frontend_coverage: number;
      total_modules: number;
      modules_above_threshold: number;
      modules_below_threshold: number;
      total_tests: number;
      pass_rate: number;
      average_execution_time: number;
      trend_direction: 'improving' | 'declining' | 'stable';
    }>(`${this.baseUrl}/summary`, {
      retry: false,
    });
    const data = this.unwrapResult(result, '获取覆盖率摘要失败');
    return { success: true, data };
  }

  /**
   * 获取测试性能分析报告
   */
  async getTestPerformanceAnalysis(params?: {
    module?: string;
    time_range?: string;
    sort_by?: 'execution_time' | 'memory_usage' | 'cpu_usage';
  }): Promise<
    StandardApiResponse<{
      slow_tests: TestPerformanceMetrics[];
      memory_intensive_tests: TestPerformanceMetrics[];
      cpu_intensive_tests: TestPerformanceMetrics[];
      performance_trends: Array<{
        date: string;
        avg_execution_time: number;
        avg_memory_usage: number;
      }>;
      recommendations: string[];
    }>
  > {
    const result = await apiClient.get<{
      slow_tests: TestPerformanceMetrics[];
      memory_intensive_tests: TestPerformanceMetrics[];
      cpu_intensive_tests: TestPerformanceMetrics[];
      performance_trends: Array<{
        date: string;
        avg_execution_time: number;
        avg_memory_usage: number;
      }>;
      recommendations: string[];
    }>(`${this.baseUrl}/performance-analysis`, {
      params,
      retry: false,
    });
    const data = this.unwrapResult(result, '获取测试性能分析失败');
    return { success: true, data };
  }

  /**
   * 触发测试覆盖率扫描
   */
  async triggerCoverageScan(options?: {
    backend?: boolean;
    frontend?: boolean;
    specific_modules?: string[];
    parallel?: boolean;
  }): Promise<
    StandardApiResponse<{
      scan_id: string;
      status: 'started' | 'queued';
      estimated_duration: number;
    }>
  > {
    const result = await apiClient.post<{
      scan_id: string;
      status: 'started' | 'queued';
      estimated_duration: number;
    }>(`${this.baseUrl}/trigger-scan`, options ?? {}, {
      retry: false,
    });
    const data = this.unwrapResult(result, '触发覆盖率扫描失败');
    return { success: true, data };
  }

  /**
   * 获取扫描状态
   */
  async getScanStatus(scanId: string): Promise<
    StandardApiResponse<{
      scan_id: string;
      status: 'running' | 'completed' | 'failed' | 'cancelled';
      progress: number;
      current_step: string;
      estimated_remaining_time?: number;
      result?: CoverageReport;
      error_message?: string;
    }>
  > {
    const result = await apiClient.get<{
      scan_id: string;
      status: 'running' | 'completed' | 'failed' | 'cancelled';
      progress: number;
      current_step: string;
      estimated_remaining_time?: number;
      result?: CoverageReport;
      error_message?: string;
    }>(`${this.baseUrl}/scan-status/${scanId}`, {
      retry: false,
    });
    const data = this.unwrapResult(result, '获取扫描状态失败');
    return { success: true, data };
  }
}

// 导出服务实例
export const testCoverageService = new TestCoverageService();

// 导出默认实例
export default testCoverageService;
