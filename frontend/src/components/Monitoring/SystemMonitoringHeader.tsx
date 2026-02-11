import React from 'react';
import { Row, Col, Space, Button, Tooltip, Tag } from 'antd';
import { MonitorOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';

import { getStatusColor } from './systemMonitoringTypes';
import styles from './SystemMonitoringHeader.module.css';

interface SystemMonitoringHeaderProps {
  autoRefresh: boolean;
  onToggleAutoRefresh: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  status?: string;
}

const SystemMonitoringHeader: React.FC<SystemMonitoringHeaderProps> = ({
  autoRefresh,
  onToggleAutoRefresh,
  onRefresh,
  isRefreshing,
  status,
}) => {
  return (
    <Row justify="space-between" align="middle" className={styles.headerRow}>
      <Col>
        <Space>
          <MonitorOutlined className={styles.monitorIcon} />
          <h2 className={styles.headerTitle}>系统监控仪表板</h2>
          {status != null && status !== '' && (
            <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
          )}
        </Space>
      </Col>
      <Col>
        <Space>
          <Tooltip title="自动刷新">
            <Button
              type={autoRefresh ? 'primary' : 'default'}
              size="small"
              onClick={onToggleAutoRefresh}
            >
              自动刷新: {autoRefresh ? '开启' : '关闭'}
            </Button>
          </Tooltip>
          <Button icon={<ReloadOutlined />} size="small" onClick={onRefresh} loading={isRefreshing}>
            刷新
          </Button>
          <Button
            icon={<SettingOutlined />}
            size="small"
            onClick={() => {
              /* 打开设置 */
            }}
          >
            设置
          </Button>
        </Space>
      </Col>
    </Row>
  );
};

export default React.memo(SystemMonitoringHeader);
