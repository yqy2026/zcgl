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
  message,
  Tooltip
} from 'antd';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line
} from 'recharts';
import {
  DollarOutlined,
  FileTextOutlined,
  AccountBookOutlined,
  RiseOutlined,
  DownloadOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import moment from 'moment';
import 'moment/locale/zh-cn';
import type { ColumnsType } from 'antd/es/table';

import {
  rentContractService,
  OwnershipRentStatistics,
  AssetRentStatistics,
  MonthlyRentStatistics
} from '@/services/rentContractService';
import { formatCurrency } from '@/utils/format';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { TabPane } = Tabs;
const { Title } = Typography;

moment.locale('zh-cn');

// 颜色配置
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

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
    } catch (error) {
      message.error('获取统计数据失败');
      console.error('Statistics fetch error:', error);
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
    } catch (error) {
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
  const ownershipChartData = ownershipStats.map(item => ({
    name: item.ownership_name,
    value: Number(item.total_due_amount),
    paid: Number(item.total_paid_amount),
    overdue: Number(item.total_overdue_amount)
  }));

  const monthlyChartData = monthlyStats.map(item => ({
    month: item.year_month,
    due: Number(item.total_due_amount),
    paid: Number(item.total_paid_amount),
    overdue: Number(item.total_overdue_amount),
    rate: Number(item.payment_rate)
  }));

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
                  value={dateRange}
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

        <Tabs defaultActiveKey="ownership" type="card">
          <TabPane tab="权属方统计" key="ownership">
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                <Card title="权属方租金分布" loading={loading}>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={ownershipChartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {ownershipChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <RechartsTooltip formatter={(value) => formatCurrency(Number(value))} />
                    </PieChart>
                  </ResponsiveContainer>
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
          </TabPane>

          <TabPane tab="资产统计" key="asset">
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
          </TabPane>

          <TabPane tab="月度趋势" key="monthly">
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={16}>
                <Card title="月度租金趋势" loading={loading}>
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={monthlyChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis />
                      <RechartsTooltip formatter={(value) => formatCurrency(Number(value))} />
                      <Legend />
                      <Bar dataKey="due" name="应收金额" fill="#1890ff" />
                      <Bar dataKey="paid" name="已收金额" fill="#52c41a" />
                      <Bar dataKey="overdue" name="欠款金额" fill="#f5222d" />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
              <Col xs={24} lg={8}>
                <Card title="收缴率趋势" loading={loading}>
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={monthlyChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis domain={[0, 100]} />
                      <RechartsTooltip formatter={(value) => `${value}%`} />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="rate"
                        name="收缴率"
                        stroke="#52c41a"
                        strokeWidth={2}
                        dot={{ fill: '#52c41a' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
            </Row>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default RentStatisticsPage;