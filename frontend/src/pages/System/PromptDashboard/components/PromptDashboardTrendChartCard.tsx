import React from 'react';
import { Card, Col, Row } from 'antd';
import dayjs from 'dayjs';
import type { Tone } from '../types';
import type { PerformanceMetrics } from '../types';
import { getAccuracyTone, getConfidenceTone } from '../utils';
import styles from '../../PromptDashboard.module.css';

interface PromptDashboardTrendChartCardProps {
  performanceData: PerformanceMetrics[];
  resolveToneClassName: (tone: Tone) => string;
}

const PromptDashboardTrendChartCard: React.FC<PromptDashboardTrendChartCardProps> = ({
  performanceData,
  resolveToneClassName,
}) => {
  const renderPerformanceChart = () => {
    if (performanceData.length === 0) {
      return <div className={styles.chartEmpty}>暂无数据</div>;
    }

    return (
      <div className={styles.chartContainer}>
        <div className={styles.trendGrid}>
          {performanceData.map(day => (
            <div className={styles.trendItem} key={day.date}>
              <div className={styles.trendDate}>{dayjs(day.date).format('MM-DD')}</div>
              <div className={styles.trendMetricBlock}>
                <span className={styles.trendMetricLabel}>准确率</span>
                <span
                  className={`${styles.metricValue} ${resolveToneClassName(getAccuracyTone(day.accuracy))}`}
                >
                  {(day.accuracy * 100).toFixed(0)}%
                </span>
              </div>
              <div className={styles.trendMetricBlock}>
                <span className={styles.trendMetricLabel}>置信度</span>
                <span
                  className={`${styles.trendConfidence} ${resolveToneClassName(
                    getConfidenceTone(day.confidence)
                  )}`}
                >
                  {(day.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <Row gutter={[16, 16]} className={styles.sectionSpacing}>
      <Col span={24}>
        <Card title="近7天性能趋势">{renderPerformanceChart()}</Card>
      </Col>
    </Row>
  );
};

export default PromptDashboardTrendChartCard;
