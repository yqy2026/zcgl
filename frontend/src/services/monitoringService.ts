/**
 * 系统监控服务 - 前端API服务层
 *
 * 提供系统监控相关的API调用和数据处理功能
 *
 * @author Claude Code
 * @created 2025-11-01
 */

import { apiClient } from './apiClient'

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
  private readonly baseUrl = '/api/v1/monitoring'

  /**
   * 获取系统性能指标
   */
  async getSystemMetrics(): Promise<SystemMetrics> {
    try {
      const response = await apiClient.get(`/api/v1/system-metrics`)
      return response.data
    } catch (error) {
      console.error('操作失败:', error)
      throw new Error(error instanceof Error ? error.message : '操作失败')
    }
  }

  /**
   * 获取应用性能指标
   */
  async getApplicationMetrics(): Promise<ApplicationMetrics> {
    const response = await apiClient.get(`/api/v1/application-metrics`)
    return response.data
  }

  /**
   * 获取系统健康状态
   */
  async getHealthStatus(): Promise<HealthStatus> {
    const response = await apiClient.get(`/api/v1/health`)
    return response.data
  }

  /**
   * 获取系统指标历史数据
   */
  async getMetricsHistory(hours: number = 24): Promise<SystemMetrics[]> {
    const response = await apiClient.get(`/api/v1/metrics/history`, {
      params: { hours }
    })
    return response.data
  }

  /**
   * 获取性能告警列表
   */
  async getPerformanceAlerts(params?: {
    level?: 'info' | 'warning' | 'critical'
    resolved?: boolean
  }): Promise<PerformanceAlert[]> {
    const response = await apiClient.get(`/api/v1/alerts`, { params })
    return response.data
  }

  /**
   * 解决告警
   */
  async resolveAlert(alertId: string): Promise<{ message: string; success: boolean }> {
    const response = await apiClient.post(`/api/v1/alerts/${alertId}/resolve`)
    return response.data
  }

  /**
   * 获取监控仪表板数据
   */
  async getDashboardData(): Promise<DashboardData> {
    const response = await apiClient.get(`/api/v1/dashboard`)
    return response.data
  }

  /**
   * 手动触发指标收集
   */
  async triggerMetricsCollection(): Promise<MetricsCollectionResult> {
    const response = await apiClient.post(`/api/v1/metrics/collect`)
    return response.data
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
    const response = await apiClient.get(`/api/v1/service/status`)
    return response.data
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
    const response = await apiClient.put(`/api/v1/config`, config)
    return response.data
  }

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
    const response = await apiClient.post(`/api/v1/export`, params, {
      responseType: 'blob'
    })
    return response.data
  }

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
    const response = await apiClient.get(`/api/v1/reports/performance`, {
      params: { timeRange }
    })
    return response.data
  }

  /**
   * 获取组件健康详情
   */
  async getComponentHealth(componentName?: string): Promise<{
    component: string
    status: string
    metrics: Record<string, any>
    history: Array<{
      timestamp: string
      status: string
      metrics: Record<string, any>
    }>
    issues: Array<{
      type: string
      severity: 'high' | 'medium' | 'low'
      description: string
      first_seen: string
      last_seen: string
    }>
  }> {
    const params = componentName ? { component: componentName } : {}
    const response = await apiClient.get(`/api/v1/components/health`, { params })
    return response.data
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
    const response = await apiClient.post(`/api/v1/alerts/rules`, rule)
    return response.data
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
    const response = await apiClient.get(`/api/v1/alerts/rules`)
    return response.data
  }

  /**
   * 删除告警规则
   */
  async deleteAlertRule(ruleId: string): Promise<{ message: string; success: boolean }> {
    const response = await apiClient.delete(`/api/v1/alerts/rules/${ruleId}`)
    return response.data
  }
}

// 导出单例实例
export const monitoringService = new MonitoringService()

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
}
