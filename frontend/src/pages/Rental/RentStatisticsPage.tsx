import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  DatePicker,
  Select,
  Button,
  Tabs,
  Tag,
  Progress,
  Space,
  Typography
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { Pie, Column, Line } from '@ant-design/plots';
import {
  DollarOutlined,
  AccountBookOutlined,
  RiseOutlined,
  DownloadOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import type { ColumnsType } from 'antd/es/table';

import {
  rentContractService
} from '@/services/rentContractService';

import {
  OwnershipRentStatistics,
  AssetRentStatistics,
  MonthlyRentStatistics,
  RentStatisticsOverview
} from '@/types/rentContract';
import { formatCurrency } from '@/utils/format';
import { createLogger } from '@/utils/logger';
import { COLORS, CHART_COLORS } from '@/styles/colorMap';

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
  // eslint-disable-next-line @typescript-eslint/naming-convention
  due: number;
  // eslint-disable-next-line @typescript-eslint/naming-convention
  paid: number;
  // eslint-disable-next-line @typescript-eslint/naming-convention
  overdue: number;
  rate: number;
}

const RentStatisticsPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().startOf('year'),
    dayjs().endOf('year')
  ]);
  const [overviewData, setOverviewData] = useState<RentStatisticsOverview | null>(null);
  const [ownershipStats, setOwnershipStats] = useState<OwnershipRentStatistics[]>([]);
  const [assetStats, setAssetStats] = useState<AssetRentStatistics[]>([]);
  const [monthlyStats, setMonthlyStats] = useState<MonthlyRentStatistics[]>([]);
  const [selectedYear, setSelectedYear] = useState<number>(dayjs().year());

  // 获取统计数据
  const fetchStatistics = async () => {
    setLoading(true);
    try {
      const [startDate, endDate] = dateRange;
      const startStr = startDate.format('YYYY-MM-DD');
      const endStr = endDate.format('YYYY-MM-DD');

      // 并行获取所有统计数据
      const [overview, ownershipData, assetData, monthlyData] = await Promise.all([
        rentContractService.getStatisticsOverview({
          start_date: startStr,
          end_date: endStr
        }),
        rentContractService.getOwnershipStatistics({
          start_date: startStr,
          end_date: endStr
        }),
        rentContractService.getAssetStatistics({
          start_date: startStr,
          end_date: endStr
        }),
        rentContractService.getMonthlyStatistics({
          year: selectedYear
        })
      ]);

      setOverviewData(overview);
      setOwnershipStats(ownershipData);
      setAssetStats(assetData);
      setMonthlyStats(monthlyData);
    } catch (error) {
      pageLogger.error('Statistics fetch error:', error as Error);
      MessageManager.error('获取统计数据失败，显示模拟数据');

      // 使用模拟数据作为降级方案
      const mockOverview: RentStatisticsOverview = {
        total_due: 1500000,
        total_paid: 1200000,
        total_overdue: 300000,
        total_records: 120,
        payment_rate: 80,
        status_breakdown: [
          { status: 'active', count: 98, due_amount: 1300000, paid_amount: 1100000 },
          { status: 'pending', count: 22, due_amount: 200000, paid_amount: 100000 },
        ],
        monthly_breakdown: [
          { year_month: '2024-12', due_amount: 500000, paid_amount: 450000, overdue_amount: 50000 },
          { year_month: '2024-11', due_amount: 500000, paid_amount: 400000, overdue_amount: 100000 },
          { year_month: '2024-10', due_amount: 500000, paid_amount: 350000, overdue_amount: 150000 },
        ],
        average_unit_price: 30,
        renewal_rate: 85,
      };

      const mockOwnershipStats: OwnershipRentStatistics[] = [
        {
          ownership_id: '1',
          ownership_name: '权属方A',
          ownership_short_name: '权属A',
          contract_count: 30,
          total_due_amount: 500000,
          total_paid_amount: 450000,
          total_overdue_amount: 50000,
          payment_rate: 90,
        },
        {
          ownership_id: '2',
          ownership_name: '权属方B',
          ownership_short_name: '权属B',
          contract_count: 25,
          total_due_amount: 400000,
          total_paid_amount: 350000,
          total_overdue_amount: 50000,
          payment_rate: 87.5,
        },
      ];

      const mockAssetStats: AssetRentStatistics[] = [
        {
          asset_id: '1',
          asset_name: '资产A',
          asset_address: '地址A',
          contract_count: 15,
          total_due_amount: 300000,
          total_paid_amount: 280000,
          total_overdue_amount: 20000,
          payment_rate: 93.3,
        },
      ];

      const mockMonthlyStats: MonthlyRentStatistics[] = Array.from({ length: 12 }, (_, i) => ({
        year_month: `2024-${String(i + 1).padStart(2, '0')}`,
        total_contracts: 10 + i,
        total_due_amount: 100000 + i * 10000,
        total_paid_amount: 80000 + i * 8000,
        total_overdue_amount: 20000 + i * 2000,
        payment_rate: 80 + i,
      }));

      setOverviewData(mockOverview);
      setOwnershipStats(mockOwnershipStats);
      setAssetStats(mockAssetStats);
      setMonthlyStats(mockMonthlyStats);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchStatistics();
  }, [dateRange, selectedYear]);

  // 导出统计数据
  const exportStatistics = async () => {
    try {
      const blob = await rentContractService.exportStatistics({
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD')
      });

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `租金统计报表_${dateRange[0].format('YYYYMMDD')}_${dateRange[1].format('YYYYMMDD')}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      MessageManager.success('导出成功');
    } catch (error) {
      pageLogger.error('Export failed:', error as Error);
      MessageManager.error('导出失败');
    }
  };

  // 权属方统计表格列
  const ownershipColumns: ColumnsType<OwnershipRentStatistics> = [
    {
      title: '权属方名称',
      dataIndex: 'ownership_name',
      key: 'ownership_name',
      render: (text: string, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: COLORS.textSecondary }}>
            {record.ownership_short_name}
          </div>
        </div>
      )
    },
    {
      title: '合同数量',
      dataIndex: 'contract_count',
      key: 'contract_count',
      align: 'center',
      render: (count: number) => <Tag color="blue">{count} 个</Tag>
    },
    {
      title: '应收总额',
      dataIndex: 'total_due_amount',
      key: 'total_due_amount',
      align: 'right',
      render: (amount: number) => formatCurrency(amount)
    },
    {
      title: '已收总额',
      dataIndex: 'total_paid_amount',
      key: 'total_paid_amount',
      align: 'right',
      render: (amount: number) => (
        <span style={{ color: COLORS.success }}>
          {formatCurrency(amount)}
        </span>
      )
    },
    {
      title: '欠款总额',
      dataIndex: 'total_overdue_amount',
      key: 'total_overdue_amount',
      align: 'right',
      render: (amount: number) => (
        <span style={{ color: amount > 0 ? COLORS.error : COLORS.success }}>
          {formatCurrency(amount)}
        </span>
      )
    },
    {
      title: '收缴率',
      dataIndex: 'payment_rate',
      key: 'payment_rate',
      align: 'center',
      render: (rate: number | string) => {
        const percentage = Number(rate);
        let color: string = COLORS.error;
        if (percentage >= 90) color = COLORS.success;
        else if (percentage >= 70) color = COLORS.warning;

        return (
          <Progress
            type="circle"
            percent={percentage}
            width={50}
            strokeColor={color}
            format={() => `${percentage.toFixed(1)}%`}
          />
        );
      }
    }
  ];

  // 资产统计表格列
  const assetColumns: ColumnsType<AssetRentStatistics> = [
    {
      title: '资产名称',
      dataIndex: 'asset_name',
      key: 'asset_name',
      render: (text: string, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: COLORS.textSecondary }}>
            {record.asset_address?.substring(0, 30)}...
          </div>
        </div>
      )
    },
    {
      title: '合同数量',
      dataIndex: 'contract_count',
      key: 'contract_count',
      align: 'center',
      render: (count: number) => <Tag color="blue">{count} 个</Tag>
    },
    {
      title: '应收总额',
      dataIndex: 'total_due_amount',
      key: 'total_due_amount',
      align: 'right',
      render: (amount: number) => formatCurrency(amount)
    },
    {
      title: '已收总额',
      dataIndex: 'total_paid_amount',
      key: 'total_paid_amount',
      align: 'right',
      render: (amount: number) => (
        <span style={{ color: COLORS.success }}>
          {formatCurrency(amount)}
        </span>
      )
    },
    {
      title: '欠款总额',
      dataIndex: 'total_overdue_amount',
      key: 'total_overdue_amount',
      align: 'right',
      render: (amount: number) => (
        <span style={{ color: amount > 0 ? COLORS.error : COLORS.success }}>
          {formatCurrency(amount)}
        </span>
      )
    },
    {
      title: '收缴率',
      dataIndex: 'payment_rate',
      key: 'payment_rate',
      align: 'center',
      render: (rate: number | string) => {
        const percentage = Number(rate);
        let color: string = COLORS.error;
        if (percentage >= 90) color = COLORS.success;
        else if (percentage >= 70) color = COLORS.warning;

        return (
          <Progress
            type="circle"
            percent={percentage}
            width={50}
            strokeColor={color}
            format={() => `${percentage.toFixed(1)}%`}
          />
        );
      }
    }
  ];

  // 准备图表数据
  const ownershipChartData: PieChartDatum[] = (ownershipStats || []).map(item => ({
    type: item.ownership_name,
    value: Number(item.total_due_amount),
    paid: Number(item.total_paid_amount),
    overdue: Number(item.total_overdue_amount)
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
      content: '{name} {percentage}',
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

  const monthlyChartData: LineChartDatum[] = (monthlyStats || []).map(item => ({
    month: item.year_month,
    due: Number(item.total_due_amount),
    paid: Number(item.total_paid_amount),
    overdue: Number(item.total_overdue_amount),
    rate: Number(item.payment_rate)
  }));

  // Prepare monthly bar chart data - transform to stacked format
  const monthlyBarData = (monthlyStats || []).flatMap(item => [
    { month: item.year_month, type: '应收金额', value: Number(item.total_due_amount) },
    { month: item.year_month, type: '已收金额', value: Number(item.total_paid_amount) },
    { month: item.year_month, type: '欠款金额', value: Number(item.total_overdue_amount) },
  ]);

  const monthlyBarConfig = {
    data: monthlyBarData,
    xField: 'month',
    yField: 'value',
    seriesField: 'type',
    color: ({ type }: { type: string }) => {
      if (type === '应收金额') return COLORS.primary;
      if (type === '已收金额') return COLORS.success;
      if (type === '欠款金额') return COLORS.error;
      return COLORS.primary;
    },
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
    color: COLORS.success,
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
            <Card title="权属方租金分布" loading={loading}>
              <Pie {...ownershipPieConfig} height={300} />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="权属方收缴情况" loading={loading}>
              <Table
                columns={ownershipColumns}
                dataSource={ownershipStats}
                rowKey="ownership_id"
                pagination={false}
                loading={loading}
                scroll={{ x: 800 }}
              />
            </Card>
          </Col>
        </Row>
      )
    },
    {
      key: 'asset',
      label: '资产统计',
      children: (
        <Row gutter={[16, 16]}>
          <Col xs={24}>
            <Card title="资产租金统计" loading={loading}>
              <Table
                columns={assetColumns}
                dataSource={assetStats}
                rowKey="asset_id"
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true
                }}
                loading={loading}
                scroll={{ x: 1000 }}
              />
            </Card>
          </Col>
        </Row>
      )
    },
    {
      key: 'monthly',
      label: '月度趋势',
      children: (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={16}>
            <Card title="月度租金趋势" loading={loading}>
              <Column {...monthlyBarConfig} height={400} />
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card title="收缴率趋势" loading={loading}>
              <Line {...monthlyLineConfig} height={400} />
            </Card>
          </Col>
        </Row>
      )
    }
  ];

  return (
    <div style={{ padding: '24px', background: COLORS.bgQuaternary, minHeight: '100vh' }}>
      <Card>
        <div style={{ marginBottom: '24px' }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={3} style={{ margin: 0 }}>
                <AccountBookOutlined /> 租金统计报表
              </Title>
            </Col>
            <Col>
              <Space>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => {
                    if (dates) setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs]);
                  }}
                  style={{ width: 300 }}
                />
                <Select
                  value={selectedYear}
                  onChange={setSelectedYear}
                  style={{ width: 120 }}
                >
                  {Array.from({ length: 5 }, (_, i) => dayjs().year() - i).map(year => (
                    <Option key={year} value={year}>{year}年</Option>
                  ))}
                </Select>
                <Button
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={fetchStatistics}
                  loading={loading}
                >
                  刷新
                </Button>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={exportStatistics}
                >
                  导出
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        {/* 概览统计卡片 */}
        {overviewData && (
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="应收总额"
                  value={Number(overviewData.total_due || 0)}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="元"
                  valueStyle={{ color: COLORS.primary }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="已收总额"
                  value={Number(overviewData.total_paid || 0)}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="元"
                  valueStyle={{ color: COLORS.success }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="欠款总额"
                  value={Number(overviewData.total_overdue || 0)}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="元"
                  valueStyle={{ color: Number(overviewData.total_overdue || 0) > 0 ? COLORS.error : COLORS.success }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="收缴率"
                  value={Number(overviewData.payment_rate || 0)}
                  precision={1}
                  prefix={<RiseOutlined />}
                  suffix="%"
                  valueStyle={{ color: Number(overviewData.payment_rate || 0) >= 90 ? COLORS.success : COLORS.warning }}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* V2: Operational Indicators */}
        {overviewData && (
          <>
            <Title level={4} style={{ marginBottom: '16px' }}>运营指标</Title>
            <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title="平均租金单价"
                    value={Number(overviewData.average_unit_price || 0)}
                    precision={2}
                    prefix={<DollarOutlined />}
                    suffix="元/㎡/月"
                    valueStyle={{ color: COLORS.primary }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title="合同续签率"
                    value={Number(overviewData.renewal_rate || 0)}
                    precision={1}
                    prefix={<ReloadOutlined />}
                    suffix="%"
                    valueStyle={{ color: COLORS.success }}
                  />
                </Card>
              </Col>
            </Row>
          </>
        )}

        <Tabs defaultActiveKey="ownership" type="card" items={tabItems} />
      </Card>
    </div>
  );
};

export default RentStatisticsPage;
