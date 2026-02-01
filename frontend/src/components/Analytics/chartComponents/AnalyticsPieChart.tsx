import React, { useMemo } from 'react';
import { Pie } from '@ant-design/plots';

import ChartErrorBoundary from '../ChartErrorBoundary';
import { CHART_COLORS } from '@/styles/colorMap';

import ChartContainer from './ChartContainer';
import type { ChartDatum } from './chartTypes';

interface PieChartProps {
  data: Array<{ name: string; value: number; percentage?: number }>;
  dataKey: string;
  labelKey?: string;
  outerRadius?: number;
  height?: number;
  showLegend?: boolean;
  loading?: boolean;
}

const AnalyticsPieChart: React.FC<PieChartProps> = ({
  data,
  dataKey: _dataKey, // Unused in current implementation
  labelKey: _labelKey = 'name', // Unused in current implementation
  outerRadius = 80,
  height = 300,
  showLegend = true,
  loading = false,
}) => {
  const chartData = useMemo(() => {
    if (data == null || data.length === 0) return [];
    return data
      .filter(item => item.value > 0)
      .map(item => ({
        type: item.name,
        value: item.value,
      }));
  }, [data]);

  const config = useMemo(
    () => ({
      data: chartData,
      angleField: 'value',
      colorField: 'type',
      color: CHART_COLORS,
      radius: outerRadius / 100,
      label: {
        type: 'outer' as const,
        content: '{name} {percentage}',
      },
      legend: showLegend
        ? {
            layout: 'horizontal' as const,
            position: 'bottom' as const,
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
    }),
    [chartData, outerRadius, showLegend]
  );

  return (
    <ChartContainer loading={loading} height={height} hasData={chartData.length > 0}>
      <ChartErrorBoundary>
        <Pie {...config} height={height} />
      </ChartErrorBoundary>
    </ChartContainer>
  );
};

export default React.memo(AnalyticsPieChart);
