import React from 'react';
import { Alert, Card, Col, Row, Space, Tag } from 'antd';
import type { Tone } from '../types';
import type { OptimizationSuggestion } from '../types';
import { getPriorityConfig } from '../utils';
import styles from '../../PromptDashboard.module.css';

interface PromptDashboardSuggestionsCardProps {
  suggestions: OptimizationSuggestion[];
  resolveToneClassName: (tone: Tone) => string;
}

const PromptDashboardSuggestionsCard: React.FC<PromptDashboardSuggestionsCardProps> = ({
  suggestions,
  resolveToneClassName,
}) => {
  const renderSuggestions = () => {
    if (suggestions.length === 0) {
      return (
        <Alert
          title="表现优秀！"
          description="当前 Prompt 性能表现良好，暂无明显优化建议。"
          type="success"
          showIcon
        />
      );
    }

    return (
      <Space orientation="vertical" size={12} className={styles.suggestionsList}>
        {suggestions.map(suggestion => {
          const priorityConfig = getPriorityConfig(suggestion.priority);
          return (
            <Alert
              key={`${suggestion.field_name}-${suggestion.priority}`}
              title={
                <Space size={[8, 6]} wrap>
                  <Tag
                    icon={priorityConfig.icon}
                    className={`${styles.semanticTag} ${styles.priorityTag} ${resolveToneClassName(priorityConfig.tone)}`}
                  >
                    {priorityConfig.label}
                  </Tag>
                  <strong className={styles.suggestionFieldName}>{suggestion.field_name}</strong>
                  <span className={styles.suggestionHint}>{priorityConfig.hint}</span>
                </Space>
              }
              description={
                <div>
                  <p className={styles.suggestionParagraph}>
                    <strong className={styles.suggestionLabel}>问题：</strong>
                    {suggestion.issue}
                  </p>
                  <p className={styles.suggestionParagraph}>
                    <strong className={styles.suggestionLabel}>建议：</strong>
                    {suggestion.suggestion}
                  </p>
                </div>
              }
              type={priorityConfig.alertType}
              showIcon
            />
          );
        })}
      </Space>
    );
  };

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card title="优化建议">{renderSuggestions()}</Card>
      </Col>
    </Row>
  );
};

export default PromptDashboardSuggestionsCard;
