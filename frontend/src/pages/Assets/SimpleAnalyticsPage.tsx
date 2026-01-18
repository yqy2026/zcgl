/**
 * 简化版的资产分析页面 - 用于调试
 */
import React from 'react';
import { Card, Empty, Typography } from 'antd';
import { AnalyticsStatsGrid } from '@/components/Analytics/AnalyticsStatsCard';

const { Title } = Typography;

const SimpleAnalyticsPage: React.FC = () => {
  // 使用模拟数据进行测试
  const mockData = {
    total_assets: 100,
    total_area: 50000,
    total_rentable_area: 48000,
    occupancy_rate: 95,
    total_annual_income: 1000000,
    total_net_income: 800000,
    total_monthly_rent: 80000,
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>资产分析（简化版）</Title>

      <Card title="概览统计" style={{ marginBottom: '24px' }}>
        <AnalyticsStatsGrid data={mockData} loading={false} />
      </Card>

      <Card>
        <Empty description="这是简化版页面，仅用于测试" />
      </Card>
    </div>
  );
};

export default SimpleAnalyticsPage;
