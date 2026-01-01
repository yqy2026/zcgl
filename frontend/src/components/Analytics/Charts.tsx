import React, { useMemo } from 'react'
import { Pie, Column, Line, Area } from '@ant-design/plots'
import ChartErrorBoundary from './ChartErrorBoundary'
import { Empty, Spin } from 'antd'

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#fa8c16', '#eb2f96', '#13c2c2', '#52c41a']

interface PieChartProps {
  data: Array<{ name: string; value: number; percentage?: number }>
  dataKey: string
  labelKey?: string
  outerRadius?: number
  height?: number
  showLegend?: boolean
  loading?: boolean
}

export const AnalyticsPieChart: React.FC<PieChartProps> = ({
  data,
  dataKey: _dataKey,  // Unused in current implementation
  labelKey: _labelKey = 'name',  // Unused in current implementation
  outerRadius = 80,
  height = 300,
  showLegend = true,
  loading = false
}) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []
    return data.filter(item => item.value > 0).map(item => ({
      type: item.name,
      value: item.value,
    }))
  }, [data])

  const config = {
    data: chartData,
    angleField: 'value',
    colorField: 'type',
    color: COLORS,
    radius: outerRadius / 100,
    label: {
      type: 'outer' as const,
      content: '{name} {percentage}',
    },
    legend: showLegend ? {
      layout: 'horizontal' as const,
      position: 'bottom' as const,
    } : false,
    tooltip: {
      formatter: (datum: any) => ({
        name: datum.type,
        value: datum.value.toLocaleString(),
      }),
    },
  }

  if (loading) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="暂无数据" />
      </div>
    )
  }

  return (
    <ChartErrorBoundary>
      <Pie {...config} height={height} />
    </ChartErrorBoundary>
  )
}

interface BarChartProps {
  data: Array<Record<string, unknown>>
  xDataKey: string
  yDataKey: string
  barName?: string
  fill?: string
  height?: number
  showLegend?: boolean
  loading?: boolean
  isPercentage?: boolean
}

export const AnalyticsBarChart: React.FC<BarChartProps> = ({
  data,
  xDataKey,
  yDataKey,
  barName = '数值',
  fill = '#1890ff',
  height = 300,
  showLegend = true,
  loading = false,
  isPercentage = false
}) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []
    return data
  }, [data])

  const config = {
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
      formatter: (datum: any) => isPercentage
        ? `${datum[yDataKey].toFixed(1)}%`
        : datum[yDataKey].toLocaleString(),
    },
    legend: showLegend ? {
      position: 'top' as const,
    } : false,
    tooltip: {
      formatter: (datum: any) => ({
        name: barName,
        value: isPercentage
          ? `${datum[yDataKey].toFixed(1)}%`
          : datum[yDataKey].toLocaleString(),
      }),
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
  }

  if (loading) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="暂无数据" />
      </div>
    )
  }

  return (
    <ChartErrorBoundary>
      <Column {...config} height={height} />
    </ChartErrorBoundary>
  )
}

interface LineChartProps {
  data: Array<Record<string, unknown>>
  xDataKey: string
  yDataKey: string
  lineName?: string
  stroke?: string
  strokeWidth?: number
  height?: number
  showLegend?: boolean
  loading?: boolean
  isPercentage?: boolean
  showDots?: boolean
}

export const AnalyticsLineChart: React.FC<LineChartProps> = ({
  data,
  xDataKey,
  yDataKey,
  lineName = '趋势',
  stroke = '#8884d8',
  strokeWidth = 2,
  height = 300,
  showLegend = true,
  loading = false,
  isPercentage = false,
  showDots = true
}) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []
    return data
  }, [data])

  if (loading) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="暂无数据" />
      </div>
    )
  }

  const config = {
    data: chartData,
    xField: xDataKey,
    yField: yDataKey,
    smooth: true,
    color: stroke,
    lineStyle: {
      lineWidth: strokeWidth,
    },
    point: showDots ? {
      size: 4,
    } : false,
    legend: showLegend ? {
      position: 'top' as const,
    } : false,
    tooltip: {
      formatter: (datum: any) => ({
        name: lineName,
        value: isPercentage
          ? `${datum[yDataKey].toFixed(1)}%`
          : datum[yDataKey].toLocaleString(),
      }),
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
  }

  if (loading) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="暂无数据" />
      </div>
    )
  }

  return (
    <ChartErrorBoundary>
      <Line {...config} height={height} />
    </ChartErrorBoundary>
  )
}

interface MultiBarChartProps {
  data: Array<Record<string, unknown>>
  xDataKey: string
  bars: Array<{
    dataKey: string
    name: string
    fill: string
  }>
  height?: number
  showLegend?: boolean
  loading?: boolean
}

export const AnalyticsMultiBarChart: React.FC<MultiBarChartProps> = ({
  data,
  xDataKey,
  bars,
  height = 300,
  showLegend = true,
  loading = false
}) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []
    return data
  }, [data])

  // Transform data for multi-series column chart
  const multiBarData = useMemo(() => {
    if (!chartData || chartData.length === 0) return []
    return chartData.flatMap(item =>
      bars.map(bar => ({
        [xDataKey]: item[xDataKey],
        type: bar.name,
        value: item[bar.dataKey],
      }))
    )
  }, [chartData, bars, xDataKey])

  if (loading) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="暂无数据" />
      </div>
    )
  }

  const config = {
    data: multiBarData,
    xField: xDataKey,
    yField: 'value',
    seriesField: 'type',
    color: ({ type }: any) => {
      const bar = bars.find(b => b.name === type)
      return bar?.fill || '#1890ff'
    },
    isGroup: true,
    columnStyle: {
      fillOpacity: 0.8,
      radius: [4, 4, 0, 0],
    },
    legend: showLegend ? {
      position: 'top' as const,
    } : false,
    tooltip: {
      formatter: (datum: any) => ({
        name: datum.type,
        value: datum.value?.toLocaleString(),
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
  }

  if (loading) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="暂无数据" />
      </div>
    )
  }

  return (
    <ChartErrorBoundary>
      <Column {...config} height={height} />
    </ChartErrorBoundary>
  )
}

interface AreaChartProps {
  data: Array<Record<string, unknown>>
  xDataKey: string
  yDataKey: string
  areaName?: string
  fill?: string
  stroke?: string
  height?: number
  showLegend?: boolean
  loading?: boolean
  isPercentage?: boolean
}

export const AnalyticsAreaChart: React.FC<AreaChartProps> = ({
  data,
  xDataKey,
  areaName = '数值',
  height = 300,
  showLegend = true,
  loading = false,
  isPercentage = false
}) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []
    return data
  }, [data])

  if (loading) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="暂无数据" />
      </div>
    )
  }

  const config = {
    data: chartData,
    xField: xDataKey,
    yField: yDataKey,
    smooth: true,
    areaStyle: {
      fillOpacity: 0.3,
    },
    line: {
      color: stroke || '#1890ff',
      style: {
        lineWidth: 2,
      },
    },
    color: stroke || '#1890ff',
    legend: showLegend ? {
      position: 'top' as const,
    } : false,
    tooltip: {
      formatter: (datum: any) => ({
        name: areaName,
        value: isPercentage
          ? `${datum[yDataKey].toFixed(1)}%`
          : datum[yDataKey].toLocaleString(),
      }),
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
  }

  return (
    <ChartErrorBoundary>
      <Area {...config} height={height} />
    </ChartErrorBoundary>
  )
}