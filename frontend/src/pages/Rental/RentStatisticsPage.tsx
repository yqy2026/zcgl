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
  Typography,
  message
} from 'antd';
import { Pie, Column, Line } from '@ant-design/plots';
import {
  DollarOutlined,
  AccountBookOutlined,
  RiseOutlined,
  DownloadOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import moment from 'moment';
import 'moment/locale/zh-cn';
import type { ColumnsType } from 'antd/es/table';

import {
  rentContractService
} from '@/services/rentContractService';

type OwnershipRentStatistics = any;
type AssetRentStatistics = any;
type MonthlyRentStatistics = any;
import { formatCurrency } from '@/utils/format';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Title } = Typography;

moment.locale('zh-cn');

// 颜色配置
const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'];

const RentStatisticsPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[moment.Moment, moment.Moment]>([
    moment().startOf('year'),
    moment().endOf('year')
  ]);
  const [overviewData, setOverviewData] = useState<any>(null);
  const [ownershipStats, setOwnershipStats] = useState<OwnershipRentStatistics[]>([]);
  const [assetStats, setAssetStats] = useState<AssetRentStatistics[]>([]);
  const [monthlyStats, setMonthlyStats] = useState<MonthlyRentStatistics[]>([]);
  const [selectedYear, setSelectedYear] = useState<number>(moment().year());

  // 获取统计数据
  const fetchStatistics = async () => {
    setLoading(true);
    try {
      const [startDate, endDate] = dateRange;

      // 并行获取所有统计数据
      const [overview, ownershipData, assetData, monthlyData] = await Promise.all([
        rentContractService.getStatisticsOverview({
          start_date: startDate.format('YYYY-MM-DD'),
          end_date: endDate.format('YYYY-MM-DD')
        }),
        rentContractService.getOwnershipStatistics({
          start_date: startDate.format('YYYY-MM-DD'),
          end_date: endDate.format('YYYY-MM-DD')
        }),
        rentContractService.getAssetStatistics({
          start_date: startDate.format('YYYY-MM-DD'),
          end_date: endDate.format('YYYY-MM-DD')
        }),
        rentContractService.getMonthlyStatistics({
          year: selectedYear
        })
      ]);

      setOverviewData(overview);
      setOwnershipStats(ownershipData);
      setAssetStats(assetData);
      setMonthlyStats(monthlyData);
    } catch {
      message.error('获取统计数据失败');
      console.error('Statistics fetch error:', error);
      // 设置默认值以防止undefined错误
      setOverviewData(null);
      setOwnershipStats([]);
      setAssetStats([]);
      setMonthlyStats([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatistics();
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

      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };

  // 权属方统计表格列
  const ownershipColumns: ColumnsType<OwnershipRentStatistics> = [
    {
      title: '权属方名称',
      dataIndex: 'ownership_name',
      key: 'ownership_name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
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
      render: (count) => <Tag color="blue">{count} 个</Tag>
    },
    {
      title: '应收总额',
      dataIndex: 'total_due_amount',
      key: 'total_due_amount',
      align: 'right',
      render: (amount) => formatCurrency(amount)
    },
    {
      title: '已收总额',
      dataIndex: 'total_paid_amount',
      key: 'total_paid_amount',
      align: 'right',
      render: (amount) => (
        <span style={{ color: '#52c41a' }}>
          {formatCurrency(amount)}
        </span>
      )
    },
    {
      title: '欠款总额',
      dataIndex: 'total_overdue_amount',
      key: 'total_overdue_amount',
      align: 'right',
      render: (amount) => (
        <span style={{ color: amount > 0 ? '#f5222d' : '#52c41a' }}>
          {formatCurrency(amount)}
        </span>
      )
    },
    {
      title: '收缴率',
      dataIndex: 'payment_rate',
      key: 'payment_rate',
      align: 'center',
      render: (rate) => {
        const percentage = Number(rate);
        let color = '#f5222d';
        if (percentage >= 90) color = '#52c41a';
        else if (percentage >= 70) color = '#faad14';

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
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
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
      render: (count) => <Tag color="blue">{count} 个</Tag>
    },
    {
      title: '应收总额',
      dataIndex: 'total_due_amount',
      key: 'total_due_amount',
      align: 'right',
      render: (amount) => formatCurrency(amount)
    },
    {
      title: '已收总额',
      dataIndex: 'total_paid_amount',
      key: 'total_paid_amount',
      align: 'right',
      render: (amount) => (
        <span style={{ color: '#52c41a' }}>
          {formatCurrency(amount)}
        </span>
      )
    },
    {
      title: '欠款总额',
      dataIndex: 'total_overdue_amount',
      key: 'total_overdue_amount',
      align: 'right',
      render: (amount) => (
        <span style={{ color: amount > 0 ? '#f5222d' : '#52c41a' }}>
          {formatCurrency(amount)}
        </span>
      )
    },
    {
      title: '收缴率',
      dataIndex: 'payment_rate',
      key: 'payment_rate',
      align: 'center',
      render: (rate) => {
        const percentage = Number(rate);
        let color = '#f5222d';
        if (percentage >= 90) color = '#52c41a';
        else if (percentage >= 70) color = '#faad14';

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
  const ownershipChartData = (ownershipStats || []).map(item => ({
    type: item.ownership_name,
    value: Number(item.total_due_amount),
    paid: Number(item.total_paid_amount),
    overdue: Number(item.total_overdue_amount)
  }));

  const ownershipPieConfig = {
    data: ownershipChartData,
    angleField: 'value',
    colorField: 'type',
    color: COLORS,
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
      formatter: (datum: any) => ({
        name: datum.type,
        value: formatCurrency(datum.value),
      }),
    },
  }

  const monthlyChartData = (monthlyStats || []).map(item => ({
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
  ])

  const monthlyBarConfig = {
    data: monthlyBarData,
    xField: 'month',
    yField: 'value',
    seriesField: 'type',
    color: ({ type }: any) => {
      if (type === '应收金额') return '#1890ff'
      if (type === '已收金额') return '#52c41a'
      if (type === '欠款金额') return '#f5222d'
      return '#1890ff'
    },
    isGroup: true,
    columnStyle: {
      fillOpacity: 0.8,
    },
    legend: {
      position: 'top' as const,
    },
    tooltip: {
      formatter: (datum: any) => ({
        name: datum.type,
        value: formatCurrency(datum.value),
      }),
    },
    yAxis: {
      label: {
        formatter: (value: number) => formatCurrency(value),
      },
    },
  }

  const monthlyLineConfig = {
    data: monthlyChartData,
    xField: 'month',
    yField: 'rate',
    smooth: true,
    color: '#52c41a',
    lineStyle: {
      lineWidth: 2,
    },
    point: {
      size: 4,
      shape: 'circle',
    },
    tooltip: {
      formatter: (datum: any) => ({
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
  }

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
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
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
                  value={dateRange as any}
                  onChange={(dates) => setDateRange(dates as [moment.Moment, moment.Moment])}
                  style={{ width: 300 }}
                />
                <Select
                  value={selectedYear}
                  onChange={setSelectedYear}
                  style={{ width: 120 }}
                >
                  {Array.from({ length: 5 }, (_, i) => moment().year() - i).map(year => (
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
                  value={Number(overviewData.total_due_amount || 0)}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="元"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="已收总额"
                  value={Number(overviewData.total_paid_amount || 0)}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="元"
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="欠款总额"
                  value={Number(overviewData.total_overdue_amount || 0)}
                  precision={2}
                  prefix={<DollarOutlined />}
                  suffix="元"
                  valueStyle={{ color: Number(overviewData.total_overdue_amount || 0) > 0 ? '#f5222d' : '#52c41a' }}
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
                  valueStyle={{ color: Number(overviewData.payment_rate || 0) >= 90 ? '#52c41a' : '#faad14' }}
                />
              </Card>
            </Col>
          </Row>
        )}

        <Tabs defaultActiveKey="ownership" type="card" items={tabItems} />
      </Card>
    </div>
  );
};

export default RentStatisticsPage;
