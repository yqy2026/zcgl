import React, { useMemo } from 'react';
import { Line } from '@ant-design/plots';

import ChartErrorBoundary from '../ChartErrorBoundary';
import { CHART_COLORS } from '@/styles/colorMap';

import ChartContainer from './ChartContainer';
import type { ChartDatum } from './chartTypes';

interface LineChartProps {
  data: Array<Record<string, unknown>>;
  xDataKey: string;
  yDataKey: string;
  lineName?: string;
  stroke?: string;
  strokeWidth?: number;
  height?: number;
  showLegend?: boolean;
  loading?: boolean;
  isPercentage?: boolean;
  showDots?: boolean;
}

const AnalyticsLineChart: React.FC<LineChartProps> = ({
  data,
  xDataKey,
  yDataKey,
  lineName = '趋势',
  stroke = CHART_COLORS[4],
  strokeWidth = 2,
  height = 300,
  showLegend = true,
  loading = false,
  isPercentage = false,
  showDots = true,
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
      smooth: true,
      color: stroke,
      lineStyle: {
        lineWidth: strokeWidth,
      },
      point: showDots
        ? {
            size: 4,
          }
        : false,
      legend: showLegend
        ? {
            position: 'top' as const,
          }
        : false,
      tooltip: {
        formatter: (datum: ChartDatum) => {
          const val = datum[yDataKey] as number | undefined;
          return {
            name: lineName,
            value: isPercentage ? `${val?.toFixed(1) ?? '0'}%` : (val?.toLocaleString() ?? '0'),
          };
        },
      },
      yAxis: {
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
    [
      chartData,
      isPercentage,
      lineName,
      showDots,
      showLegend,
      stroke,
      strokeWidth,
      xDataKey,
      yDataKey,
    ]
  );

  return (
    <ChartContainer loading={loading} height={height} hasData={chartData.length > 0}>
      <ChartErrorBoundary>
        <Line {...config} height={height} />
      </ChartErrorBoundary>
    </ChartContainer>
  );
};

export default React.memo(AnalyticsLineChart);
