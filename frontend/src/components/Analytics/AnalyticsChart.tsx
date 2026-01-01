import React from 'react'
import { Pie, Column, Line } from '@ant-design/plots'
import { Card, Empty, Spin } from 'antd'

// 图表颜色主题 - 使用 Ant Design 颜色
const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#fa8c16', '#eb2f96']

// 基础图表组件属性
interface BaseChartProps {
  title: string
  loading?: boolean
  height?: number
  className?: string
}

// 饼图数据接口
interface PieData {
  type: string
  value: number
  count?: number
  percentage?: number
}

// 柱状图数据接口
interface BarData {
  name: string
  value: number
  [key: string]: unknown
}

// 折线图数据接口
interface LineData {
  date: string
  [key: string]: unknown
}

// 饼图组件
interface PieChartProps extends BaseChartProps {
  data: PieData[]
  showLegend?: boolean
  showTooltip?: boolean
  innerRadius?: number
  outerRadius?: number
}

export const AnalyticsPieChart: React.FC<PieChartProps> = ({
  title,
  data,
  loading = false,
  height = 300,
  showLegend = true,
  showTooltip = true,
  innerRadius = 0,
  outerRadius = 80,
  className
}) => {
  // Transform data from {name, value} to {type, value} for @ant-design/plots
  const chartData = data.map(item => ({
    type: (item as any).name || item.type,
    value: item.value,
  }))

  const config = {
    data: chartData,
    angleField: 'value',
    colorField: 'type',
    color: COLORS,
    radius: outerRadius / 100,
    innerRadius: innerRadius / 100,
    label: {
      type: (innerRadius > 0 ? 'inner' : 'outer') as const,
      offset: innerRadius > 0 ? '-50%' : undefined,
      content: innerRadius > 0 ? '{percentage}%' : '{name} {percentage}',
      style: {
        fontSize: 12,
        fill: '#fff',
      },
    },
    legend: showLegend ? {
      layout: 'horizontal' as const,
      position: 'bottom' as const,
    } : false,
    tooltip: showTooltip ? {
      formatter: (datum: any) => ({
        name: datum.type,
        value: formatAreaValue(datum.value),
      }),
    } : false,
  }

  if (loading) {
    return (
      <Card title={title} className={className}>
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card title={title} className={className}>
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Empty description="暂无数据" />
        </div>
      </Card>
    )
  }

  return (
    <Card title={title} className={className}>
      <Pie {...config} height={height} />
    </Card>
  )
}

// 柱状图组件
interface BarChartProps extends BaseChartProps {
  data: BarData[]
  xAxisKey: string
  barKey: string
  barSize?: number
  showLegend?: boolean
  showTooltip?: boolean
  showGrid?: boolean
  color?: string
}

export const AnalyticsBarChart: React.FC<BarChartProps> = ({
  title,
  data,
  xAxisKey,
  barKey,
  loading = false,
  height = 300,
  barSize = 30,
  showLegend = false,
  showTooltip = true,
  showGrid = true,
  color = '#1890ff',
  className
}) => {
  const config = {
    data: data,
    xField: xAxisKey,
    yField: barKey,
    color: color,
    columnStyle: {
      fillOpacity: 0.8,
      radius: [4, 4, 0, 0],
    },
    label: {
      position: 'top' as const,
      formatter: (datum: any) => formatAggressive(datum[barKey]),
      style: {
        fill: '#666',
        fontSize: 12,
      },
    },
    legend: showLegend ? {
      position: 'top' as const,
    } : false,
    tooltip: showTooltip ? {
      formatter: (datum: any) => ({
        name: datum[xAxisKey],
        value: formatAreaValue(datum[barKey]),
      }),
    } : false,
    yAxis: {
      min: 0,
      label: {
        formatter: (value: number) => formatAggressive(value),
      },
    },
    xAxis: {
      label: {
        autoRotate: true,
        autoHide: true,
        rotate: -45,
        offset: 30,
        style: {
          fontSize: 12,
        },
      },
    },
  }

  if (loading) {
    return (
      <Card title={title} className={className}>
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card title={title} className={className}>
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Empty description="暂无数据" />
        </div>
      </Card>
    )
  }

  return (
    <Card title={title} className={className}>
      <Column {...config} height={height} />
    </Card>
  )
}

// 折线图组件
interface LineChartProps extends BaseChartProps {
  data: LineData[]
  lines: Array<{
    key: string
    name: string
    color: string
    strokeWidth?: number
  }>
  xAxisKey: string
  showGrid?: boolean
  showLegend?: boolean
  showTooltip?: boolean
  showDots?: boolean
}

export const AnalyticsLineChart: React.FC<LineChartProps> = ({
  title,
  data,
  lines,
  xAxisKey,
  loading = false,
  height = 300,
  showGrid = true,
  showLegend = true,
  showTooltip = true,
  showDots = true,
  className
}) => {
  // Transform data for multi-line chart
  const chartData = data.flatMap(item =>
    lines.map(line => ({
      [xAxisKey]: item[xAxisKey],
      type: line.name,
      value: item[line.key],
    }))
  )

  const config = {
    data: chartData,
    xField: xAxisKey,
    yField: 'value',
    seriesField: 'type',
    color: ({ type }: any) => {
      const line = lines.find(l => l.name === type)
      return line?.color || '#1890ff'
    },
    smooth: true,
    lineStyle: {
      lineWidth: lines[0]?.strokeWidth || 2,
    },
    point: showDots ? {
      size: 4,
    } : false,
    legend: showLegend ? {
      position: 'top' as const,
    } : false,
    tooltip: showTooltip ? {
      formatter: (datum: any) => ({
        name: datum.type,
        value: datum.value,
      }),
    } : false,
  }

  if (loading) {
    return (
      <Card title={title} className={className}>
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card title={title} className={className}>
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Empty description="暂无数据" />
        </div>
      </Card>
    )
  }

  return (
    <Card title={title} className={className}>
      <Line {...config} height={height} />
    </Card>
  )
}

// 统一的数值格式化函数
const formatAreaValue = (value: number): string => {
  const num = Number(value);
  if (isNaN(num)) return '0㎡';

  if (num >= 10000) {
    return `${(num / 10000).toFixed(2)}万㎡`;
  } else if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}千㎡`;
  } else {
    // 对于小于1000的数值，移除不必要的.00
    const formatted = num.toFixed(2);
    return formatted.endsWith('.00') ? `${Math.round(num)}㎡` : `${formatted}㎡`;
  }
};

// 更激进的数值格式化函数，用于去除所有可能的尾随零
const formatAggressive = (value: number): string => {
  const num = Number(value);
  if (isNaN(num)) return '0';

  if (num >= 10000) {
    const result = (num / 10000).toFixed(2);
    return result.endsWith('.00') ? `${(num / 10000).toFixed(0)}万` : result + '万';
  } else if (num >= 1000) {
    const result = (num / 1000).toFixed(1);
    return result.endsWith('.0') ? `${(num / 1000).toFixed(0)}千` : result + '千';
  } else {
    return num.toFixed(0);
  }
};

// 数据转换工具函数
export const chartDataUtils = {
  // 转换饼图数据
  toPieData: (data: Array<{ name: string; count: number; percentage?: number }>): PieData[] => {
    return data.map(item => ({
      type: item.name,  // Changed from 'name' to 'type' for @ant-design/plots
      value: item.count,
      count: item.count,
      percentage: item.percentage
    }))
  },

  // 转换业态类别数据
  toBusinessCategoryData: (data: Array<{ category: string; count: number; occupancy_rate?: number }>): BarData[] => {
    return data.map(item => ({
      name: item.category,
      value: item.count,
      count: item.count,
      occupancy_rate: item.occupancy_rate || 0
    }))
  },

  // 转换出租率分布数据
  toOccupancyData: (data: Array<{ range: string; count: number; percentage?: number }>): BarData[] => {
    return data.map(item => ({
      name: item.range,
      value: item.count,
      count: item.count,
      percentage: item.percentage
    }))
  },

  // 转换趋势数据
  toTrendData: (data: Array<{ date: string; occupancy_rate: number; total_rented_area?: number; total_rentable_area?: number }>): LineData[] => {
    return data.map(item => ({
      date: item.date,
      occupancy_rate: item.occupancy_rate,
      total_rented_area: item.total_rented_area || 0,
      total_rentable_area: item.total_rentable_area || 0
    }))
  },

  // 转换面积维度数据
  toAreaData: (data: Array<{ name: string; total_area: number; area_percentage: number; average_area?: number }>): PieData[] => {
    return data.map(item => ({
      type: item.name,  // Changed from 'name' to 'type' for @ant-design/plots
      value: Math.round(item.total_area * 100) / 100,
      total_area: Math.round(item.total_area * 100) / 100,
      percentage: item.area_percentage,
      average_area: item.average_area || 0
    }))
  },

  // 转换面积维度柱状图数据
  toAreaBarData: (data: Array<{ name: string; total_area: number; count?: number; average_area?: number }>): BarData[] => {
    return data.map(item => ({
      name: item.name,
      value: Math.round(item.total_area * 100) / 100,
      total_area: Math.round(item.total_area * 100) / 100,
      count: item.count || 0,
      average_area: item.average_area || 0
    }))
  },

  // 转换业态类别面积数据
  toBusinessCategoryAreaData: (data: Array<{ category: string; total_area: number; area_percentage: number; occupancy_rate?: number }>): BarData[] => {
    return data.map(item => ({
      name: item.category,
      value: Math.round(item.total_area * 100) / 100,
      total_area: Math.round(item.total_area * 100) / 100,
      area_percentage: item.area_percentage,
      occupancy_rate: item.occupancy_rate || 0
    }))
  }
}