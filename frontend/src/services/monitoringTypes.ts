/**
 * 系统监控服务 - 类型定义
 *
 * 所有监控相关的 TypeScript 接口定义
 *
 * @author Claude Code
 * @created 2025-11-01
 * @refactored 2026-03-16 — 从 monitoringService.ts 拆分
 */

export interface SystemMetrics {
  timestamp: string;
  cpu_percent: number;
  memory_percent: number;
  memory_available_gb: number;
  disk_usage_percent: number;
  disk_free_gb: number;
  network_io: Record<string, number>;
  process_count: number;
  load_average?: number[];
}

export interface ApplicationMetrics {
  timestamp: string;
  active_connections: number;
  total_requests: number;
  average_response_time: number;
  error_rate: number;
  cache_hit_rate: number;
  database_connections: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  components: Record<
    string,
    {
      status: string;
      response_time_ms?: number;
      hit_rate?: number;
      usage_percent?: number;
      free_gb?: number;
      available_gb?: number;
      last_check: string;
      details?: string;
      error?: string;
    }
  >;
  overall_score: number;
}

export interface PerformanceAlert {
  id: string;
  level: 'info' | 'warning' | 'critical';
  message: string;
  metric_name: string;
  current_value: number;
  threshold: number;
  timestamp: string;
  resolved: boolean;
}

export interface DashboardData {
  current_system: SystemMetrics;
  current_application: ApplicationMetrics;
  health_status: HealthStatus;
  active_alerts: PerformanceAlert[];
  trends: {
    system_metrics: SystemMetrics[];
    application_metrics: ApplicationMetrics[];
  };
  summary: {
    total_alerts: number;
    critical_alerts: number;
    warning_alerts: number;
    health_score: number;
    last_updated: string;
  };
}

export interface MetricsCollectionResult {
  message: string;
  system_metrics: SystemMetrics;
  application_metrics: ApplicationMetrics;
  new_alerts_count: number;
  timestamp: string;
}

export interface TrendAnalysis {
  metric_name: string;
  current_value: number;
  avg_value_1h: number;
  avg_value_24h: number;
  trend_direction: 'up' | 'down' | 'stable';
  trend_percent: number;
  prediction_1h?: number;
  status: 'normal' | 'warning' | 'critical';
}

export interface PerformanceSummary {
  time_range_hours: number;
  data_points: {
    system: number;
    application: number;
  };
  system_metrics: {
    cpu: { avg: number; max: number; min: number };
    memory: { avg: number; max: number; min: number };
    disk: { avg: number; max: number; min: number };
  };
  application_metrics: {
    response_time: { avg: number; max: number; min: number };
    error_rate: { avg: number; max: number; min: number };
    cache_hit_rate: { avg: number; max: number; min: number };
  };
  alerts: {
    total: number;
    critical: number;
    warning: number;
    info: number;
    resolved: number;
  };
  generated_at: string;
}
