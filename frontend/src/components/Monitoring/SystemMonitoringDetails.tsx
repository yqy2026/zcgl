import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';

import { getStatusColor, type ApplicationMetrics, type SystemMetrics } from './systemMonitoringTypes';

interface SystemMonitoringDetailsProps {
  system?: SystemMetrics;
  application?: ApplicationMetrics;
}

const SystemMonitoringDetails: React.FC<SystemMonitoringDetailsProps> = ({
  system,
  application,
}) => {
  return (
    <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
      <Col span={12}>
        <Card title="系统详细信息" size="small">
          <Row gutter={[16, 8]}>
            <Col span={12}>
              <Statistic
                title="可用内存"
                value={system?.memory_available_gb ?? 0}
                suffix="GB"
                precision={1}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="可用磁盘"
                value={system?.disk_free_gb ?? 0}
                suffix="GB"
                precision={1}
              />
            </Col>
            <Col span={12}>
              <Statistic title="进程数" value={system?.process_count ?? 0} />
            </Col>
            <Col span={12}>
              <Statistic title="系统负载" value={system?.load_average?.[0] ?? 0} precision={2} />
            </Col>
          </Row>
        </Card>
      </Col>
      <Col span={12}>
        <Card title="应用详细信息" size="small">
          <Row gutter={[16, 8]}>
            <Col span={12}>
              <Statistic title="总请求数" value={application?.total_requests ?? 0} />
            </Col>
            <Col span={12}>
              <Statistic
                title="平均响应时间"
                value={application?.average_response_time ?? 0}
                suffix="ms"
                precision={1}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="错误率"
                value={application?.error_rate ?? 0}
                suffix="%"
                precision={2}
                valueStyle={{
                  color: getStatusColor((application?.error_rate ?? 0) > 5 ? 'critical' : 'normal'),
                }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="缓存命中率"
                value={application?.cache_hit_rate ?? 0}
                suffix="%"
                precision={1}
              />
            </Col>
          </Row>
        </Card>
      </Col>
    </Row>
  );
};

export default React.memo(SystemMonitoringDetails);
