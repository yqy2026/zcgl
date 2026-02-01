import React, { useMemo } from 'react';
import { Area } from '@ant-design/plots';

import ChartErrorBoundary from '../ChartErrorBoundary';
import { CHART_COLORS } from '@/styles/colorMap';

import ChartContainer from './ChartContainer';
import type { ChartDatum } from './chartTypes';

interface AreaChartProps {
  data: Array<Record<string, unknown>>;
  xDataKey: string;
  yDataKey: string;
  areaName?: string;
  fill?: string;
  stroke?: string;
  height?: number;
  showLegend?: boolean;
  loading?: boolean;
  isPercentage?: boolean;
  // Internal properties for compatibility
  _fill?: string;
  _stroke?: string;
}

const AnalyticsAreaChart: React.FC<AreaChartProps> = ({
  data,
  xDataKey,
  yDataKey,
  areaName = '数值',
  _fill,
  _stroke,
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
      smooth: true,
      areaStyle: {
        fillOpacity: 0.3,
      },
      line: {
        color: CHART_COLORS[0],
        style: {
          lineWidth: 2,
        },
      },
      color: CHART_COLORS[0],
      legend: showLegend
        ? {
            position: 'top' as const,
          }
        : false,
      tooltip: {
        formatter: (datum: ChartDatum) => {
          const val = datum[yDataKey] as number | undefined;
          return {
            name: areaName,
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
    [areaName, chartData, isPercentage, showLegend, xDataKey, yDataKey]
  );

  return (
    <ChartContainer loading={loading} height={height} hasData={chartData.length > 0}>
      <ChartErrorBoundary>
        <Area {...config} height={height} />
      </ChartErrorBoundary>
    </ChartContainer>
  );
};

export default React.memo(AnalyticsAreaChart);
