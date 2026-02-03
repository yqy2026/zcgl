import React from 'react';
import { Card, Statistic } from 'antd';

interface StatisticCardProps {
  title: string;
  value: number;
  precision?: number;
  suffix?: string;
  prefix?: string;
  valueStyle?: React.CSSProperties;
  styles?: { content?: React.CSSProperties };
  loading?: boolean;
}

export const StatisticCard: React.FC<StatisticCardProps> = ({
  title,
  value,
  precision = 0,
  suffix = '',
  prefix = '',
  valueStyle,
  styles,
  loading = false,
}) => {
  const contentStyle = styles?.content ?? valueStyle;

  return (
    <Card loading={loading}>
      <Statistic
        title={title}
        value={value}
        precision={precision}
        suffix={suffix}
        prefix={prefix}
        styles={contentStyle ? { ...styles, content: contentStyle } : styles}
      />
    </Card>
  );
};

interface FinancialStatisticCardProps extends Omit<StatisticCardProps, 'valueStyle'> {
  isPositive?: boolean;
}

export const FinancialStatisticCard: React.FC<FinancialStatisticCardProps> = ({
  title,
  value,
  isPositive = true,
  ...props
}) => {
  const contentStyle = {
    color: value >= 0 ? (isPositive ? '#3f8600' : '#cf1322') : '#cf1322',
  };

  return <StatisticCard title={title} value={value} styles={{ content: contentStyle }} {...props} />;
};
