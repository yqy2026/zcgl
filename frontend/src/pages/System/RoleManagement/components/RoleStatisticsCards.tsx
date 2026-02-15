import React from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import { KeyOutlined, SafetyOutlined, SettingOutlined, TeamOutlined } from '@ant-design/icons';
import type { RoleStatistics } from '../types';
import styles from '../../RoleManagementPage.module.css';

interface RoleStatisticsCardsProps {
  statistics: RoleStatistics;
}

const RoleStatisticsCards: React.FC<RoleStatisticsCardsProps> = ({ statistics }) => {
  return (
    <Row gutter={[16, 16]} className={styles.statsRow}>
      <Col xs={24} sm={12} xl={6}>
        <Card className={styles.statsCard}>
          <Statistic title="总角色数" value={statistics.total} prefix={<TeamOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card className={`${styles.statsCard} ${styles.toneSuccess}`}>
          <Statistic title="启用角色" value={statistics.active} prefix={<SafetyOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card className={`${styles.statsCard} ${styles.tonePrimary}`}>
          <Statistic title="系统角色" value={statistics.system} prefix={<SettingOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card className={styles.statsCard}>
          <Statistic
            title="平均权限数"
            value={statistics.avg_permissions}
            prefix={<KeyOutlined />}
            suffix="个"
          />
        </Card>
      </Col>
    </Row>
  );
};

export default RoleStatisticsCards;
