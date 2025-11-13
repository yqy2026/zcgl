/**
 * 系统监控服务 - 前端API服务层 - 统一响应处理版本
 *
 * 提供系统监控相关的API调用和数据处理功能
 *
 * @author Claude Code
 * @created 2025-11-01
 * @updated 2025-11-10
 */

import { enhancedApiClient } from './enhancedApiClient';
import { ApiErrorHandler } from '../utils/responseExtractor';

// 类型定义
export interface SystemMetrics {
  timestamp: string
  cpu_percent: number
  memory_percent: number
  memory_available_gb: number
  disk_usage_percent: number
  disk_free_gb: number
  network_io: Record<string, number>
  process_count: number
  load_average?: number[]
}

export interface ApplicationMetrics {
  timestamp: string
  active_connections: number
  total_requests: number
  average_response_time: number
  error_rate: number
  cache_hit_rate: number
  database_connections: number
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  components: Record<string, {
    status: string
    response_time_ms?: number
    hit_rate?: number
    usage_percent?: number
    free_gb?: number
    available_gb?: number
    last_check: string
    details?: string
    error?: string
  }>
  overall_score: number
}

export interface PerformanceAlert {
  id: string
  level: 'info' | 'warning' | 'critical'
  message: string
  metric_name: string
  current_value: number
  threshold: number
  timestamp: string
  resolved: boolean
}

export interface DashboardData {
  current_system: SystemMetrics
  current_application: ApplicationMetrics
  health_status: HealthStatus
  active_alerts: PerformanceAlert[]
  trends: {
    system_metrics: SystemMetrics[]
    application_metrics: ApplicationMetrics[]
  }
  summary: {
    total_alerts: number
    critical_alerts: number
    warning_alerts: number
    health_score: number
    last_updated: string
  }
}

export interface MetricsCollectionResult {
  message: string
  system_metrics: SystemMetrics
  application_metrics: ApplicationMetrics
  new_alerts_count: number
  timestamp: string
}

export interface TrendAnalysis {
  metric_name: string
  current_value: number
  avg_value_1h: number
  avg_value_24h: number
  trend_direction: 'up' | 'down' | 'stable'
  trend_percent: number
  prediction_1h?: number
  status: 'normal' | 'warning' | 'critical'
}

export interface PerformanceSummary {
  time_range_hours: number
  data_points: {
    system: number
    application: number
  }
  system_metrics: {
    cpu: { avg: number; max: number; min: number }
    memory: { avg: number; max: number; min: number }
    disk: { avg: number; max: number; min: number }
  }
  application_metrics: {
    response_time: { avg: number; max: number; min: number }
    error_rate: { avg: number; max: number; min: number }
    cache_hit_rate: { avg: number; max: number; min: number }
  }
  alerts: {
    total: number
    critical: number
    warning: number
    info: number
    resolved: number
  }
  generated_at: string
}

/**
 * 系统监控服务类
 */
export class MonitoringService {
  private readonly baseUrl = '/api/monitoring';

  // ==================== 系统指标 ====================

  /**
   * 获取系统性能指标
   */
  async getSystemMetrics(): Promise<SystemMetrics> {
    try {
      const result = await enhancedApiClient.get<SystemMetrics>(
        '/api/system-metrics',
        {
          cache: false, // 系统指标不缓存，需要实时数据
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取系统性能指标失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取应用性能指标
   */
  async getApplicationMetrics(): Promise<ApplicationMetrics> {
    try {
      const result = await enhancedApiClient.get<ApplicationMetrics>(
        '/api/application-metrics',
        {
          cache: false, // 应用指标不缓存，需要实时数据
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取应用性能指标失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取系统健康状态
   */
  async getHealthStatus(): Promise<HealthStatus> {
    try {
      const result = await enhancedApiClient.get<HealthStatus>(
        '/api/health',
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取系统健康状态失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 历史数据 ====================

  /**
   * 获取系统指标历史数据
   */
  async getMetricsHistory(hours: number = 24): Promise<SystemMetrics[]> {
    try {
      const result = await enhancedApiClient.get<SystemMetrics[]>(
        '/api/metrics/history',
        {
          params: { hours },
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取系统指标历史数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 告警管理 ====================

  /**
   * 获取性能告警列表
   */
  async getPerformanceAlerts(params?: {
    level?: 'info' | 'warning' | 'critical'
    resolved?: boolean
  }): Promise<PerformanceAlert[]> {
    try {
      const result = await enhancedApiClient.get<PerformanceAlert[]>(
        '/api/alerts',
        {
          params,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取性能告警列表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 解决告警
   */
  async resolveAlert(alertId: string): Promise<{ message: string; success: boolean }> {
    try {
      const result = await enhancedApiClient.post<{ message: string; success: boolean }>(
        `/api/alerts/${alertId}/resolve`,
        {},
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`解决告警失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 创建自定义告警规则
   */
  async createAlertRule(rule: {
    name: string
    description: string
    metric_name: string
    condition: 'greater_than' | 'less_than' | 'equals'
    threshold: number
    severity: 'info' | 'warning' | 'critical'
    enabled: boolean
    notification_channels?: string[]
  }): Promise<{ message: string; rule_id: string }> {
    try {
      const result = await enhancedApiClient.post<{ message: string; rule_id: string }>(
        '/api/alerts/rules',
        rule,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`创建告警规则失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取告警规则列表
   */
  async getAlertRules(): Promise<Array<{
    id: string
    name: string
    description: string
    metric_name: string
    condition: string
    threshold: number
    severity: string
    enabled: boolean
    created_at: string
    last_triggered?: string
  }>> {
    try {
      const result = await enhancedApiClient.get<Array<{
        id: string
        name: string
        description: string
        metric_name: string
        condition: string
        threshold: number
        severity: string
        enabled: boolean
        created_at: string
        last_triggered?: string
      }>>(
        '/api/alerts/rules',
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取告警规则列表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 删除告警规则
   */
  async deleteAlertRule(ruleId: string): Promise<{ message: string; success: boolean }> {
    try {
      const result = await enhancedApiClient.delete<{ message: string; success: boolean }>(
        `/api/alerts/rules/${ruleId}`,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`删除告警规则失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 仪表板数据 ====================

  /**
   * 获取监控仪表板数据
   */
  async getDashboardData(): Promise<DashboardData> {
    try {
      const result = await enhancedApiClient.get<DashboardData>(
        '/api/dashboard',
        {
          cache: false, // 仪表板数据需要实时
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取监控仪表板数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 系统管理 ====================

  /**
   * 手动触发指标收集
   */
  async triggerMetricsCollection(): Promise<MetricsCollectionResult> {
    try {
      const result = await enhancedApiClient.post<MetricsCollectionResult>(
        '/api/metrics/collect',
        {},
        {
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`触发指标收集失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取系统服务状态
   */
  async getServiceStatus(): Promise<{
    is_running: boolean
    collection_interval: number
    data_points: {
      system_metrics: number
      application_metrics: number
      alerts: number
    }
    config: {
      collection_interval: number
      history_retention_hours: number
      alert_threshold_cpu: number
      alert_threshold_memory: number
      alert_threshold_disk: number
      alert_threshold_response_time: number
      alert_threshold_error_rate: number
      enable_auto_collection: boolean
      enable_alerting: boolean
    }
    data_directory: string
    last_collection?: string
  }> {
    try {
      const result = await enhancedApiClient.get<{
        is_running: boolean
        collection_interval: number
        data_points: {
          system_metrics: number
          application_metrics: number
          alerts: number
        }
        config: {
          collection_interval: number
          history_retention_hours: number
          alert_threshold_cpu: number
          alert_threshold_memory: number
          alert_threshold_disk: number
          alert_threshold_response_time: number
          alert_threshold_error_rate: number
          enable_auto_collection: boolean
          enable_alerting: boolean
        }
        data_directory: string
        last_collection?: string
      }>(
        '/api/service/status',
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取系统服务状态失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新监控配置
   */
  async updateMonitoringConfig(config: {
    collection_interval?: number
    alert_threshold_cpu?: number
    alert_threshold_memory?: number
    alert_threshold_disk?: number
    alert_threshold_response_time?: number
    alert_threshold_error_rate?: number
    enable_auto_collection?: boolean
    enable_alerting?: boolean
  }): Promise<{ message: string; success: boolean }> {
    try {
      const result = await enhancedApiClient.put<{ message: string; success: boolean }>(
        '/api/config',
        config,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`更新监控配置失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 数据导出 ====================

  /**
   * 导出监控数据
   */
  async exportMonitoringData(params: {
    format: 'json' | 'csv' | 'excel'
    start_date: string
    end_date: string
    include_system_metrics: boolean
    include_application_metrics: boolean
    include_alerts: boolean
  }): Promise<Blob> {
    try {
      const result = await enhancedApiClient.get<Blob>(
        '/api/export',
        {
          params,
          responseType: 'blob',
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 }
        }
      );

      if (!result.success) {
        throw new Error(`导出监控数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 性能分析 ====================

  /**
   * 获取性能分析报告
   */
  async getPerformanceReport(timeRange: number = 24): Promise<{
    summary: PerformanceSummary
    trends: TrendAnalysis[]
    recommendations: string[]
    top_issues: Array<{
      metric: string
      severity: 'high' | 'medium' | 'low'
      description: string
      impact: string
      recommendation: string
    }>
  }> {
    try {
      const result = await enhancedApiClient.get<{
        summary: PerformanceSummary
        trends: TrendAnalysis[]
        recommendations: string[]
        top_issues: Array<{
          metric: string
          severity: 'high' | 'medium' | 'low'
          description: string
          impact: string
          recommendation: string
        }>
      }>(
        '/api/reports/performance',
        {
          params: { timeRange },
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取性能分析报告失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取组件健康详情
   */
  async getComponentHealth(componentName?: string): Promise<{
    component: string
    status: string
    metrics: Record<string, number | string | boolean | null>
    history: Array<{
      timestamp: string
      status: string
      metrics: Record<string, number | string | boolean | null>
    }>
    issues: Array<{
      type: string
      severity: 'high' | 'medium' | 'low'
      description: string
      first_seen: string
      last_seen: string
    }>
  }> {
    try {
      const params = componentName ? { component: componentName } : {};
      const result = await enhancedApiClient.get<{
        component: string
        status: string
        metrics: Record<string, number | string | boolean | null>
        history: Array<{
          timestamp: string
          status: string
          metrics: Record<string, number | string | boolean | null>
        }>
        issues: Array<{
          type: string
          severity: 'high' | 'medium' | 'low'
          description: string
          first_seen: string
          last_seen: string
        }>
      }>(
        '/api/components/health',
        {
          params,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取组件健康详情失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 实时监控 ====================

  /**
   * 获取实时系统状态（简化版）
   */
  async getRealTimeStatus(): Promise<{
    cpu: number
    memory: number
    disk: number
    response_time: number
    error_rate: number
    health_score: number
    active_alerts: number
  }> {
    try {
      const [systemMetrics, appMetrics, healthStatus, alerts] = await Promise.all([
        this.getSystemMetrics(),
        this.getApplicationMetrics(),
        this.getHealthStatus(),
        this.getPerformanceAlerts({ resolved: false })
      ]);

      return {
        cpu: systemMetrics.cpu_percent,
        memory: systemMetrics.memory_percent,
        disk: systemMetrics.disk_usage_percent,
        response_time: appMetrics.average_response_time,
        error_rate: appMetrics.error_rate,
        health_score: healthStatus.overall_score,
        active_alerts: alerts.length
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(`获取实时系统状态失败: ${enhancedError.message}`);
    }
  }

  /**
   * 检查系统是否健康
   */
  async isSystemHealthy(): Promise<boolean> {
    try {
      const healthStatus = await this.getHealthStatus();
      return healthStatus.status === 'healthy' && healthStatus.overall_score >= 80;
    } catch (error) {
      console.warn('检查系统健康状态失败:', error);
      return false;
    }
  }

  /**
   * 获取关键告警数量
   */
  async getCriticalAlertsCount(): Promise<number> {
    try {
      const alerts = await this.getPerformanceAlerts({
        level: 'critical',
        resolved: false
      });
      return alerts.length;
    } catch (error) {
      console.warn('获取关键告警数量失败:', error);
      return 0;
    }
  }
}

// 导出单例实例
export const monitoringService = new MonitoringService();

// 导出类型
export type {
  SystemMetrics,
  ApplicationMetrics,
  HealthStatus,
  PerformanceAlert,
  DashboardData,
  MetricsCollectionResult,
  TrendAnalysis,
  PerformanceSummary
};