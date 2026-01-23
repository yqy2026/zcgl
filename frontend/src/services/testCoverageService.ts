/**
 * 测试覆盖率监控服务
 * 提供测试覆盖率数据的API调用封装
 */

import { StandardApiResponse } from '@/types/apiResponse';

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
  private baseUrl = '/api/test-coverage';

  /**
   * 获取当前测试覆盖率报告
   */
  async getCurrentCoverageReport(): Promise<StandardApiResponse<CoverageReport>> {
    const response = await fetch(`${this.baseUrl}/report`);
    if (!response.ok) {
      throw new Error(`获取覆盖率报告失败: ${response.statusText}`);
    }
    const data = (await response.json()) as CoverageReport;
    return {
      success: true,
      data,
    };
  }

  /**
   * 获取覆盖率趋势数据
   */
  async getCoverageTrend(days: number = 30): Promise<StandardApiResponse<CoverageTrend[]>> {
    const response = await fetch(`${this.baseUrl}/trend?days=${days}`);
    if (!response.ok) {
      throw new Error(`获取覆盖率趋势失败: ${response.statusText}`);
    }
    const data = (await response.json()) as CoverageTrend[];
    return {
      success: true,
      data,
    };
  }

  /**
   * 获取模块覆盖率列表
   */
  async getModuleCoverage(
    minCoverage: number = 0,
    maxCoverage: number = 100
  ): Promise<StandardApiResponse<CoverageMetrics[]>> {
    const params = new URLSearchParams({
      min_coverage: minCoverage.toString(),
      max_coverage: maxCoverage.toString(),
    });
    const response = await fetch(`${this.baseUrl}/modules?${params}`);
    if (!response.ok) {
      throw new Error(`获取模块覆盖率失败: ${response.statusText}`);
    }
    const data = (await response.json()) as CoverageMetrics[];
    return {
      success: true,
      data,
    };
  }

  /**
   * 获取覆盖率阈值配置
   */
  async getCoverageThresholds(): Promise<StandardApiResponse<CoverageThreshold>> {
    const response = await fetch(`${this.baseUrl}/thresholds`);
    if (!response.ok) {
      throw new Error(`获取覆盖率阈值失败: ${response.statusText}`);
    }
    const data = (await response.json()) as CoverageThreshold;
    return {
      success: true,
      data,
    };
  }

  /**
   * 更新覆盖率阈值配置
   */
  async updateCoverageThresholds(
    thresholds: CoverageThreshold
  ): Promise<StandardApiResponse<CoverageThreshold>> {
    const response = await fetch(`${this.baseUrl}/thresholds`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(thresholds),
    });
    if (!response.ok) {
      throw new Error(`更新覆盖率阈值失败: ${response.statusText}`);
    }
    const data = (await response.json()) as CoverageThreshold;
    return {
      success: true,
      data,
    };
  }

  /**
   * 检查质量门禁状态
   */
  async checkQualityGate(): Promise<StandardApiResponse<QualityGateResult>> {
    const response = await fetch(`${this.baseUrl}/quality-gate`);
    if (!response.ok) {
      throw new Error(`检查质量门禁失败: ${response.statusText}`);
    }
    const data = (await response.json()) as QualityGateResult;
    return {
      success: true,
      data,
    };
  }

  /**
   * 创建新的覆盖率报告
   */
  async createCoverageReport(
    report: Omit<CoverageReport, 'generated_at'>
  ): Promise<StandardApiResponse<{ report_id: number }>> {
    const response = await fetch(`${this.baseUrl}/report`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(report),
    });
    if (!response.ok) {
      throw new Error(`创建覆盖率报告失败: ${response.statusText}`);
    }
    const data = (await response.json()) as { report_id: number };
    return {
      success: true,
      data,
    };
  }

  /**
   * 删除覆盖率报告
   */
  async deleteCoverageReport(reportId: number): Promise<StandardApiResponse<null>> {
    const response = await fetch(`${this.baseUrl}/reports/${reportId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`删除覆盖率报告失败: ${response.statusText}`);
    }
    return {
      success: true,
      data: null,
    };
  }

  /**
   * 获取测试执行报告
   */
  async getTestExecutionReport(executionId?: string): Promise<StandardApiResponse<TestExecutionReport[]>> {
    const url =
      executionId !== null && executionId !== undefined && executionId !== ''
        ? `${this.baseUrl}/test-execution/${executionId}`
        : `${this.baseUrl}/test-execution`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`获取测试执行报告失败: ${response.statusText}`);
    }
    const data = (await response.json()) as TestExecutionReport[];
    return {
      success: true,
      data,
    };
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
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, value.toString());
        }
      });
    }
    const url = `${this.baseUrl}/defects${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`获取缺陷报告失败: ${response.statusText}`);
    }
    const data = (await response.json()) as { defects: DefectReport[]; total: number };
    return {
      success: true,
      data,
    };
  }

  /**
   * 创建缺陷报告
   */
  async createDefectReport(
    defect: Omit<DefectReport, 'defect_id' | 'created_at' | 'updated_at'>
  ): Promise<StandardApiResponse<DefectReport>> {
    const response = await fetch(`${this.baseUrl}/defects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(defect),
    });
    if (!response.ok) {
      throw new Error(`创建缺陷报告失败: ${response.statusText}`);
    }
    const data = (await response.json()) as DefectReport;
    return {
      success: true,
      data,
    };
  }

  /**
   * 更新缺陷报告
   */
  async updateDefectReport(
    defectId: string,
    updates: Partial<DefectReport>
  ): Promise<StandardApiResponse<DefectReport>> {
    const response = await fetch(`${this.baseUrl}/defects/${defectId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      throw new Error(`更新缺陷报告失败: ${response.statusText}`);
    }
    const data = (await response.json()) as DefectReport;
    return {
      success: true,
      data,
    };
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
    const response = await fetch(`${this.baseUrl}/summary`);
    if (!response.ok) {
      throw new Error(`获取覆盖率摘要失败: ${response.statusText}`);
    }
    const data = (await response.json()) as {
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
    };
    return {
      success: true,
      data,
    };
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
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, value);
        }
      });
    }
    const url = `${this.baseUrl}/performance-analysis${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`获取测试性能分析失败: ${response.statusText}`);
    }
    const data = (await response.json()) as {
      slow_tests: TestPerformanceMetrics[];
      memory_intensive_tests: TestPerformanceMetrics[];
      cpu_intensive_tests: TestPerformanceMetrics[];
      performance_trends: Array<{
        date: string;
        avg_execution_time: number;
        avg_memory_usage: number;
      }>;
      recommendations: string[];
    };
    return {
      success: true,
      data,
    };
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
    const response = await fetch(`${this.baseUrl}/trigger-scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(options || {}),
    });
    if (!response.ok) {
      throw new Error(`触发覆盖率扫描失败: ${response.statusText}`);
    }
    const data = (await response.json()) as {
      scan_id: string;
      status: 'started' | 'queued';
      estimated_duration: number;
    };
    return {
      success: true,
      data,
    };
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
    const response = await fetch(`${this.baseUrl}/scan-status/${scanId}`);
    if (!response.ok) {
      throw new Error(`获取扫描状态失败: ${response.statusText}`);
    }
    const data = (await response.json()) as {
      scan_id: string;
      status: 'running' | 'completed' | 'failed' | 'cancelled';
      progress: number;
      current_step: string;
      estimated_remaining_time?: number;
      result?: CoverageReport;
      error_message?: string;
    };
    return {
      success: true,
      data,
    };
  }
}

// 导出服务实例
export const testCoverageService = new TestCoverageService();

// 导出默认实例
export default testCoverageService;
