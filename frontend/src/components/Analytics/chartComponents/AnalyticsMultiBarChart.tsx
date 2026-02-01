import React, { useMemo } from 'react';
import { Column } from '@ant-design/plots';

import ChartErrorBoundary from '../ChartErrorBoundary';
import { CHART_COLORS } from '@/styles/colorMap';

import ChartContainer from './ChartContainer';
import type { ChartDatum } from './chartTypes';

interface MultiBarChartProps {
  data: Array<Record<string, unknown>>;
  xDataKey: string;
  bars: Array<{
    dataKey: string;
    name: string;
    fill: string;
  }>;
  height?: number;
  showLegend?: boolean;
  loading?: boolean;
}

const AnalyticsMultiBarChart: React.FC<MultiBarChartProps> = ({
  data,
  xDataKey,
  bars,
  height = 300,
  showLegend = true,
  loading = false,
}) => {
  const chartData = useMemo(() => {
    if (data == null || data.length === 0) return [];
    return data;
  }, [data]);

  // Transform data for multi-series column chart
  const multiBarData = useMemo(() => {
    if (chartData.length === 0) return [];
    return chartData.flatMap(item =>
      bars.map(bar => ({
        [xDataKey]: item[xDataKey],
        type: bar.name,
        value: item[bar.dataKey],
      }))
    );
  }, [chartData, bars, xDataKey]);

  const config = useMemo(
    () => ({
      data: multiBarData,
      xField: xDataKey,
      yField: 'value',
      seriesField: 'type',
      color: ({ type }: ChartDatum) => {
        const bar = bars.find(b => b.name === type);
        return bar !== undefined && bar !== null ? bar.fill : CHART_COLORS[0];
      },
      isGroup: true,
      columnStyle: {
        fillOpacity: 0.8,
        radius: [4, 4, 0, 0],
      },
      legend: showLegend
        ? {
            position: 'top' as const,
          }
        : false,
      tooltip: {
        formatter: (datum: ChartDatum) => ({
          name: datum.type ?? '',
          value:
            typeof datum.value === 'number'
              ? datum.value.toLocaleString()
              : String(datum.value ?? ''),
        }),
      },
      yAxis: {
        min: 0,
      },
      xAxis: {
        label: {
          autoRotate: true,
          rotate: -45,
          offset: 30,
        },
      },
    }),
    [bars, multiBarData, showLegend, xDataKey]
  );

  return (
    <ChartContainer loading={loading} height={height} hasData={chartData.length > 0}>
      <ChartErrorBoundary>
        <Column {...config} height={height} />
      </ChartErrorBoundary>
    </ChartContainer>
  );
};

export default React.memo(AnalyticsMultiBarChart);
