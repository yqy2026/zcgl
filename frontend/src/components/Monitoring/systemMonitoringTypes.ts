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
  components: Record<string, unknown>;
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

export interface ChartDataPoint {
  time: string;
  value: number;
  category?: string;
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

export const STATUS_COLORS = {
  healthy: '#52c41a',
  degraded: '#faad14',
  unhealthy: '#ff4d4f',
  normal: '#52c41a',
  warning: '#faad14',
  critical: '#ff4d4f',
} as const;

export const ALERT_LEVEL_COLORS = {
  info: '#1890ff',
  warning: '#faad14',
  critical: '#ff4d4f',
} as const;

export const getStatusColor = (status: string): string => {
  return STATUS_COLORS[status as keyof typeof STATUS_COLORS] ?? '#d9d9d9';
};

export const getAlertLevelColor = (level: string): string => {
  return ALERT_LEVEL_COLORS[level as keyof typeof ALERT_LEVEL_COLORS] ?? '#d9d9d9';
};
