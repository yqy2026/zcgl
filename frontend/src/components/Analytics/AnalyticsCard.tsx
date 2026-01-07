import React from 'react';
import { Card, Empty } from 'antd';

interface AnalyticsCardProps {
  title: string;
  children: React.ReactNode;
  loading?: boolean;
  hasData?: boolean;
  size?: 'default' | 'small';
  className?: string;
}

export const AnalyticsCard: React.FC<AnalyticsCardProps> = ({
  title,
  children,
  loading = false,
  hasData = true,
  size = 'small',
  className = '',
}) => {
  return (
    <Card title={title} size={size} className={className} loading={loading}>
      {!hasData ? <Empty description="暂无数据" /> : children}
    </Card>
  );
};

// Note: ChartCard is simplified since @ant-design/plots has built-in responsive support
// Just use AnalyticsCard directly with chart components that have height prop
export { AnalyticsCard as ChartCard };
