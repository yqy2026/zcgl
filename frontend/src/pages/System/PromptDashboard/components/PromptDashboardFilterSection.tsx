import React from 'react';
import { Card, DatePicker, Select, Space, Tag } from 'antd';
import type { Dayjs } from 'dayjs';
import { ListToolbar } from '@/components/Common/ListToolbar';
import styles from '../../PromptDashboard.module.css';

const { RangePicker } = DatePicker;

interface PromptOption {
  label: string;
  value: string;
}

interface PromptDashboardFilterSectionProps {
  dateRange: [Dayjs, Dayjs] | null;
  dateRangeLabel: string;
  promptOptions: PromptOption[];
  selectedPromptId: string | null;
  selectedPromptName?: string;
  onDateRangeChange: (value: [Dayjs | null, Dayjs | null] | null) => void;
  onPromptChange: (value: string) => void;
}

const PromptDashboardFilterSection: React.FC<PromptDashboardFilterSectionProps> = ({
  dateRange,
  dateRangeLabel,
  promptOptions,
  selectedPromptId,
  selectedPromptName,
  onDateRangeChange,
  onPromptChange,
}) => {
  return (
    <>
      <Card className={styles.sectionSpacing}>
        <ListToolbar
          variant="plain"
          items={[
            {
              key: 'date-range',
              col: { xs: 24, md: 10 },
              content: (
                <RangePicker
                  value={dateRange}
                  onChange={onDateRangeChange}
                  className={styles.rangePicker}
                  allowClear
                  aria-label="监控时间范围"
                />
              ),
            },
            {
              key: 'prompt',
              col: { xs: 24, md: 14 },
              content: (
                <Select
                  className={styles.promptSelect}
                  placeholder="选择 Prompt"
                  value={selectedPromptId ?? undefined}
                  onChange={onPromptChange}
                  options={promptOptions}
                  aria-label="选择 Prompt 模板"
                />
              ),
            },
          ]}
        />
      </Card>

      <div className={`${styles.sectionSpacing} ${styles.filterSummary}`}>
        <Space size={[8, 8]} wrap>
          <Tag className={`${styles.semanticTag} ${styles.toneNeutral}`}>
            监控区间：{dateRangeLabel}
          </Tag>
          <Tag
            className={`${styles.semanticTag} ${
              selectedPromptName != null && selectedPromptName !== ''
                ? styles.tonePrimary
                : styles.toneNeutral
            }`}
          >
            当前模板：{selectedPromptName ?? '未选择'}
          </Tag>
        </Space>
      </div>
    </>
  );
};

export default PromptDashboardFilterSection;
