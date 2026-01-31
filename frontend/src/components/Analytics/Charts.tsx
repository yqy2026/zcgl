import React, { useMemo } from 'react';
import { Pie, Column, Line, Area } from '@ant-design/plots';
import ChartErrorBoundary from './ChartErrorBoundary';
import { Empty, Spin } from 'antd';
import { CHART_COLORS } from '@/styles/colorMap';

// Type for chart tooltip/formatter datum with dynamic field access
interface ChartDatum {
  type?: string;
  value?: number;
  [key: string]: unknown;
}

interface PieChartProps {
  data: Array<{ name: string; value: number; percentage?: number }>;
  dataKey: string;
  labelKey?: string;
  outerRadius?: number;
  height?: number;
  showLegend?: boolean;
  loading?: boolean;
}

export const AnalyticsPieChart = React.memo(function AnalyticsPieChart({
  data,
  dataKey: _dataKey, // Unused in current implementation
  labelKey: _labelKey = 'name', // Unused in current implementation
  outerRadius = 80,
  height = 300,
  showLegend = true,
  loading = false,
}: PieChartProps) {
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

  if (loading !== undefined && loading !== null) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (chartData == null || chartData.length === 0) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Empty description="暂无数据" />
      </div>
    );
  }

  return (
    <ChartErrorBoundary>
      <Pie {...config} height={height} />
    </ChartErrorBoundary>
  );
});

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

export const AnalyticsBarChart = React.memo(function AnalyticsBarChart({
  data,
  xDataKey,
  yDataKey,
  barName = '数值',
  fill = CHART_COLORS[0],
  height = 300,
  showLegend = true,
  loading = false,
  isPercentage = false,
}: BarChartProps) {
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

  if (loading !== undefined && loading !== null) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (chartData == null || chartData.length === 0) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Empty description="暂无数据" />
      </div>
    );
  }

  return (
    <ChartErrorBoundary>
      <Column {...config} height={height} />
    </ChartErrorBoundary>
  );
});

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

export const AnalyticsLineChart = React.memo(function AnalyticsLineChart({
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
}: LineChartProps) {
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
  if (loading !== undefined && loading !== null) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (chartData == null || chartData.length === 0) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Empty description="暂无数据" />
      </div>
    );
  }

  return (
    <ChartErrorBoundary>
      <Line {...config} height={height} />
    </ChartErrorBoundary>
  );
});

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

export const AnalyticsMultiBarChart = React.memo(function AnalyticsMultiBarChart({
  data,
  xDataKey,
  bars,
  height = 300,
  showLegend = true,
  loading = false,
}: MultiBarChartProps) {
  const chartData = useMemo(() => {
    if (data == null || data.length === 0) return [];
    return data;
  }, [data]);

  // Transform data for multi-series column chart
  const multiBarData = useMemo(() => {
    if (chartData === undefined || chartData === null || chartData.length === 0) return [];
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
  if (loading !== undefined && loading !== null) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (chartData == null || chartData.length === 0) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Empty description="暂无数据" />
      </div>
    );
  }

  return (
    <ChartErrorBoundary>
      <Column {...config} height={height} />
    </ChartErrorBoundary>
  );
});

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

export const AnalyticsAreaChart = React.memo(function AnalyticsAreaChart({
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
}: AreaChartProps) {
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
  if (loading !== undefined && loading !== null) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (chartData == null || chartData.length === 0) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Empty description="暂无数据" />
      </div>
    );
  }

  return (
    <ChartErrorBoundary>
      <Area {...config} height={height} />
    </ChartErrorBoundary>
  );
});
