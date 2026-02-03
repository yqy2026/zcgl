/**
 * LLM Prompt 性能监控 Dashboard
 * 展示 Prompt 的性能趋势、准确率变化、错误分析等
 */

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Row,
  Col,
  Statistic,
  Typography,
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
import { RiseOutlined, FallOutlined, CheckCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import type { PromptTemplate, PromptStatistics } from '@/types/llmPrompt';
import { llmPromptService } from '@/services/llmPromptService';
import { createLogger } from '@/utils/logger';
import { COLORS } from '@/styles/colorMap';

const logger = createLogger('PromptDashboard');
const { Title } = Typography;
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

const PromptDashboard: React.FC = () => {
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const [performanceData, setPerformanceData] = useState<PerformanceMetrics[]>([]);
  const [fieldErrorRates, setFieldErrorRates] = useState<FieldErrorRate[]>([]);
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
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
  const isInitialLoading =
    promptsQuery.isLoading === true || statisticsQuery.isLoading === true;
  const isRefreshing =
    promptsQuery.isFetching === true || statisticsQuery.isFetching === true;
  const hasError =
    promptsQuery.isError === true || statisticsQuery.isError === true;
  const errorMessage =
    (promptsQuery.error instanceof Error ? promptsQuery.error.message : null) ??
    (statisticsQuery.error instanceof Error
      ? statisticsQuery.error.message
      : null);

  const handleRefresh = () => {
    void Promise.all([promptsQuery.refetch(), statisticsQuery.refetch()]);
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
          suggestion: '租户名称识别基本良好，可考虑添加更多样例',
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
      const activePrompt = prompts.find(p => p.status === 'ACTIVE');
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
      render: (name: string) => <Tag color="blue">{name}</Tag>,
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
      render: (rate: number) => (
        <span
          style={{
            color: rate > 0.08 ? COLORS.error : rate > 0.05 ? COLORS.warning : COLORS.success,
            fontWeight: 'bold',
          }}
        >
          {(rate * 100).toFixed(1)}%
        </span>
      ),
    },
    {
      title: '错误率分布',
      key: 'progress',
      render: (_, record) => (
        <Progress
          percent={record.error_rate * 100}
          size="small"
          strokeColor={
            record.error_rate > 0.08
              ? COLORS.error
              : record.error_rate > 0.05
                ? COLORS.warning
                : COLORS.success
          }
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
      <Space orientation="vertical" style={{ width: '100%' }}>
        {suggestions.map(s => (
          <Alert
            key={`${s.field_name}-${s.priority}`}
            title={
              <Space>
                <span>
                  <Tag
                    color={
                      s.priority === 'high' ? 'red' : s.priority === 'medium' ? 'orange' : 'green'
                    }
                  >
                    {s.priority === 'high'
                      ? '高优先级'
                      : s.priority === 'medium'
                        ? '中优先级'
                        : '低优先级'}
                  </Tag>
                  <strong>{s.field_name}</strong>
                </span>
              </Space>
            }
            description={
              <div>
                <p style={{ margin: '8px 0' }}>
                  <strong>问题：</strong>
                  {s.issue}
                </p>
                <p style={{ margin: '8px 0' }}>
                  <strong>建议：</strong>
                  {s.suggestion}
                </p>
              </div>
            }
            type={s.priority === 'high' ? 'error' : s.priority === 'medium' ? 'warning' : 'info'}
            showIcon
          />
        ))}
      </Space>
    );
  };

  // 渲染性能趋势图（简化版，实际可使用ECharts或Recharts）
  const renderPerformanceChart = () => {
    if (performanceData.length === 0) {
      return <div style={{ textAlign: 'center', padding: 40 }}>暂无数据</div>;
    }

    return (
      <div style={{ padding: 20 }}>
        <Row gutter={16}>
          {performanceData.map(day => (
            <Col span={3} key={day.date}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
                  {dayjs(day.date).format('MM-DD')}
                </div>
                <div style={{ marginBottom: 4 }}>
                  <div style={{ fontSize: 10, color: '#999' }}>准确率</div>
                  <div
                    style={{
                      fontSize: 16,
                      fontWeight: 'bold',
                      color:
                        day.accuracy >= 0.85
                          ? COLORS.success
                          : day.accuracy >= 0.75
                            ? COLORS.warning
                            : COLORS.error,
                    }}
                  >
                    {(day.accuracy * 100).toFixed(0)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#999' }}>置信度</div>
                  <div
                    style={{
                      fontSize: 14,
                      color:
                        day.confidence >= 0.8
                          ? COLORS.success
                          : day.confidence >= 0.7
                            ? COLORS.warning
                            : COLORS.error,
                    }}
                  >
                    {(day.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </Col>
          ))}
        </Row>
      </div>
    );
  };

  if (isInitialLoading === true) {
    return (
      <div style={{ padding: 50, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  const selectedPrompt = prompts.find(p => p.id === selectedPromptId);

  return (
    <div style={{ padding: 24, background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 头部 */}
      <Card style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Title level={3} style={{ margin: 0 }}>
                LLM Prompt 性能监控
              </Title>
            </Space>
          </Col>
          <Col>
            <Space>
              <RangePicker
                value={dateRange}
                onChange={dates => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
              />
              <Select
                style={{ width: 300 }}
                placeholder="选择 Prompt"
                value={selectedPromptId}
                onChange={setSelectedPromptId}
                options={prompts.map(p => ({
                  label: `${p.name} (${p.version})`,
                  value: p.id,
                }))}
              />
              <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={isRefreshing}>
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {hasError === true && (
        <Alert
          style={{ marginBottom: 24 }}
          type="error"
          title="数据加载失败"
          description={errorMessage ?? '请稍后重试'}
          showIcon
        />
      )}

      {/* 统计概览 */}
      {statistics != null && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总 Prompt 数"
                value={statistics.total_prompts}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="活跃 Prompt"
                value={statistics.status_distribution.find(s => s.status === 'ACTIVE')?.count ?? 0}
                styles={{ content: { color: COLORS.success } }}
                suffix={<span style={{ fontSize: 14 }}>/ {statistics.total_prompts}</span>}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均准确率"
                value={(statistics.overall_avg_accuracy * 100).toFixed(1)}
                suffix="%"
                styles={{ content: {
                  color: statistics.overall_avg_accuracy >= 0.85 ? COLORS.success : COLORS.warning,
                } }}
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
          <Col span={6}>
            <Card>
              <Statistic
                title="平均置信度"
                value={(statistics.overall_avg_confidence * 100).toFixed(1)}
                suffix="%"
                styles={{ content: {
                  color: statistics.overall_avg_confidence >= 0.8 ? COLORS.success : COLORS.warning,
                } }}
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
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={24}>
            <Card
              title={
                <Space>
                  <span>{selectedPrompt.name}</span>
                  <Tag color="blue">v{selectedPrompt.version}</Tag>
                  <Tag color={selectedPrompt.status === 'ACTIVE' ? 'green' : 'default'}>
                    {selectedPrompt.status}
                  </Tag>
                </Space>
              }
            >
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic title="使用次数" value={selectedPrompt.total_usage} />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="平均准确率"
                    value={(selectedPrompt.avg_accuracy * 100).toFixed(1)}
                    suffix="%"
                    styles={{ content: {
                      color:
                        selectedPrompt.avg_accuracy >= 0.85
                          ? COLORS.success
                          : selectedPrompt.avg_accuracy >= 0.75
                            ? COLORS.warning
                            : COLORS.error,
                    } }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="平均置信度"
                    value={(selectedPrompt.avg_confidence * 100).toFixed(1)}
                    suffix="%"
                    styles={{ content: {
                      color:
                        selectedPrompt.avg_confidence >= 0.8
                          ? COLORS.success
                          : selectedPrompt.avg_confidence >= 0.7
                            ? COLORS.warning
                            : COLORS.error,
                    } }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic title="提供商" value={selectedPrompt.provider.toUpperCase()} />
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
      )}

      {/* 性能趋势图 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="近7天性能趋势">{renderPerformanceChart()}</Card>
        </Col>
      </Row>

      {/* 字段错误率 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="字段错误率分析">
            <Table
              columns={fieldErrorColumns}
              dataSource={fieldErrorRates}
              rowKey="field_name"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* 优化建议 */}
      <Row gutter={16}>
        <Col span={24}>
          <Card title="优化建议">{renderSuggestions()}</Card>
        </Col>
      </Row>
    </div>
  );
};

export default PromptDashboard;
