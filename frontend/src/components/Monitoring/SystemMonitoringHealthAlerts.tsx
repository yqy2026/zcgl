import React, { useCallback, useMemo } from 'react';
import { Card, Row, Col, Tag, List, Badge, Button, Space } from 'antd';
import { AlertOutlined } from '@ant-design/icons';
import { Gauge } from '@ant-design/plots';

import {
  getAlertLevelColor,
  getStatusColor,
  type DashboardData,
  type HealthStatus,
  type PerformanceAlert,
} from './systemMonitoringTypes';

interface SystemMonitoringHealthAlertsProps {
  healthStatus?: HealthStatus;
  summary?: DashboardData['summary'];
  alerts: PerformanceAlert[];
  onResolveAlert: (alertId: string) => void;
  isResolving: boolean;
}

const SystemMonitoringHealthAlerts: React.FC<SystemMonitoringHealthAlertsProps> = ({
  healthStatus,
  summary,
  alerts,
  onResolveAlert,
  isResolving,
}) => {
  const healthGaugeConfig = useMemo(
    () => ({
      percent: (healthStatus?.overall_score ?? 0) / 100,
      color: getStatusColor(healthStatus?.status ?? 'unknown'),
      indicator: {
        pointer: { style: { stroke: '#D0D0D0' } },
        pin: { style: { stroke: '#D0D0D0' } },
      },
      statistic: {
        content: {
          style: { fontSize: '36px', lineHeight: '36px' },
          formatter: () => `${healthStatus?.overall_score ?? 0}%`,
        },
      },
    }),
    [healthStatus]
  );

  const alertItems = useMemo(() => alerts.slice(0, 5), [alerts]);

  const renderAlertItem = useCallback(
    (alert: PerformanceAlert) => {
      const actions = alert.resolved
        ? []
        : [
            <Button
              key={`resolve-${alert.id}`}
              size="small"
              type="text"
              onClick={() => onResolveAlert(alert.id)}
              loading={isResolving}
            >
              解决
            </Button>,
          ];

      return (
        <List.Item actions={actions}>
          <List.Item.Meta
            avatar={<Badge dot={!alert.resolved} color={getAlertLevelColor(alert.level)} />}
            title={
              <Space>
                <Tag color={getAlertLevelColor(alert.level)}>{alert.level.toUpperCase()}</Tag>
                <span>{alert.metric_name}</span>
              </Space>
            }
            description={alert.message}
          />
        </List.Item>
      );
    },
    [isResolving, onResolveAlert]
  );

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col span={8}>
        <Card title="系统健康状态" size="small">
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <Gauge {...healthGaugeConfig} height={200} />
            <div style={{ marginTop: 16 }}>
              <Tag color={getStatusColor(healthStatus?.status ?? 'unknown')}>
                {(healthStatus?.status ?? 'unknown').toUpperCase()}
              </Tag>
            </div>
          </div>
        </Card>
      </Col>
      <Col span={16}>
        <Card
          title={
            <Space>
              <AlertOutlined />
              活跃告警
              <Badge count={summary?.total_alerts ?? 0} />
            </Space>
          }
          size="small"
        >
          <List
            size="small"
            dataSource={alertItems}
            renderItem={renderAlertItem}
            locale={{ emptyText: '暂无告警' }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default React.memo(SystemMonitoringHealthAlerts);
