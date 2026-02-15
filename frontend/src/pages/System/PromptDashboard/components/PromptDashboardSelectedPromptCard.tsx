import React from 'react';
import { Card, Col, Row, Space, Statistic, Tag } from 'antd';
import type { PromptTemplate } from '@/types/llmPrompt';
import type { PromptStatusMeta, Tone } from '../types';
import { getAccuracyTone, getConfidenceTone, normalizeVersion } from '../utils';
import styles from '../../PromptDashboard.module.css';

interface PromptDashboardSelectedPromptCardProps {
  selectedPrompt: PromptTemplate;
  selectedStatusMeta: PromptStatusMeta | null;
  resolveToneClassName: (tone: Tone) => string;
}

const PromptDashboardSelectedPromptCard: React.FC<PromptDashboardSelectedPromptCardProps> = ({
  selectedPrompt,
  selectedStatusMeta,
  resolveToneClassName,
}) => {
  return (
    <Row gutter={[16, 16]} className={styles.sectionSpacing}>
      <Col span={24}>
        <Card
          title={
            <Space size={[8, 8]} wrap>
              <span className={styles.promptName}>{selectedPrompt.name}</span>
              <Tag className={`${styles.semanticTag} ${styles.versionTag} ${styles.tonePrimary}`}>
                {normalizeVersion(selectedPrompt.version)}
              </Tag>
              {selectedStatusMeta != null && (
                <Tag
                  icon={selectedStatusMeta.icon}
                  className={`${styles.semanticTag} ${styles.statusTag} ${resolveToneClassName(selectedStatusMeta.tone)}`}
                >
                  {selectedStatusMeta.label}
                  <span className={styles.statusHint}>{selectedStatusMeta.hint}</span>
                </Tag>
              )}
            </Space>
          }
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} xl={6}>
              <Statistic title="使用次数" value={selectedPrompt.total_usage} />
            </Col>
            <Col
              xs={24}
              sm={12}
              xl={6}
              className={resolveToneClassName(getAccuracyTone(selectedPrompt.avg_accuracy))}
            >
              <Statistic
                title="平均准确率"
                value={(selectedPrompt.avg_accuracy * 100).toFixed(1)}
                suffix="%"
              />
            </Col>
            <Col
              xs={24}
              sm={12}
              xl={6}
              className={resolveToneClassName(getConfidenceTone(selectedPrompt.avg_confidence))}
            >
              <Statistic
                title="平均置信度"
                value={(selectedPrompt.avg_confidence * 100).toFixed(1)}
                suffix="%"
              />
            </Col>
            <Col xs={24} sm={12} xl={6}>
              <Statistic title="提供商" value={selectedPrompt.provider.toUpperCase()} />
            </Col>
          </Row>
        </Card>
      </Col>
    </Row>
  );
};

export default PromptDashboardSelectedPromptCard;
