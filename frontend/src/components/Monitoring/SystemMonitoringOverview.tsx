import React from 'react';
import { Card, Row, Col, Statistic, Progress } from 'antd';

import {
  getStatusColor,
  type ApplicationMetrics,
  type SystemMetrics,
} from './systemMonitoringTypes';
import styles from './SystemMonitoringOverview.module.css';

interface SystemMonitoringOverviewProps {
  system?: SystemMetrics;
  application?: ApplicationMetrics;
}

const SystemMonitoringOverview: React.FC<SystemMonitoringOverviewProps> = ({
  system,
  application,
}) => {
  const cpuPercent = system?.cpu_percent ?? 0;
  const memoryPercent = system?.memory_percent ?? 0;
  const diskPercent = system?.disk_usage_percent ?? 0;
  const activeConnections = application?.active_connections ?? 0;

  return (
    <Row gutter={[16, 16]} className={styles.overviewRow}>
      <Col span={6}>
        <Card size="small">
          <Statistic
            title="CPU使用率"
            value={cpuPercent}
            suffix="%"
            styles={{
              content: {
                color: getStatusColor(cpuPercent > 80 ? 'critical' : 'normal'),
              },
            }}
          />
          <Progress
            percent={cpuPercent}
            showInfo={false}
            strokeColor={getStatusColor(cpuPercent > 80 ? 'critical' : 'normal')}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic
            title="内存使用率"
            value={memoryPercent}
            suffix="%"
            styles={{
              content: {
                color: getStatusColor(memoryPercent > 85 ? 'critical' : 'normal'),
              },
            }}
          />
          <Progress
            percent={memoryPercent}
            showInfo={false}
            strokeColor={getStatusColor(memoryPercent > 85 ? 'critical' : 'normal')}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic
            title="磁盘使用率"
            value={diskPercent}
            suffix="%"
            styles={{
              content: {
                color: getStatusColor(diskPercent > 90 ? 'critical' : 'normal'),
              },
            }}
          />
          <Progress
            percent={diskPercent}
            showInfo={false}
            strokeColor={getStatusColor(diskPercent > 90 ? 'critical' : 'normal')}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small">
          <Statistic
            title="活跃连接"
            value={activeConnections}
            styles={{ content: { color: 'var(--color-primary)' } }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default React.memo(SystemMonitoringOverview);
