/**
 * 系统监控仪表板组件
 *
 * 功能特性:
 * - 实时系统性能监控
 * - 应用性能指标展示
 * - 健康状态检查
 * - 告警管理
 * - 性能趋势分析
 *
 * @author Claude Code
 * @created 2025-11-01
 */

import React, { useState, useCallback } from 'react';
import { Alert, Button } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { monitoringService } from '@/services/monitoringService';
import type { DashboardData } from './systemMonitoringTypes';
import SystemMonitoringHeader from './SystemMonitoringHeader';
import SystemMonitoringOverview from './SystemMonitoringOverview';
import SystemMonitoringHealthAlerts from './SystemMonitoringHealthAlerts';
import SystemMonitoringTrendCharts from './SystemMonitoringTrendCharts';
import SystemMonitoringDetails from './SystemMonitoringDetails';

const SystemMonitoringDashboard: React.FC = () => {
  const [refreshInterval, _setRefreshInterval] = useState(30000); // 30秒刷新
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [_selectedTimeRange, _setSelectedTimeRange] = useState(24); // 小时

  const queryClient = useQueryClient();

  // 获取仪表板数据
  const {
    data: dashboardData,
    isLoading,
    error,
    refetch,
  } = useQuery<DashboardData>({
    queryKey: ['monitoring-dashboard'],
    queryFn: () => monitoringService.getDashboardData(),
    refetchInterval: autoRefresh ? refreshInterval : false,
    retry: 3,
    retryDelay: 1000,
  });

  // 手动刷新
  const handleRefresh = useCallback(() => {
    void refetch();
  }, [refetch]);

  const handleToggleAutoRefresh = useCallback(() => {
    setAutoRefresh(prev => !prev);
  }, []);

  // 解决告警
  const resolveAlertMutation = useMutation({
    mutationFn: (alertId: string) => monitoringService.resolveAlert(alertId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['monitoring-dashboard'] });
    },
  });

  const handleResolveAlert = useCallback(
    (alertId: string) => {
      resolveAlertMutation.mutate(alertId);
    },
    [resolveAlertMutation]
  );

  if (error != null) {
    return (
      <Alert
        message="监控数据加载失败"
        description="无法获取系统监控数据，请检查网络连接或联系管理员"
        type="error"
        showIcon
        action={
          <Button size="small" onClick={handleRefresh}>
            重试
          </Button>
        }
      />
    );
  }

  return (
    <div className="system-monitoring-dashboard">
      <SystemMonitoringHeader
        autoRefresh={autoRefresh}
        onToggleAutoRefresh={handleToggleAutoRefresh}
        onRefresh={handleRefresh}
        isRefreshing={isLoading}
        status={dashboardData?.health_status?.status}
      />

      <SystemMonitoringOverview
        system={dashboardData?.current_system}
        application={dashboardData?.current_application}
      />

      <SystemMonitoringHealthAlerts
        healthStatus={dashboardData?.health_status}
        summary={dashboardData?.summary}
        alerts={dashboardData?.active_alerts ?? []}
        onResolveAlert={handleResolveAlert}
        isResolving={resolveAlertMutation.isPending}
      />

      <SystemMonitoringTrendCharts
        systemMetrics={dashboardData?.trends?.system_metrics ?? []}
        applicationMetrics={dashboardData?.trends?.application_metrics ?? []}
      />

      <SystemMonitoringDetails
        system={dashboardData?.current_system}
        application={dashboardData?.current_application}
      />
    </div>
  );
};

export default React.memo(SystemMonitoringDashboard);
