import React from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import { CheckCircleOutlined, FallOutlined, RiseOutlined } from '@ant-design/icons';
import type { PromptStatistics } from '@/types/llmPrompt';
import type { Tone } from '../types';
import { getAccuracyTone, getConfidenceTone } from '../utils';
import styles from '../../PromptDashboard.module.css';

interface PromptDashboardOverviewCardsProps {
  statistics: PromptStatistics;
  activePromptCount: number;
  accuracyTrend: 'up' | 'down' | 'stable';
  confidenceTrend: 'up' | 'down' | 'stable';
  resolveToneClassName: (tone: Tone) => string;
}

const renderTrendIcon = (trend: 'up' | 'down' | 'stable') => {
  if (trend === 'up') {
    return <RiseOutlined />;
  }
  if (trend === 'down') {
    return <FallOutlined />;
  }
  return null;
};

const PromptDashboardOverviewCards: React.FC<PromptDashboardOverviewCardsProps> = ({
  statistics,
  activePromptCount,
  accuracyTrend,
  confidenceTrend,
  resolveToneClassName,
}) => {
  return (
    <Row gutter={[16, 16]} className={styles.sectionSpacing}>
      <Col xs={24} sm={12} xl={6}>
        <Card className={`${styles.summaryCard} ${styles.statsCard}`}>
          <Statistic
            title="总 Prompt 数"
            value={statistics.total_prompts}
            prefix={<CheckCircleOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card className={`${styles.summaryCard} ${styles.statsCard} ${styles.toneSuccess}`}>
          <Statistic
            title="活跃 Prompt"
            value={activePromptCount}
            suffix={<span className={styles.totalSuffix}>/ {statistics.total_prompts}</span>}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card
          className={`${styles.summaryCard} ${styles.statsCard} ${resolveToneClassName(
            getAccuracyTone(statistics.overall_avg_accuracy)
          )}`}
        >
          <Statistic
            title="平均准确率"
            value={(statistics.overall_avg_accuracy * 100).toFixed(1)}
            suffix="%"
            prefix={renderTrendIcon(accuracyTrend)}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card
          className={`${styles.summaryCard} ${styles.statsCard} ${resolveToneClassName(
            getConfidenceTone(statistics.overall_avg_confidence)
          )}`}
        >
          <Statistic
            title="平均置信度"
            value={(statistics.overall_avg_confidence * 100).toFixed(1)}
            suffix="%"
            prefix={renderTrendIcon(confidenceTrend)}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default PromptDashboardOverviewCards;
