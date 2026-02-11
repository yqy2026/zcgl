/**
 * 简化版的资产分析页面 - 用于调试
 */
import React from 'react';
import { Card, Empty } from 'antd';
import { AnalyticsStatsGrid } from '@/components/Analytics/AnalyticsStatsCard';
import PageContainer from '@/components/Common/PageContainer';
import styles from './SimpleAnalyticsPage.module.css';

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
    <PageContainer title="资产分析（简化版）" subTitle="用于调试资产分析模块的基础展示">
      <Card title="概览统计" className={styles.overviewCard}>
        <AnalyticsStatsGrid data={mockData} loading={false} />
      </Card>

      <Card>
        <Empty description="这是简化版页面，仅用于测试" />
      </Card>
    </PageContainer>
  );
};

export default SimpleAnalyticsPage;
