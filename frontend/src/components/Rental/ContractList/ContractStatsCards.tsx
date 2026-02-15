import React from 'react';
import { Row, Col, Card, Statistic, Tag } from 'antd';
import { FileTextOutlined, DollarOutlined } from '@ant-design/icons';
import type { RentStatisticsOverview } from '@/types/rentContract';
import styles from './ContractStatsCards.module.css';

interface ContractStatsCardsProps {
  statistics: RentStatisticsOverview | null;
}

type Tone = 'primary' | 'success' | 'warning' | 'error';

const resolvePaymentRateTone = (paymentRate: number): Tone => {
  if (paymentRate >= 90) {
    return 'success';
  }
  if (paymentRate >= 70) {
    return 'warning';
  }
  return 'error';
};

const resolvePaymentRateLabel = (paymentRate: number): string => {
  if (paymentRate >= 90) {
    return '优';
  }
  if (paymentRate >= 70) {
    return '中';
  }
  return '低';
};

const ContractStatsCards: React.FC<ContractStatsCardsProps> = ({ statistics }) => {
  if (statistics == null) {
    return null;
  }

  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };
  const paymentRate = Number(statistics.payment_rate ?? 0);
  const paymentRateTone = resolvePaymentRateTone(paymentRate);
  const paymentRateLabel = resolvePaymentRateLabel(paymentRate);

  return (
    <Row gutter={[16, 16]} className={styles.statsRow}>
      <Col xs={24} sm={12} lg={6}>
        <Card className={[styles.metricCard, styles.tonePrimary].join(' ')}>
          <Statistic
            title="总合同数"
            value={statistics.total_records}
            prefix={<FileTextOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <Card className={[styles.metricCard, styles.tonePrimary].join(' ')}>
          <Statistic
            title="应收总额"
            value={statistics.total_due}
            precision={2}
            prefix={<DollarOutlined />}
            suffix="元"
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <Card className={[styles.metricCard, styles.toneSuccess].join(' ')}>
          <Statistic
            title="已收总额"
            value={statistics.total_paid}
            precision={2}
            prefix={<DollarOutlined />}
            suffix="元"
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <Card className={[styles.metricCard, toneClassMap[paymentRateTone]].join(' ')}>
          <Statistic title="收缴率" value={statistics.payment_rate} precision={2} suffix="%" />
          <Tag className={[styles.statusTag, toneClassMap[paymentRateTone]].join(' ')}>
            {paymentRateLabel}
          </Tag>
        </Card>
      </Col>
    </Row>
  );
};

export default ContractStatsCards;
