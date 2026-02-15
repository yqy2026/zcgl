import React, { useCallback } from 'react';
import { Alert, Button, Spin } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import PageContainer from '@/components/Common/PageContainer';
import type { Tone } from './types';
import { usePromptDashboardData } from './hooks/usePromptDashboardData';
import PromptDashboardFilterSection from './components/PromptDashboardFilterSection';
import PromptDashboardOverviewCards from './components/PromptDashboardOverviewCards';
import PromptDashboardSelectedPromptCard from './components/PromptDashboardSelectedPromptCard';
import PromptDashboardTrendChartCard from './components/PromptDashboardTrendChartCard';
import PromptDashboardFieldErrorCard from './components/PromptDashboardFieldErrorCard';
import PromptDashboardSuggestionsCard from './components/PromptDashboardSuggestionsCard';
import styles from '../PromptDashboard.module.css';

const toneClassMap: Record<Tone, string> = {
  primary: styles.tonePrimary,
  success: styles.toneSuccess,
  warning: styles.toneWarning,
  error: styles.toneError,
  neutral: styles.toneNeutral,
};

const PromptDashboard: React.FC = () => {
  const {
    statistics,
    selectedPromptId,
    selectedPrompt,
    selectedStatusMeta,
    performanceData,
    fieldErrorRates,
    suggestions,
    dateRange,
    dateRangeLabel,
    promptOptions,
    activePromptCount,
    monitoredFieldCount,
    highRiskFieldCount,
    accuracyTrend,
    confidenceTrend,
    isInitialLoading,
    isRefreshing,
    hasError,
    errorMessage,
    handleRefresh,
    handleDateRangeChange,
    handlePromptChange,
  } = usePromptDashboardData();

  const getToneClassName = useCallback((tone: Tone): string => {
    return toneClassMap[tone];
  }, []);

  if (isInitialLoading === true) {
    return (
      <PageContainer
        className={styles.pageShell}
        title="LLM Prompt 性能监控"
        subTitle="跟踪模板表现并识别优化机会"
      >
        <div className={styles.loadingContainer}>
          <Spin size="large" />
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      className={styles.pageShell}
      title="LLM Prompt 性能监控"
      subTitle="跟踪模板表现并识别优化机会"
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={handleRefresh}
          loading={isRefreshing}
          aria-label="刷新监控数据"
          className={styles.actionButton}
        >
          刷新
        </Button>
      }
    >
      <PromptDashboardFilterSection
        dateRange={dateRange}
        dateRangeLabel={dateRangeLabel}
        promptOptions={promptOptions}
        selectedPromptId={selectedPromptId}
        selectedPromptName={selectedPrompt?.name}
        onDateRangeChange={handleDateRangeChange}
        onPromptChange={handlePromptChange}
      />

      {hasError === true && (
        <div role="alert" className={styles.sectionSpacing}>
          <Alert
            type="error"
            title="数据加载失败"
            description={errorMessage ?? '请稍后重试'}
            showIcon
          />
        </div>
      )}

      {statistics != null && (
        <PromptDashboardOverviewCards
          statistics={statistics}
          activePromptCount={activePromptCount}
          accuracyTrend={accuracyTrend}
          confidenceTrend={confidenceTrend}
          resolveToneClassName={getToneClassName}
        />
      )}

      {selectedPrompt != null && (
        <PromptDashboardSelectedPromptCard
          selectedPrompt={selectedPrompt}
          selectedStatusMeta={selectedStatusMeta}
          resolveToneClassName={getToneClassName}
        />
      )}

      <PromptDashboardTrendChartCard
        performanceData={performanceData}
        resolveToneClassName={getToneClassName}
      />

      <PromptDashboardFieldErrorCard
        fieldErrorRates={fieldErrorRates}
        monitoredFieldCount={monitoredFieldCount}
        highRiskFieldCount={highRiskFieldCount}
        resolveToneClassName={getToneClassName}
      />

      <PromptDashboardSuggestionsCard
        suggestions={suggestions}
        resolveToneClassName={getToneClassName}
      />
    </PageContainer>
  );
};

export default PromptDashboard;
