import React from 'react';
import {
  ApartmentOutlined,
  PartitionOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Statistic } from 'antd';
import type { OrganizationStatistics } from '@/types/organization';
import styles from '../../OrganizationPage.module.css';

interface OrganizationStatisticsCardsProps {
  statistics: OrganizationStatistics;
}

const OrganizationStatisticsCards: React.FC<OrganizationStatisticsCardsProps> = ({
  statistics,
}) => {
  return (
    <Row gutter={16} className={styles.statsRow}>
      <Col xs={24} sm={12} md={6}>
        <Card className={styles.statsCard}>
          <Statistic title="总组织数" value={statistics.total} prefix={<ApartmentOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card className={`${styles.statsCard} ${styles.toneSuccess}`}>
          <Statistic title="活跃组织" value={statistics.active} prefix={<TeamOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card className={`${styles.statsCard} ${styles.toneError}`}>
          <Statistic title="停用组织" value={statistics.inactive} prefix={<SettingOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card className={styles.statsCard}>
          <Statistic
            title="组织类型"
            value={Object.keys(statistics.by_type ?? {}).length}
            prefix={<PartitionOutlined />}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default OrganizationStatisticsCards;
