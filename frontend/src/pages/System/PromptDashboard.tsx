/**
 * LLM Prompt 性能监控 Dashboard
 * 展示 Prompt 的性能趋势、准确率变化、错误分析等
 */

import React, { useState, useEffect, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Row,
  Col,
  Statistic,
  Spin,
  Alert,
  Tag,
  Progress,
  Table,
  Select,
  DatePicker,
  Space,
  Button,
} from 'antd';
import {
  RiseOutlined,
  FallOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  StopOutlined,
  FireOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { PromptStatus, type PromptTemplate, type PromptStatistics } from '@/types/llmPrompt';
import { llmPromptService } from '@/services/llmPromptService';
import { createLogger } from '@/utils/logger';
import PageContainer from '@/components/Common/PageContainer';
import { ListToolbar } from '@/components/Common/ListToolbar';
import styles from './PromptDashboard.module.css';

const logger = createLogger('PromptDashboard');
const { RangePicker } = DatePicker;

interface PerformanceMetrics {
  date: string;
  accuracy: number;
  confidence: number;
  extraction_count: number;
  corrected_count: number;
}

interface FieldErrorRate {
  field_name: string;
  error_count: number;
  total_count: number;
  error_rate: number;
}

interface OptimizationSuggestion {
  priority: 'high' | 'medium' | 'low';
  field_name: string;
  issue: string;
  suggestion: string;
}

type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';
type MetricTone = Extract<Tone, 'success' | 'warning' | 'error'>;

interface PromptStatusMeta {
  label: string;
  hint: string;
  tone: Tone;
  icon: ReactNode;
}

interface SuggestionPriorityMeta {
  label: string;
  hint: string;
  tone: Tone;
  icon: ReactNode;
  alertType: 'error' | 'warning' | 'info';
}

const PROMPT_STATUS_META_MAP: Record<PromptStatus, PromptStatusMeta> = {
  [PromptStatus.ACTIVE]: {
    label: '使用中',
    hint: '在线生效',
    tone: 'success',
    icon: <CheckCircleOutlined />,
  },
  [PromptStatus.DRAFT]: {
    label: '草稿',
    hint: '待发布',
    tone: 'warning',
    icon: <ClockCircleOutlined />,
  },
  [PromptStatus.ARCHIVED]: {
    label: '已归档',
    hint: '仅历史',
    tone: 'neutral',
    icon: <StopOutlined />,
  },
};

const PRIORITY_META_MAP: Record<OptimizationSuggestion['priority'], SuggestionPriorityMeta> = {
  high: {
    label: '高优先级',
    hint: '建议尽快处理',
    tone: 'error',
    icon: <FireOutlined />,
    alertType: 'error',
  },
  medium: {
    label: '中优先级',
    hint: '建议本周处理',
    tone: 'warning',
    icon: <ExclamationCircleOutlined />,
    alertType: 'warning',
  },
  low: {
    label: '低优先级',
    hint: '可排期处理',
    tone: 'success',
    icon: <InfoCircleOutlined />,
    alertType: 'info',
  },
};

const getAccuracyTone = (value: number): MetricTone => {
  if (value >= 0.85) {
    return 'success';
  }
  if (value >= 0.75) {
    return 'warning';
  }
  return 'error';
};

const getConfidenceTone = (value: number): MetricTone => {
  if (value >= 0.8) {
    return 'success';
  }
  if (value >= 0.7) {
    return 'warning';
  }
  return 'error';
};

const getErrorRateTone = (value: number): MetricTone => {
  if (value > 0.08) {
    return 'error';
  }
  if (value > 0.05) {
    return 'warning';
  }
  return 'success';
};

const getToneClassName = (tone: Tone): string => {
  if (tone === 'primary') {
    return styles.tonePrimary;
  }
  if (tone === 'success') {
    return styles.toneSuccess;
  }
  if (tone === 'warning') {
    return styles.toneWarning;
  }
  if (tone === 'neutral') {
    return styles.toneNeutral;
  }
  return styles.toneError;
};

const getToneColor = (tone: MetricTone): string => {
  if (tone === 'success') {
    return 'var(--color-success)';
  }
  if (tone === 'warning') {
    return 'var(--color-warning)';
  }
  return 'var(--color-error)';
};

const getPriorityConfig = (priority: OptimizationSuggestion['priority']): SuggestionPriorityMeta =>
  PRIORITY_META_MAP[priority];

const getPromptStatusMeta = (status: PromptStatus): PromptStatusMeta => PROMPT_STATUS_META_MAP[status];

const normalizeVersion = (version: string): string => {
  if (version.toLowerCase().startsWith('v')) {
    return version;
  }
  return `v${version}`;
};

const PromptDashboard: React.FC = () => {
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const [performanceData, setPerformanceData] = useState<PerformanceMetrics[]>([]);
  const [fieldErrorRates, setFieldErrorRates] = useState<FieldErrorRate[]>([]);
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>([
    dayjs().subtract(30, 'days'),
    dayjs(),
  ]);

  const promptsQuery = useQuery({
    queryKey: ['llm-prompts', 'list', { page_size: 100 }],
    queryFn: async () => {
      try {
        return await llmPromptService.getPrompts({ page_size: 100 });
      } catch (error) {
        logger.error('加载 Prompt 列表失败', error);
        throw error;
      }
    },
  });

  const statisticsQuery = useQuery({
    queryKey: ['llm-prompts', 'statistics'],
    queryFn: async () => {
      try {
        return await llmPromptService.getStatistics();
      } catch (error) {
        logger.error('加载统计数据失败', error);
        throw error;
      }
    },
  });

  const prompts: PromptTemplate[] = promptsQuery.data?.items ?? [];
  const statistics: PromptStatistics | null = statisticsQuery.data ?? null;
  const isInitialLoading = promptsQuery.isLoading === true || statisticsQuery.isLoading === true;
  const isRefreshing = promptsQuery.isFetching === true || statisticsQuery.isFetching === true;
  const hasError = promptsQuery.isError === true || statisticsQuery.isError === true;
  const errorMessage =
    (promptsQuery.error instanceof Error ? promptsQuery.error.message : null) ??
    (statisticsQuery.error instanceof Error ? statisticsQuery.error.message : null);

  const handleRefresh = () => {
    void Promise.all([promptsQuery.refetch(), statisticsQuery.refetch()]);
  };

  const handleDateRangeChange = (value: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    if (value != null && value[0] != null && value[1] != null) {
      setDateRange([value[0], value[1]]);
      return;
    }
    setDateRange(null);
  };

  const handlePromptChange = (value: string) => {
    setSelectedPromptId(value);
  };

  // 加载选中 Prompt 的详细数据
  const loadPromptDetails = async (_promptId: string) => {
    try {
      // 模拟性能数据（实际应该从后端 API 获取）
      const mockPerformanceData: PerformanceMetrics[] = [
        {
          date: dayjs().subtract(6, 'days').format('YYYY-MM-DD'),
          accuracy: 0.82,
          confidence: 0.78,
          extraction_count: 45,
          corrected_count: 8,
        },
        {
          date: dayjs().subtract(5, 'days').format('YYYY-MM-DD'),
          accuracy: 0.84,
          confidence: 0.8,
          extraction_count: 52,
          corrected_count: 8,
        },
        {
          date: dayjs().subtract(4, 'days').format('YYYY-MM-DD'),
          accuracy: 0.86,
          confidence: 0.82,
          extraction_count: 48,
          corrected_count: 7,
        },
        {
          date: dayjs().subtract(3, 'days').format('YYYY-MM-DD'),
          accuracy: 0.85,
          confidence: 0.81,
          extraction_count: 50,
          corrected_count: 7,
        },
        {
          date: dayjs().subtract(2, 'days').format('YYYY-MM-DD'),
          accuracy: 0.88,
          confidence: 0.83,
          extraction_count: 55,
          corrected_count: 6,
        },
        {
          date: dayjs().subtract(1, 'days').format('YYYY-MM-DD'),
          accuracy: 0.87,
          confidence: 0.84,
          extraction_count: 47,
          corrected_count: 6,
        },
        {
          date: dayjs().format('YYYY-MM-DD'),
          accuracy: 0.89,
          confidence: 0.85,
          extraction_count: 53,
          corrected_count: 6,
        },
      ];

      const mockFieldErrorRates: FieldErrorRate[] = [
        { field_name: 'contract_number', error_count: 15, total_count: 350, error_rate: 0.043 },
        { field_name: 'sign_date', error_count: 28, total_count: 350, error_rate: 0.08 },
        { field_name: 'landlord_name', error_count: 12, total_count: 350, error_rate: 0.034 },
        { field_name: 'tenant_name', error_count: 18, total_count: 350, error_rate: 0.051 },
        { field_name: 'monthly_rent', error_count: 35, total_count: 350, error_rate: 0.1 },
        { field_name: 'lease_start_date', error_count: 22, total_count: 350, error_rate: 0.063 },
        { field_name: 'lease_end_date', error_count: 25, total_count: 350, error_rate: 0.071 },
      ];

      const mockSuggestions: OptimizationSuggestion[] = [
        {
          priority: 'high',
          field_name: 'monthly_rent',
          issue: '错误率 10%，为最高',
          suggestion: '租金字段识别错误较多，建议添加Few-shot示例和格式验证',
        },
        {
          priority: 'high',
          field_name: 'lease_end_date',
          issue: '错误率 7.1%',
          suggestion: '结束日期识别不准确，建议优化日期提取逻辑',
        },
        {
          priority: 'medium',
          field_name: 'lease_start_date',
          issue: '错误率 6.3%',
          suggestion: '开始日期识别需要改进，建议强调日期格式要求',
        },
        {
          priority: 'medium',
          field_name: 'sign_date',
          issue: '错误率 8.0%',
          suggestion: '签订日期格式错误，建议统一YYYY-MM-DD格式',
        },
        {
          priority: 'low',
          field_name: 'tenant_name',
          issue: '错误率 5.1%',
          suggestion: '承租方名称识别基本良好，可考虑添加更多样例',
        },
      ];

      setPerformanceData(mockPerformanceData);
      setFieldErrorRates(mockFieldErrorRates);
      setSuggestions(mockSuggestions);
    } catch (error) {
      logger.error('加载Prompt详情失败', error);
    }
  };

  useEffect(() => {
    if (selectedPromptId == null && prompts.length > 0) {
      const activePrompt = prompts.find(p => p.status === PromptStatus.ACTIVE);
      const nextPromptId = activePrompt?.id ?? prompts[0]?.id ?? null;
      if (nextPromptId != null) {
        setSelectedPromptId(nextPromptId);
      }
    }
  }, [prompts, selectedPromptId]);

  useEffect(() => {
    if (selectedPromptId != null) {
      loadPromptDetails(selectedPromptId);
    }
  }, [selectedPromptId]);

  // 计算趋势
  const calculateTrend = (data: number[]): 'up' | 'down' | 'stable' => {
    if (data.length < 2) return 'stable';
    const first = data[0];
    const last = data[data.length - 1];
    const change = ((last - first) / first) * 100;
    if (change > 2) return 'up';
    if (change < -2) return 'down';
    return 'stable';
  };

  const accuracyTrend = calculateTrend(performanceData.map(d => d.accuracy));
  const confidenceTrend = calculateTrend(performanceData.map(d => d.confidence));

  // 字段错误率表格列
  const fieldErrorColumns: ColumnsType<FieldErrorRate> = [
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
          <span className={`${styles.metricValue} ${getToneClassName(tone)}`}>
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
  ];

  // 优化建议列表
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
      <Space direction="vertical" size={12} className={styles.suggestionsList}>
        {suggestions.map(suggestion => {
          const priorityConfig = getPriorityConfig(suggestion.priority);
          return (
            <Alert
              key={`${suggestion.field_name}-${suggestion.priority}`}
              title={
                <Space size={[8, 6]} wrap>
                  <Tag
                    icon={priorityConfig.icon}
                    className={`${styles.semanticTag} ${styles.priorityTag} ${getToneClassName(
                      priorityConfig.tone
                    )}`}
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

  // 渲染性能趋势图（简化版，实际可使用ECharts或Recharts）
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
                  className={`${styles.metricValue} ${getToneClassName(getAccuracyTone(day.accuracy))}`}
                >
                  {(day.accuracy * 100).toFixed(0)}%
                </span>
              </div>
              <div className={styles.trendMetricBlock}>
                <span className={styles.trendMetricLabel}>置信度</span>
                <span
                  className={`${styles.trendConfidence} ${getToneClassName(
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

  if (isInitialLoading === true) {
    return (
      <PageContainer title="LLM Prompt 性能监控" subTitle="跟踪模板表现并识别优化机会">
        <div className={styles.loadingContainer}>
          <Spin size="large" />
        </div>
      </PageContainer>
    );
  }

  const selectedPrompt = prompts.find(p => p.id === selectedPromptId);
  const selectedStatusMeta =
    selectedPrompt != null ? getPromptStatusMeta(selectedPrompt.status) : null;
  const activePromptCount =
    statistics?.status_distribution.find(item => item.status === PromptStatus.ACTIVE)?.count ?? 0;
  const monitoredFieldCount = fieldErrorRates.length;
  const highRiskFieldCount = fieldErrorRates.filter(
    item => getErrorRateTone(item.error_rate) === 'error'
  ).length;
  const dateRangeLabel =
    dateRange != null
      ? `${dateRange[0].format('YYYY-MM-DD')} ~ ${dateRange[1].format('YYYY-MM-DD')}`
      : '全部时间';

  return (
    <PageContainer
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
                  onChange={handleDateRangeChange}
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
                  onChange={handlePromptChange}
                  options={prompts.map(prompt => ({
                    label: `${prompt.name} (${normalizeVersion(prompt.version)})`,
                    value: prompt.id,
                  }))}
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
              selectedPrompt != null ? styles.tonePrimary : styles.toneNeutral
            }`}
          >
            当前模板：{selectedPrompt?.name ?? '未选择'}
          </Tag>
        </Space>
      </div>

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

      {/* 统计概览 */}
      {statistics != null && (
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
                suffix={
                  <span className={styles.totalSuffix}>/ {statistics.total_prompts}</span>
                }
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card
              className={`${styles.summaryCard} ${styles.statsCard} ${getToneClassName(
                getAccuracyTone(statistics.overall_avg_accuracy)
              )}`}
            >
              <Statistic
                title="平均准确率"
                value={(statistics.overall_avg_accuracy * 100).toFixed(1)}
                suffix="%"
                prefix={
                  accuracyTrend === 'up' ? (
                    <RiseOutlined />
                  ) : accuracyTrend === 'down' ? (
                    <FallOutlined />
                  ) : null
                }
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card
              className={`${styles.summaryCard} ${styles.statsCard} ${getToneClassName(
                getConfidenceTone(statistics.overall_avg_confidence)
              )}`}
            >
              <Statistic
                title="平均置信度"
                value={(statistics.overall_avg_confidence * 100).toFixed(1)}
                suffix="%"
                prefix={
                  confidenceTrend === 'up' ? (
                    <RiseOutlined />
                  ) : confidenceTrend === 'down' ? (
                    <FallOutlined />
                  ) : null
                }
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 选中的 Prompt 详情 */}
      {selectedPrompt != null && (
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
                      className={`${styles.semanticTag} ${styles.statusTag} ${getToneClassName(
                        selectedStatusMeta.tone
                      )}`}
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
                  className={getToneClassName(getAccuracyTone(selectedPrompt.avg_accuracy))}
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
                  className={getToneClassName(getConfidenceTone(selectedPrompt.avg_confidence))}
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
      )}

      {/* 性能趋势图 */}
      <Row gutter={[16, 16]} className={styles.sectionSpacing}>
        <Col span={24}>
          <Card title="近7天性能趋势">{renderPerformanceChart()}</Card>
        </Col>
      </Row>

      {/* 字段错误率 */}
      <Row gutter={[16, 16]} className={styles.sectionSpacing}>
        <Col span={24}>
          <Card title="字段错误率分析">
            <div className={styles.tableSummary}>
              <span className={styles.summaryText}>监控字段：{monitoredFieldCount} 个</span>
              <span
                className={`${styles.summaryText} ${
                  highRiskFieldCount > 0 ? styles.toneError : styles.toneSuccess
                }`}
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

      {/* 优化建议 */}
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="优化建议">{renderSuggestions()}</Card>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default PromptDashboard;
