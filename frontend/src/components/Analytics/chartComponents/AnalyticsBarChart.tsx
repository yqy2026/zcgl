import React, { useMemo } from 'react';
import { Column } from '@ant-design/plots';

import ChartErrorBoundary from '../ChartErrorBoundary';
import { CHART_COLORS } from '@/styles/colorMap';

import ChartContainer from './ChartContainer';
import type { ChartDatum } from './chartTypes';

interface BarChartProps {
  data: Array<Record<string, unknown>>;
  xDataKey: string;
  yDataKey: string;
  barName?: string;
  fill?: string;
  height?: number;
  showLegend?: boolean;
  loading?: boolean;
  isPercentage?: boolean;
}

const AnalyticsBarChart: React.FC<BarChartProps> = ({
  data,
  xDataKey,
  yDataKey,
  barName = '数值',
  fill = CHART_COLORS[0],
  height = 300,
  showLegend = true,
  loading = false,
  isPercentage = false,
}) => {
  const chartData = useMemo(() => {
    if (data == null || data.length === 0) return [];
    return data;
  }, [data]);

  const config = useMemo(
    () => ({
      data: chartData,
      xField: xDataKey,
      yField: yDataKey,
      color: fill,
      columnStyle: {
        fillOpacity: 0.8,
        radius: [4, 4, 0, 0],
      },
      label: {
        position: 'top' as const,
        formatter: (datum: ChartDatum) => {
          const val = datum[yDataKey] as number | undefined;
          return isPercentage ? `${val?.toFixed(1) ?? '0'}%` : (val?.toLocaleString() ?? '0');
        },
      },
      legend: showLegend
        ? {
            position: 'top' as const,
          }
        : false,
      tooltip: {
        formatter: (datum: ChartDatum) => {
          const val = datum[yDataKey] as number | undefined;
          return {
            name: barName,
            value: isPercentage ? `${val?.toFixed(1) ?? '0'}%` : (val?.toLocaleString() ?? '0'),
          };
        },
      },
      yAxis: {
        min: 0,
        label: {
          formatter: isPercentage ? (value: number) => `${value}%` : undefined,
        },
      },
      xAxis: {
        label: {
          autoRotate: true,
          rotate: -45,
          offset: 30,
        },
      },
    }),
    [barName, chartData, fill, isPercentage, showLegend, xDataKey, yDataKey]
  );

  return (
    <ChartContainer loading={loading} height={height} hasData={chartData.length > 0}>
      <ChartErrorBoundary>
        <Column {...config} height={height} />
      </ChartErrorBoundary>
    </ChartContainer>
  );
};

export default React.memo(AnalyticsBarChart);
