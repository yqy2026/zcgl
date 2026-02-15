import React from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import { ExclamationCircleOutlined, FileTextOutlined, SettingOutlined } from '@ant-design/icons';
import type { LogStatistics } from '@/services/systemService';
import type { Tone } from '../types';
import { getResponseTimeTone } from '../utils';
import styles from '../../OperationLogPage.module.css';

interface OperationLogStatisticsCardsProps {
  statistics: LogStatistics;
  resolveToneClassName: (tone: Tone) => string;
}

const OperationLogStatisticsCards: React.FC<OperationLogStatisticsCardsProps> = ({
  statistics,
  resolveToneClassName,
}) => {
  return (
    <Row gutter={[16, 16]} className={styles.statsRow}>
      <Col xs={24} sm={12} xl={6}>
        <Card className={`${styles.statsCard} ${styles.toneSuccess}`}>
          <Statistic title="今日操作" value={statistics.today} prefix={<FileTextOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card className={`${styles.statsCard} ${styles.tonePrimary}`}>
          <Statistic title="本周操作" value={statistics.this_week} prefix={<SettingOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card className={`${styles.statsCard} ${styles.toneError}`}>
          <Statistic
            title="错误数量"
            value={statistics.error_count}
            prefix={<ExclamationCircleOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card
          className={`${styles.statsCard} ${resolveToneClassName(
            getResponseTimeTone(statistics.avg_response_time)
          )}`}
        >
          <Statistic
            title="平均响应时间"
            value={statistics.avg_response_time}
            suffix="ms"
            prefix={<SettingOutlined />}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default OperationLogStatisticsCards;
