import React, { useMemo } from 'react';
import { Card, Col, Progress, Row, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Tone } from '../types';
import type { FieldErrorRate } from '../types';
import { getErrorRateTone, getToneColor } from '../utils';
import styles from '../../PromptDashboard.module.css';

interface PromptDashboardFieldErrorCardProps {
  fieldErrorRates: FieldErrorRate[];
  monitoredFieldCount: number;
  highRiskFieldCount: number;
  resolveToneClassName: (tone: Tone) => string;
}

const PromptDashboardFieldErrorCard: React.FC<PromptDashboardFieldErrorCardProps> = ({
  fieldErrorRates,
  monitoredFieldCount,
  highRiskFieldCount,
  resolveToneClassName,
}) => {
  const fieldErrorColumns = useMemo<ColumnsType<FieldErrorRate>>(
    () => [
      {
        title: '字段名称',
        dataIndex: 'field_name',
        key: 'field_name',
        render: (name: string) => (
          <Tag className={`${styles.semanticTag} ${styles.fieldNameTag} ${styles.tonePrimary}`}>
            {name}
          </Tag>
        ),
      },
      {
        title: '错误次数',
        dataIndex: 'error_count',
        key: 'error_count',
        align: 'right',
      },
      {
        title: '总次数',
        dataIndex: 'total_count',
        key: 'total_count',
        align: 'right',
      },
      {
        title: '错误率',
        dataIndex: 'error_rate',
        key: 'error_rate',
        align: 'right',
        render: (rate: number) => {
          const tone = getErrorRateTone(rate);
          return (
            <span className={`${styles.metricValue} ${resolveToneClassName(tone)}`}>
              {(rate * 100).toFixed(1)}%
            </span>
          );
        },
      },
      {
        title: '错误率分布',
        key: 'progress',
        render: (_, record) => (
          <Progress
            percent={record.error_rate * 100}
            size="small"
            strokeColor={getToneColor(getErrorRateTone(record.error_rate))}
          />
        ),
      },
    ],
    [resolveToneClassName]
  );

  return (
    <Row gutter={[16, 16]} className={styles.sectionSpacing}>
      <Col span={24}>
        <Card title="字段错误率分析">
          <div className={styles.tableSummary}>
            <span className={styles.summaryText}>监控字段：{monitoredFieldCount} 个</span>
            <span
              className={`${styles.summaryText} ${highRiskFieldCount > 0 ? styles.toneError : styles.toneSuccess}`}
            >
              高风险字段：{highRiskFieldCount} 个
            </span>
          </div>
          <Table<FieldErrorRate>
            columns={fieldErrorColumns}
            dataSource={fieldErrorRates}
            rowKey="field_name"
            pagination={false}
            size="small"
            scroll={{ x: 720 }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default PromptDashboardFieldErrorCard;
