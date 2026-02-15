import React, { useState, useMemo, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  DatePicker,
  Select,
  Button,
  Tabs,
  Tag,
  Progress,
  Space,
  Typography,
  Table,
  Tooltip,
} from 'antd';
import { useMutation, useQuery } from '@tanstack/react-query';
import { MessageManager } from '@/utils/messageManager';
import { Pie, Column, Line } from '@ant-design/plots';
import {
  DollarOutlined,
  AccountBookOutlined,
  RiseOutlined,
  DownloadOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import type { ColumnsType } from 'antd/es/table';

import { rentContractService } from '@/services/rentContractService';
import { RENTAL_QUERY_KEYS } from '@/constants/queryKeys';
import { useArrayListData } from '@/hooks/useArrayListData';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import PageContainer from '@/components/Common/PageContainer';
import { ChartErrorBoundary } from '@/components/Analytics';

import {
  OwnershipRentStatistics,
  AssetRentStatistics,
  MonthlyRentStatistics,
  RentStatisticsOverview,
} from '@/types/rentContract';
import { formatCurrency } from '@/utils/format';
import { createLogger } from '@/utils/logger';
import { CHART_COLORS } from '@/styles/colorMap';
import styles from './RentStatisticsPage.module.css';

const pageLogger = createLogger('RentStatistics');

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Title } = Typography;

dayjs.locale('zh-cn');

interface ChartDatum {
  type: string;
  value: number;
  [key: string]: unknown;
}

interface PieChartDatum {
  type: string;
  value: number;
  paid: number;
  overdue: number;
}

interface LineChartDatum {
  month: string;
  due: number;
  paid: number;
  overdue: number;
  rate: number;
}

interface RentStatisticsData {
  overview: RentStatisticsOverview;
  ownershipData: OwnershipRentStatistics[];
  assetData: AssetRentStatistics[];
  monthlyData: MonthlyRentStatistics[];
}

type Tone = 'primary' | 'success' | 'warning' | 'error';

const TONE_COLOR_MAP: Record<Tone, string> = {
  primary: 'var(--color-primary)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  error: 'var(--color-error)',
};

const BAR_SERIES_COLOR_MAP: Record<string, string> = {
  应收金额: TONE_COLOR_MAP.primary,
  已收金额: TONE_COLOR_MAP.success,
  欠款金额: TONE_COLOR_MAP.error,
};

const normalizePercentage = (value: number | string): number => {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return 0;
  }
  return Math.min(100, Math.max(0, numericValue));
};

const resolvePaymentTone = (rate: number): Tone => {
  if (rate >= 90) {
    return 'success';
  }
  if (rate >= 70) {
    return 'warning';
  }
  return 'error';
};

const resolvePaymentLabel = (rate: number): string => {
  if (rate >= 90) {
    return '优';
  }
  if (rate >= 70) {
    return '中';
  }
  return '低';
};

const resolveOverdueTone = (amount: number): Tone => {
  if (amount > 0) {
    return 'error';
  }
  return 'success';
};

const truncateText = (value: string | null | undefined, maxLength: number): string => {
  if (value == null) {
    return '—';
  }
  const normalizedValue = value.trim();
  if (normalizedValue === '') {
    return '—';
  }
  if (normalizedValue.length <= maxLength) {
    return normalizedValue;
  }
  return `${normalizedValue.slice(0, maxLength)}...`;
};

const RentStatisticsPage: React.FC = () => {
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().startOf('year'),
    dayjs().endOf('year'),
  ]);
  const [selectedYear, setSelectedYear] = useState<number>(dayjs().year());

  const startDateStr = useMemo(() => dateRange[0].format('YYYY-MM-DD'), [dateRange]);
  const endDateStr = useMemo(() => dateRange[1].format('YYYY-MM-DD'), [dateRange]);

  const statisticsQuery = useQuery<RentStatisticsData, Error>({
    queryKey: RENTAL_QUERY_KEYS.rentStatistics({
      start: startDateStr,
      end: endDateStr,
      year: selectedYear,
    }),
    queryFn: async () => {
      try {
        const [overview, ownershipData, assetData, monthlyData] = await Promise.all([
          rentContractService.getStatisticsOverview({
            start_date: startDateStr,
            end_date: endDateStr,
          }),
          rentContractService.getOwnershipStatistics({
            start_date: startDateStr,
            end_date: endDateStr,
          }),
          rentContractService.getAssetStatistics({
            start_date: startDateStr,
            end_date: endDateStr,
          }),
          rentContractService.getMonthlyStatistics({
            year: selectedYear,
          }),
        ]);

        return {
          overview,
          ownershipData,
          assetData,
          monthlyData,
        };
      } catch (error) {
        pageLogger.error('Statistics fetch error:', error as Error);
        throw error;
      }
    },
  });

  useEffect(() => {
    if (statisticsQuery.isError === true) {
      MessageManager.error('获取统计数据失败');
    }
  }, [statisticsQuery.isError]);

  const overviewData: RentStatisticsOverview | null = statisticsQuery.data?.overview ?? null;
  const ownershipStats: OwnershipRentStatistics[] = statisticsQuery.data?.ownershipData ?? [];
  const assetStats: AssetRentStatistics[] = useMemo(
    () => statisticsQuery.data?.assetData ?? [],
    [statisticsQuery.data?.assetData]
  );
  const monthlyStats: MonthlyRentStatistics[] = statisticsQuery.data?.monthlyData ?? [];
  const isStatisticsLoading = statisticsQuery.isLoading || statisticsQuery.isFetching;

  const {
    data: assetRows,
    loading: assetTableLoading,
    pagination: assetPagination,
    loadList: loadAssetList,
    updatePagination: updateAssetPagination,
  } = useArrayListData<AssetRentStatistics, Record<string, never>>({
    items: assetStats,
    initialFilters: {},
    initialPageSize: 10,
  });

  useEffect(() => {
    void loadAssetList({ page: 1 });
  }, [assetStats, loadAssetList]);

  // 导出统计数据
  const exportStatisticsMutation = useMutation({
    mutationFn: async () => {
      return await rentContractService.exportStatistics({
        start_date: startDateStr,
        end_date: endDateStr,
      });
    },
    onSuccess: blob => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `租金统计报表_${dateRange[0].format('YYYYMMDD')}_${dateRange[1].format('YYYYMMDD')}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      MessageManager.success('导出成功');
    },
    onError: (error: unknown) => {
      pageLogger.error('Export failed:', error as Error);
      MessageManager.error('导出失败');
    },
  });

  // 权属方统计表格列
  const ownershipColumns: ColumnsType<OwnershipRentStatistics> = [
    {
      title: '权属方名称',
      dataIndex: 'ownership_name',
      key: 'ownership_name',
      render: (text: string, record) => (
        <div className={styles.nameCell}>
          <div className={styles.primaryText}>{text}</div>
          <div className={styles.secondaryText}>
            {truncateText(record.ownership_short_name, 24)}
          </div>
        </div>
      ),
    },
    {
      title: '合同数量',
      dataIndex: 'contract_count',
      key: 'contract_count',
      align: 'center',
      render: (count: number) => <Tag className={styles.countTag}>{count} 个</Tag>,
    },
    {
      title: '应收总额',
      dataIndex: 'total_due_amount',
      key: 'total_due_amount',
      align: 'right',
      render: (amount: number) => formatCurrency(amount),
    },
    {
      title: '已收总额',
      dataIndex: 'total_paid_amount',
      key: 'total_paid_amount',
      align: 'right',
      render: (amount: number) => (
        <span className={styles.positiveValue}>{formatCurrency(amount)}</span>
      ),
    },
    {
      title: '欠款总额',
      dataIndex: 'total_overdue_amount',
      key: 'total_overdue_amount',
      align: 'right',
      render: (amount: number) => {
        const tone = resolveOverdueTone(amount);
        return (
          <Space size={6} className={styles.inlineStatus} wrap>
            <span className={[styles.valueText, toneClassMap[tone]].join(' ')}>
              {formatCurrency(amount)}
            </span>
            <Tag className={[styles.statusTag, toneClassMap[tone]].join(' ')}>
              {tone === 'error' ? '有欠款' : '正常'}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: '收缴率',
      dataIndex: 'payment_rate',
      key: 'payment_rate',
      align: 'center',
      render: (rate: number | string) => {
        const percentage = normalizePercentage(rate);
        const tone = resolvePaymentTone(percentage);

        return (
          <div className={styles.paymentRateCell}>
            <Progress
              type="circle"
              percent={percentage}
              size={50}
              strokeColor={TONE_COLOR_MAP[tone]}
              format={() => `${percentage.toFixed(1)}%`}
            />
            <Tag className={[styles.statusTag, toneClassMap[tone]].join(' ')}>
              {resolvePaymentLabel(percentage)}
            </Tag>
          </div>
        );
      },
    },
  ];

  // 资产统计表格列
  const assetColumns: ColumnsType<AssetRentStatistics> = [
    {
      title: '资产名称',
      dataIndex: 'asset_name',
      key: 'asset_name',
      render: (text: string, record) => (
        <div className={styles.nameCell}>
          <div className={styles.primaryText}>{text}</div>
          <div className={styles.secondaryText}>
            <Tooltip title={record.asset_address ?? '暂无地址'}>
              <span>{truncateText(record.asset_address, 30)}</span>
            </Tooltip>
          </div>
        </div>
      ),
    },
    {
      title: '合同数量',
      dataIndex: 'contract_count',
      key: 'contract_count',
      align: 'center',
      render: (count: number) => <Tag className={styles.countTag}>{count} 个</Tag>,
    },
    {
      title: '应收总额',
      dataIndex: 'total_due_amount',
      key: 'total_due_amount',
      align: 'right',
      render: (amount: number) => formatCurrency(amount),
    },
    {
      title: '已收总额',
      dataIndex: 'total_paid_amount',
      key: 'total_paid_amount',
      align: 'right',
      render: (amount: number) => (
        <span className={styles.positiveValue}>{formatCurrency(amount)}</span>
      ),
    },
    {
      title: '欠款总额',
      dataIndex: 'total_overdue_amount',
      key: 'total_overdue_amount',
      align: 'right',
      render: (amount: number) => {
        const tone = resolveOverdueTone(amount);
        return (
          <Space size={6} className={styles.inlineStatus} wrap>
            <span className={[styles.valueText, toneClassMap[tone]].join(' ')}>
              {formatCurrency(amount)}
            </span>
            <Tag className={[styles.statusTag, toneClassMap[tone]].join(' ')}>
              {tone === 'error' ? '有欠款' : '正常'}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: '收缴率',
      dataIndex: 'payment_rate',
      key: 'payment_rate',
      align: 'center',
      render: (rate: number | string) => {
        const percentage = normalizePercentage(rate);
        const tone = resolvePaymentTone(percentage);

        return (
          <div className={styles.paymentRateCell}>
            <Progress
              type="circle"
              percent={percentage}
              size={50}
              strokeColor={TONE_COLOR_MAP[tone]}
              format={() => `${percentage.toFixed(1)}%`}
            />
            <Tag className={[styles.statusTag, toneClassMap[tone]].join(' ')}>
              {resolvePaymentLabel(percentage)}
            </Tag>
          </div>
        );
      },
    },
  ];

  // 准备图表数据
  const ownershipChartData: PieChartDatum[] = ownershipStats.map(item => ({
    type: item.ownership_name,
    value: Number(item.total_due_amount),
    paid: Number(item.total_paid_amount),
    overdue: Number(item.total_overdue_amount),
  }));

  const ownershipPieConfig = {
    data: ownershipChartData,
    angleField: 'value',
    colorField: 'type',
    color: CHART_COLORS,
    radius: 0.8,
    innerRadius: 0.4,
    label: {
      type: 'outer' as const,
      content: (datum: { type?: string; percent?: number }) => {
        const name = typeof datum.type === 'string' ? datum.type : '';
        const percentValue = typeof datum.percent === 'number' ? datum.percent : undefined;
        const percentText = percentValue !== undefined ? `${(percentValue * 100).toFixed(1)}%` : '';
        return percentText !== '' ? `${name} ${percentText}` : name;
      },
    },
    legend: {
      layout: 'horizontal' as const,
      position: 'bottom' as const,
    },
    tooltip: {
      formatter: (datum: PieChartDatum) => ({
        name: datum.type,
        value: formatCurrency(datum.value),
      }),
    },
  };

  const monthlyChartData: LineChartDatum[] = monthlyStats.map(item => ({
    month: item.year_month,
    due: Number(item.total_due_amount),
    paid: Number(item.total_paid_amount),
    overdue: Number(item.total_overdue_amount),
    rate: Number(item.payment_rate),
  }));

  // Prepare monthly bar chart data - transform to stacked format
  const monthlyBarData = monthlyStats.flatMap(item => [
    { month: item.year_month, type: '应收金额', value: Number(item.total_due_amount) },
    { month: item.year_month, type: '已收金额', value: Number(item.total_paid_amount) },
    { month: item.year_month, type: '欠款金额', value: Number(item.total_overdue_amount) },
  ]);

  const monthlyBarConfig = {
    data: monthlyBarData,
    xField: 'month',
    yField: 'value',
    seriesField: 'type',
    color: ({ type }: { type: string }) => BAR_SERIES_COLOR_MAP[type] ?? TONE_COLOR_MAP.primary,
    isGroup: true,
    columnStyle: {
      fillOpacity: 0.8,
    },
    legend: {
      position: 'top' as const,
    },
    tooltip: {
      formatter: (datum: ChartDatum) => ({
        name: datum.type,
        value: formatCurrency(datum.value),
      }),
    },
    yAxis: {
      label: {
        formatter: (value: number) => formatCurrency(value),
      },
    },
  };

  const monthlyLineConfig = {
    data: monthlyChartData,
    xField: 'month',
    yField: 'rate',
    smooth: true,
    color: TONE_COLOR_MAP.success,
    lineStyle: {
      lineWidth: 2,
    },
    point: {
      size: 4,
      shape: 'circle',
    },
    tooltip: {
      formatter: (datum: LineChartDatum) => ({
        name: '收缴率',
        value: `${datum.rate.toFixed(2)}%`,
      }),
    },
    yAxis: {
      min: 0,
      max: 100,
      label: {
        formatter: (value: number) => `${value}%`,
      },
    },
  };

  // 标签页配置
  const tabItems = [
    {
      key: 'ownership',
      label: '权属方统计',
      children: (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="权属方租金分布" loading={isStatisticsLoading}>
              <ChartErrorBoundary>
                <Pie {...ownershipPieConfig} height={300} />
              </ChartErrorBoundary>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="权属方收缴情况" loading={isStatisticsLoading}>
              <Table
                columns={ownershipColumns}
                dataSource={ownershipStats}
                rowKey="ownership_id"
                pagination={false}
                loading={isStatisticsLoading}
                scroll={{ x: 800 }}
              />
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'asset',
      label: '资产统计',
      children: (
        <Row gutter={[16, 16]}>
          <Col xs={24}>
            <Card title="资产租金统计" loading={isStatisticsLoading}>
              <TableWithPagination
                columns={assetColumns}
                dataSource={assetRows}
                rowKey="asset_id"
                loading={isStatisticsLoading || assetTableLoading}
                paginationState={assetPagination}
                onPageChange={updateAssetPagination}
                paginationProps={{
                  showSizeChanger: true,
                  showQuickJumper: true,
                }}
                scroll={{ x: 1000 }}
              />
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'monthly',
      label: '月度趋势',
      children: (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={16}>
            <Card title="月度租金趋势" loading={isStatisticsLoading}>
              <ChartErrorBoundary>
                <Column {...monthlyBarConfig} height={400} />
              </ChartErrorBoundary>
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card title="收缴率趋势" loading={isStatisticsLoading}>
              <ChartErrorBoundary>
                <Line {...monthlyLineConfig} height={400} />
              </ChartErrorBoundary>
            </Card>
          </Col>
        </Row>
      ),
    },
  ];

  const overdueTone: Tone = Number(overviewData?.total_overdue ?? 0) > 0 ? 'error' : 'success';
  const paymentRateTone: Tone = resolvePaymentTone(Number(overviewData?.payment_rate ?? 0));

  return (
    <PageContainer
      className={styles.statisticsPage}
      contentStyle={{ background: 'var(--color-bg-quaternary)' }}
    >
      <Card className={styles.mainCard}>
        <div className={styles.headerSection}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={3} className={styles.pageTitle}>
                <AccountBookOutlined /> 租金统计报表
              </Title>
            </Col>
            <Col className={styles.headerActions}>
              <Space size={12} wrap className={styles.headerActionGroup}>
                <RangePicker
                  value={dateRange}
                  onChange={dates => {
                    if (dates != null) {
                      setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs]);
                    }
                  }}
                  className={styles.dateRangePicker}
                />
                <Select
                  value={selectedYear}
                  onChange={setSelectedYear}
                  className={styles.yearSelect}
                >
                  {Array.from({ length: 5 }, (_, i) => dayjs().year() - i).map(year => (
                    <Option key={year} value={year}>
                      {year}年
                    </Option>
                  ))}
                </Select>
                <Button
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={() => void statisticsQuery.refetch()}
                  loading={statisticsQuery.isFetching}
                  className={styles.actionButton}
                >
                  刷新
                </Button>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={() => exportStatisticsMutation.mutate()}
                  loading={exportStatisticsMutation.isPending}
                  className={styles.actionButton}
                >
                  导出
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        {/* 概览统计卡片 */}
        {overviewData != null && (
          <Row gutter={[16, 16]} className={styles.overviewRow}>
            <Col xs={24} sm={12} md={6}>
              <Card className={[styles.metricCard, toneClassMap.primary].join(' ')}>
                <Statistic
                  title="应收总额"
                  value={Number(overviewData.total_due ?? 0)}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="元"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card className={[styles.metricCard, toneClassMap.success].join(' ')}>
                <Statistic
                  title="已收总额"
                  value={Number(overviewData.total_paid ?? 0)}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="元"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card className={[styles.metricCard, toneClassMap[overdueTone]].join(' ')}>
                <Statistic
                  title="欠款总额"
                  value={Number(overviewData.total_overdue ?? 0)}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="元"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card className={[styles.metricCard, toneClassMap[paymentRateTone]].join(' ')}>
                <Statistic
                  title="收缴率"
                  value={normalizePercentage(Number(overviewData.payment_rate ?? 0))}
                  precision={1}
                  prefix={<RiseOutlined />}
                  suffix="%"
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* V2: Operational Indicators */}
        {overviewData != null && (
          <>
            <Title level={4} className={styles.sectionTitle}>
              运营指标
            </Title>
            <Row gutter={[16, 16]} className={styles.operationRow}>
              <Col xs={24} sm={12} md={6}>
                <Card className={[styles.metricCard, toneClassMap.primary].join(' ')}>
                  <Statistic
                    title="平均租金单价"
                    value={Number(overviewData.average_unit_price ?? 0)}
                    precision={2}
                    prefix={<DollarOutlined />}
                    suffix="元/㎡/月"
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card className={[styles.metricCard, toneClassMap.success].join(' ')}>
                  <Statistic
                    title="合同续签率"
                    value={Number(overviewData.renewal_rate ?? 0)}
                    precision={1}
                    prefix={<ReloadOutlined />}
                    suffix="%"
                  />
                </Card>
              </Col>
            </Row>
          </>
        )}

        <Tabs defaultActiveKey="ownership" type="card" items={tabItems} />
      </Card>
    </PageContainer>
  );
};

export default RentStatisticsPage;
