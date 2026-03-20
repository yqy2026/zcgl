/**
 * 系统监控服务 - 统一导出入口（hub）
 *
 * 本文件作为 re-export hub 保持所有现有导入路径的向后兼容性。
 * 实际实现已拆分至:
 *   - ./monitoringTypes   (接口/类型定义)
 *   - ./monitoringMetrics (MonitoringService 类 + 单例)
 *
 * @author Claude Code
 * @created 2025-11-01
 * @refactored 2026-03-16 — 拆分为 hub + monitoringTypes + monitoringMetrics
 */

// Re-export types
export type {
  SystemMetrics,
  ApplicationMetrics,
  HealthStatus,
  PerformanceAlert,
  DashboardData,
  MetricsCollectionResult,
  TrendAnalysis,
  PerformanceSummary,
} from './monitoringTypes';

// Re-export service class and singleton
export { MonitoringService, monitoringService } from './monitoringMetrics';
