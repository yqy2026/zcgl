import React from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import { LockOutlined, SettingOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons';
import type { UserStatistics } from '../types';
import styles from '../../UserManagementPage.module.css';

interface UserStatisticsCardsProps {
  statistics: UserStatistics;
}

const UserStatisticsCards: React.FC<UserStatisticsCardsProps> = ({ statistics }) => {
  return (
    <Row gutter={[16, 16]} className={styles.statsRow}>
      <Col xs={24} sm={12} md={6}>
        <Card className={`${styles.statsCard} ${styles.tonePrimary}`}>
          <Statistic title="总用户数" value={statistics.total} prefix={<UserOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card className={`${styles.statsCard} ${styles.activeStatsCard}`}>
          <Statistic
            title="活跃用户"
            value={statistics.active}
            prefix={<TeamOutlined />}
            suffix={<span className={styles.totalSuffix}>/ {statistics.total}</span>}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card className={`${styles.statsCard} ${styles.inactiveStatsCard}`}>
          <Statistic title="停用用户" value={statistics.inactive} prefix={<SettingOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card className={`${styles.statsCard} ${styles.lockedStatsCard}`}>
          <Statistic title="锁定用户" value={statistics.locked} prefix={<LockOutlined />} />
        </Card>
      </Col>
    </Row>
  );
};

export default UserStatisticsCards;
