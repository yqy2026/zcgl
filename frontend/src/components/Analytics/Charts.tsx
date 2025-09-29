import React, { useMemo } from 'react'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import ChartErrorBoundary from './ChartErrorBoundary'
import { Empty, Spin } from 'antd'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']

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
  dataKey,
  labelKey = 'name',
  outerRadius = 80,
  height = 300,
  showLegend = true,
  loading = false
}) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []
    return data.filter(item => item.value > 0)
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

  return (
    <ChartErrorBoundary>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ [labelKey]: name, percentage }) =>
              `${name} ${percentage ? percentage.toFixed(1) + '%' : ''}`
            }
            outerRadius={outerRadius}
            fill="#8884d8"
            dataKey={dataKey}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          {showLegend && <Legend />}
          <Tooltip
            formatter={(value: number, name: string, props: any) => [
              `${value.toLocaleString()}`,
              props.payload[labelKey] || name
            ]}
          />
        </PieChart>
      </ResponsiveContainer>
    </ChartErrorBoundary>
  )
}

interface BarChartProps {
  data: Array<Record<string, any>>
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
  fill = '#8884d8',
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

  return (
    <ChartErrorBoundary>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey={xDataKey}
            angle={-45}
            textAnchor="end"
            height={60}
            interval={0}
          />
          <YAxis
            tickFormatter={isPercentage ? (value) => `${value}%` : undefined}
          />
          <Tooltip
            formatter={(value: number) => [
              isPercentage ? `${value.toFixed(1)}%` : value.toLocaleString(),
              barName
            ]}
          />
          {showLegend && <Legend />}
          <Bar
            dataKey={yDataKey}
            fill={fill}
            name={barName}
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartErrorBoundary>
  )
}

interface LineChartProps {
  data: Array<Record<string, any>>
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

  return (
    <ChartErrorBoundary>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey={xDataKey}
            angle={-45}
            textAnchor="end"
            height={60}
            interval={0}
          />
          <YAxis
            tickFormatter={isPercentage ? (value) => `${value}%` : undefined}
          />
          <Tooltip
            formatter={(value: number) => [
              isPercentage ? `${value.toFixed(1)}%` : value.toLocaleString(),
              lineName
            ]}
          />
          {showLegend && <Legend />}
          <Line
            type="monotone"
            dataKey={yDataKey}
            stroke={stroke}
            name={lineName}
            strokeWidth={strokeWidth}
            dot={showDots ? { r: 4 } : false}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartErrorBoundary>
  )
}

interface MultiBarChartProps {
  data: Array<Record<string, any>>
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
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey={xDataKey}
            angle={-45}
            textAnchor="end"
            height={60}
            interval={0}
          />
          <YAxis />
          <Tooltip />
          {showLegend && <Legend />}
          {bars.map((bar, index) => (
            <Bar
              key={bar.dataKey}
              dataKey={bar.dataKey}
              fill={bar.fill}
              name={bar.name}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartErrorBoundary>
  )
}

interface AreaChartProps {
  data: Array<Record<string, any>>
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
  yDataKey,
  areaName = '数值',
  fill = '#8884d8',
  stroke = '#8884d8',
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

  return (
    <ChartErrorBoundary>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey={xDataKey}
            angle={-45}
            textAnchor="end"
            height={60}
            interval={0}
          />
          <YAxis
            tickFormatter={isPercentage ? (value) => `${value}%` : undefined}
          />
          <Tooltip
            formatter={(value: number) => [
              isPercentage ? `${value.toFixed(1)}%` : value.toLocaleString(),
              areaName
            ]}
          />
          {showLegend && <Legend />}
        </LineChart>
      </ResponsiveContainer>
    </ChartErrorBoundary>
  )
}