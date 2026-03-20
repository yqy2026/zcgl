import React from 'react';
import { Alert, Card, Col, Row, Statistic } from 'antd';

import type { CompleteResult } from '@/services/pdfImportService';
import styles from './ContractImportReview.module.css';

type ConfidenceTone = 'success' | 'warning' | 'error';

interface ReviewSummaryProps {
  result: CompleteResult;
}

const getConfidenceTone = (score: number): ConfidenceTone => {
  if (score >= 90) {
    return 'success';
  }
  if (score >= 70) {
    return 'warning';
  }
  return 'error';
};

const getConfidenceToneClassName = (score: number): string => {
  const tone = getConfidenceTone(score);
  if (tone === 'success') {
    return styles.toneSuccess;
  }
  if (tone === 'warning') {
    return styles.toneWarning;
  }
  return styles.toneError;
};

const renderMessageList = (messages: string[]) => (
  <ul>
    {messages.map(message => (
      <li key={message}>{message}</li>
    ))}
  </ul>
);

const ReviewSummary: React.FC<ReviewSummaryProps> = ({ result }) => (
  <>
    <Card className={styles.sectionCard}>
      <Row gutter={[16, 16]} className={styles.statsRow}>
        <Col xs={24} sm={12} xl={6}>
          <Card
            className={`${styles.statsCard} ${getConfidenceToneClassName(result.summary.extraction_confidence)}`}
          >
            <Statistic
              title="提取可信度"
              value={result.summary.extraction_confidence}
              precision={2}
              suffix="%"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card
            className={`${styles.statsCard} ${getConfidenceToneClassName(result.summary.validation_score)}`}
          >
            <Statistic
              title="验证评分"
              value={result.summary.validation_score}
              precision={2}
              suffix="%"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card
            className={`${styles.statsCard} ${getConfidenceToneClassName(result.summary.match_confidence)}`}
          >
            <Statistic
              title="匹配置信度"
              value={result.summary.match_confidence}
              precision={2}
              suffix="%"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card
            className={`${styles.statsCard} ${getConfidenceToneClassName(result.summary.total_confidence)}`}
          >
            <Statistic
              title="总体评分"
              value={result.summary.total_confidence}
              precision={2}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>
    </Card>

    {result.recommendations.length > 0 && (
      <Alert
        title="系统建议"
        description={renderMessageList(result.recommendations)}
        type="info"
        showIcon
        className={styles.messageAlert}
      />
    )}

    {result.extraction_result.warnings != null && result.extraction_result.warnings.length > 0 && (
      <Alert
        title="提取警告"
        description={renderMessageList(result.extraction_result.warnings)}
        type="warning"
        showIcon
        className={styles.messageAlert}
      />
    )}

    {result.validation_result.errors.length > 0 && (
      <Alert
        title="验证错误"
        description={renderMessageList(result.validation_result.errors)}
        type="error"
        showIcon
        className={styles.messageAlert}
      />
    )}

    {result.validation_result.warnings.length > 0 && (
      <Alert
        title="验证警告"
        description={renderMessageList(result.validation_result.warnings)}
        type="warning"
        showIcon
        className={styles.messageAlert}
      />
    )}
  </>
);

export default ReviewSummary;
