import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Button,
  DatePicker,
  Space,
  Tooltip,
  Alert,
  Modal,
  Form,
  InputNumber,
  Tabs
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  ReloadOutlined,
  SettingOutlined,
  RiseOutlined,
  FallOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { Line, Column } from '@ant-design/plots';
import { COLORS, CHART_COLORS } from '@/styles/colorMap';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import type { ColumnsType } from 'antd/es/table';

// 类型定义
interface CoverageMetrics {
  module_name: string;
  coverage_percentage: number;
  lines_covered: number;
  lines_total: number;
  branches_covered: number;
  branches_total: number;
  functions_covered: number;
  functions_total: number;
  last_updated: string;
  file_path: string;
}

interface CoverageReport {
  project_name: string;
  total_coverage: number;
  backend_coverage?: number;
  frontend_coverage?: number;
  module_metrics: CoverageMetrics[];
  test_execution_time?: number;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  generated_at: string;
}

interface CoverageTrend {
  date: string;
  backend_coverage?: number;
  frontend_coverage?: number;
  total_coverage: number;
}

interface CoverageThreshold {
  backend_threshold: number;
  frontend_threshold: number;
  total_threshold: number;
}

// 图表数据类型定义
interface ChartDatum {
  覆盖率: number
  [key: string]: number | string
}

interface _CoverageTrendDatum {
  date: string
  total_coverage: number
  backend_coverage?: number
  frontend_coverage?: number
}

interface QualityGateResult {
  passed: boolean;
  thresholds: {
    backend: number;
    frontend: number;
    total: number;
  };
  current_coverage: {
    backend?: number;
    frontend?: number;
    total: number;
  };
  failed_checks: string[];
}

// API服务函数
const fetchCoverageReport = async (): Promise<CoverageReport> => {
  const response = await fetch('/api/test-coverage/report');
  if (!response.ok) {
    throw new Error('获取覆盖率报告失败');
  }
  return response.json();
};

const fetchCoverageTrend = async (days: number = 30): Promise<CoverageTrend[]> => {
  const response = await fetch(`/api/test-coverage/trend?days=${days}`);
  if (!response.ok) {
    throw new Error('获取覆盖率趋势失败');
  }
  return response.json();
};

const fetchModuleCoverage = async (
  minCoverage: number = 0,
  maxCoverage: number = 100
): Promise<CoverageMetrics[]> => {
  const response = await fetch(
    `/api/test-coverage/modules?min_coverage=${minCoverage}&max_coverage=${maxCoverage}`
  );
  if (!response.ok) {
    throw new Error('获取模块覆盖率失败');
  }
  return response.json();
};

const fetchCoverageThresholds = async (): Promise<CoverageThreshold> => {
  const response = await fetch('/api/test-coverage/thresholds');
  if (!response.ok) {
    throw new Error('获取覆盖率阈值失败');
  }
  return response.json();
};

const updateCoverageThresholds = async (thresholds: CoverageThreshold): Promise<CoverageThreshold> => {
  const response = await fetch('/api/test-coverage/thresholds', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(thresholds),
  });
  if (!response.ok) {
    throw new Error('更新覆盖率阈值失败');
  }
  return response.json();
};

const fetchQualityGate = async (): Promise<QualityGateResult> => {
  const response = await fetch('/api/test-coverage/quality-gate');
  if (!response.ok) {
    throw new Error('获取质量门禁状态失败');
  }
  return response.json();
};

// 主组件
const TestCoverageDashboard: React.FC = () => {
  const [trendDays, setTrendDays] = useState(30);
  const [thresholdModalVisible, setThresholdModalVisible] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 获取覆盖率报告
  const { data: coverageReport, isLoading: reportLoading, refetch: refetchReport } = useQuery({
    queryKey: ['coverage-report'],
    queryFn: fetchCoverageReport,
    refetchInterval: 60000, // 每分钟刷新一次
  });

  // 获取覆盖率趋势
  const { data: coverageTrend, isLoading: _trendLoading } = useQuery({
    queryKey: ['coverage-trend', trendDays],
    queryFn: () => fetchCoverageTrend(trendDays),
  });

  // 获取模块覆盖率
  const { data: moduleCoverage, isLoading: moduleLoading } = useQuery({
    queryKey: ['module-coverage'],
    queryFn: () => fetchModuleCoverage(),
  });

  // 获取阈值配置
  const { data: thresholds, isLoading: thresholdsLoading } = useQuery({
    queryKey: ['coverage-thresholds'],
    queryFn: fetchCoverageThresholds,
  });

  // 获取质量门禁状态
  const { data: qualityGate, isLoading: qualityGateLoading } = useQuery({
    queryKey: ['quality-gate'],
    queryFn: fetchQualityGate,
    refetchInterval: 30000, // 每30秒检查一次
  });

  // 更新阈值配置
  const updateThresholdsMutation = useMutation({
    mutationFn: updateCoverageThresholds,
    onSuccess: (data) => {
      MessageManager.success('阈值配置更新成功');
      setThresholdModalVisible(false);
      queryClient.setQueryData(['coverage-thresholds'], data);
    },
    onError: (error) => {
      MessageManager.error(`更新阈值失败: ${error.message}`);
    },
  });

  // 处理阈值表单提交
  const handleThresholdSubmit = (values: CoverageThreshold) => {
    updateThresholdsMutation.mutate(values);
  };

  // 模块覆盖率表格列配置
  const moduleColumns: ColumnsType<CoverageMetrics> = [
    {
      title: '模块名称',
      dataIndex: 'module_name',
      key: 'module_name',
      width: 200,
      render: (text, record) => (
        <Tooltip title={record.file_path}>
          <span>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '覆盖率',
      dataIndex: 'coverage_percentage',
      key: 'coverage_percentage',
      width: 120,
      sorter: (a, b) => a.coverage_percentage - b.coverage_percentage,
      render: (value) => {
        const color = value >= 80 ? COLORS.success : value >= 60 ? COLORS.warning : COLORS.error;
        return (
          <Progress
            percent={value}
            size="small"
            strokeColor={color}
            format={(percent) => `${percent?.toFixed(1)}%`}
          />
        );
      },
    },
    {
      title: '行覆盖率',
      key: 'lines',
      width: 120,
      render: (_, record) => (
        <span>
          {record.lines_covered}/{record.lines_total}
          <span style={{ marginLeft: 4, color: COLORS.textSecondary }}>
            ({((record.lines_covered / record.lines_total) * 100).toFixed(1)}%)
          </span>
        </span>
      ),
    },
    {
      title: '分支覆盖率',
      key: 'branches',
      width: 120,
      render: (_, record) => (
        <span>
          {record.branches_covered}/{record.branches_total}
          <span style={{ marginLeft: 4, color: COLORS.textSecondary }}>
            ({((record.branches_covered / record.branches_total) * 100).toFixed(1)}%)
          </span>
        </span>
      ),
    },
    {
      title: '函数覆盖率',
      key: 'functions',
      width: 120,
      render: (_, record) => (
        <span>
          {record.functions_covered}/{record.functions_total}
          <span style={{ marginLeft: 4, color: COLORS.textSecondary }}>
            ({((record.functions_covered / record.functions_total) * 100).toFixed(1)}%)
          </span>
        </span>
      ),
    },
    {
      title: '最后更新',
      dataIndex: 'last_updated',
      key: 'last_updated',
      width: 150,
      render: (value) => dayjs(value).format('YYYY-MM-DD HH:mm:ss'),
    },
  ];

  // 覆盖率趋势图表配置
  const trendConfig = {
    data: coverageTrend?.map(item => ({
      date: dayjs(item.date).format('MM-DD'),
      后端覆盖率: item.backend_coverage,
      前端覆盖率: item.frontend_coverage,
      总体覆盖率: item.total_coverage,
    })) || [],
    xField: 'date',
    yField: 'value',
    seriesField: 'type',
    smooth: true,
    color: [COLORS.primary, COLORS.success, COLORS.warning],
    point: {
      size: 3,
      shape: 'circle',
    },
    tooltip: {
      formatter: (datum: ChartDatum & { type?: string; value?: number }) => ({
        name: datum.type,
        value: `${datum.value?.toFixed(1)}%`,
      }),
    },
  };

  // 模块覆盖率柱状图配置
  const moduleCoverageConfig = {
    data: moduleCoverage?.slice(0, 10).map(item => ({
      module: item.module_name.length > 15 ? item.module_name.substring(0, 15) + '...' : item.module_name,
      覆盖率: item.coverage_percentage,
    })) || [],
    xField: 'module',
    yField: '覆盖率',
    color: (datum: ChartDatum) => {
      return datum.覆盖率 >= 80 ? COLORS.success : datum.覆盖率 >= 60 ? COLORS.warning : COLORS.error;
    },
    label: {
      position: 'middle',
      formatter: (datum: ChartDatum) => `${datum.覆盖率.toFixed(1)}%`,
    },
    meta: {
      覆盖率: {
        alias: '覆盖率(%)',
        min: 0,
        max: 100,
      },
    },
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题和操作按钮 */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>测试覆盖率监控</h1>
        <Space>
          <Button
            type="default"
            icon={<SettingOutlined />}
            onClick={() => setThresholdModalVisible(true)}
            loading={thresholdsLoading}
          >
            阈值设置
          </Button>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={() => refetchReport()}
            loading={reportLoading}
          >
            刷新数据
          </Button>
        </Space>
      </div>

      {/* 质量门禁状态 */}
      {!qualityGateLoading && qualityGate && (
        <Alert
          style={{ marginBottom: 24 }}
          type={qualityGate.passed ? 'success' : 'error'}
          message={
            qualityGate.passed
              ? '✅ 质量门禁通过 - 所有覆盖率指标都达到要求'
              : '❌ 质量门禁失败 - 存在不达标的覆盖率指标'
          }
          description={
            !qualityGate.passed && qualityGate.failed_checks.length > 0 && (
              <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
                {qualityGate.failed_checks.map((check, index) => (
                  <li key={index}>{check}</li>
                ))}
              </ul>
            )
          }
          showIcon
        />
      )}

      {/* 总体覆盖率统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总体覆盖率"
              value={coverageReport?.total_coverage || 0}
              precision={1}
              suffix="%"
              valueStyle={{
                color: (coverageReport?.total_coverage || 0) >= (thresholds?.total_threshold || 75) ? COLORS.success : COLORS.error,
              }}
              prefix={(coverageReport?.total_coverage || 0) >= (thresholds?.total_threshold || 75) ? <RiseOutlined /> : <FallOutlined />}
            />
            {thresholds && (
              <div style={{ fontSize: 12, color: COLORS.textSecondary, marginTop: 8 }}>
                目标: {thresholds.total_threshold}%
              </div>
            )}
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="后端覆盖率"
              value={coverageReport?.backend_coverage || 0}
              precision={1}
              suffix="%"
              valueStyle={{
                color: (coverageReport?.backend_coverage || 0) >= (thresholds?.backend_threshold || 80) ? COLORS.success : COLORS.error,
              }}
              prefix={(coverageReport?.backend_coverage || 0) >= (thresholds?.backend_threshold || 80) ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            />
            {thresholds && (
              <div style={{ fontSize: 12, color: COLORS.textSecondary, marginTop: 8 }}>
                目标: {thresholds.backend_threshold}%
              </div>
            )}
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="前端覆盖率"
              value={coverageReport?.frontend_coverage || 0}
              precision={1}
              suffix="%"
              valueStyle={{
                color: (coverageReport?.frontend_coverage || 0) >= (thresholds?.frontend_threshold || 70) ? COLORS.success : COLORS.error,
              }}
              prefix={(coverageReport?.frontend_coverage || 0) >= (thresholds?.frontend_threshold || 70) ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            />
            {thresholds && (
              <div style={{ fontSize: 12, color: COLORS.textSecondary, marginTop: 8 }}>
                目标: {thresholds.frontend_threshold}%
              </div>
            )}
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="测试执行时间"
              value={coverageReport?.test_execution_time || 0}
              precision={1}
              suffix="秒"
              prefix={<InfoCircleOutlined />}
            />
            <div style={{ fontSize: 12, color: COLORS.textSecondary, marginTop: 8 }}>
              总测试数: {coverageReport?.total_tests || 0}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 详细信息标签页 */}
      <Tabs
        defaultActiveKey="trend"
        items={[
          {
            key: 'trend',
            label: '覆盖率趋势',
            children: (
              <Card>
                <div style={{ marginBottom: 16 }}>
                  <Space>
                    <span>时间范围:</span>
                    <DatePicker.RangePicker
                      defaultValue={[
                        dayjs().subtract(trendDays, 'day'),
                        dayjs(),
                      ]}
                      onChange={(dates) => {
                        if (dates && dates[0] && dates[1]) {
                          const days = dates[1].diff(dates[0], 'day');
                          setTrendDays(days);
                        }
                      }}
                    />
                  </Space>
                </div>
                <Line {...trendConfig} height={300} />
              </Card>
            ),
          },
          {
            key: 'modules',
            label: '模块详情',
            children: (
              <Card>
                <Table
                  columns={moduleColumns}
                  dataSource={moduleCoverage}
                  rowKey="module_name"
                  loading={moduleLoading}
                  pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 个模块`,
                  }}
                  scroll={{ x: 800 }}
                />
              </Card>
            ),
          },
          {
            key: 'chart',
            label: '模块覆盖率图表',
            children: (
              <Card>
                <Column {...moduleCoverageConfig} height={400} />
              </Card>
            ),
          },
        ]}
      />

      {/* 阈值设置弹窗 */}
      <Modal
        title="覆盖率阈值设置"
        open={thresholdModalVisible}
        onCancel={() => setThresholdModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={updateThresholdsMutation.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={thresholds}
          onFinish={handleThresholdSubmit}
        >
          <Form.Item
            label="后端覆盖率阈值 (%)"
            name="backend_threshold"
            rules={[
              { required: true, message: '请输入后端覆盖率阈值' },
              { type: 'number', min: 0, max: 100, message: '阈值范围为 0-100' },
            ]}
          >
            <InputNumber
              min={0}
              max={100}
              precision={1}
              style={{ width: '100%' }}
              addonAfter="%"
            />
          </Form.Item>
          <Form.Item
            label="前端覆盖率阈值 (%)"
            name="frontend_threshold"
            rules={[
              { required: true, message: '请输入前端覆盖率阈值' },
              { type: 'number', min: 0, max: 100, message: '阈值范围为 0-100' },
            ]}
          >
            <InputNumber
              min={0}
              max={100}
              precision={1}
              style={{ width: '100%' }}
              addonAfter="%"
            />
          </Form.Item>
          <Form.Item
            label="总体覆盖率阈值 (%)"
            name="total_threshold"
            rules={[
              { required: true, message: '请输入总体覆盖率阈值' },
              { type: 'number', min: 0, max: 100, message: '阈值范围为 0-100' },
            ]}
          >
            <InputNumber
              min={0}
              max={100}
              precision={1}
              style={{ width: '100%' }}
              addonAfter="%"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TestCoverageDashboard;
