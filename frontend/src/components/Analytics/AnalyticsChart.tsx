import React from 'react'
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
import { Card, Empty, Spin } from 'antd'

// 图表颜色主题
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#ff7300']

// 基础图表组件属性
interface BaseChartProps {
  title: string
  loading?: boolean
  height?: number
  className?: string
}

// 饼图数据接口
interface PieData {
  name: string
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
  const renderCustomizedLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent
  }: {
    cx: number
    cy: number
    midAngle: number
    innerRadius: number
    outerRadius: number
    percent: number
  }) => {
    if (percent < 0.05) return null // 小于5%不显示标签

    const RADIAN = Math.PI / 180
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontSize={12}
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    )
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
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={2}
            dataKey="value"
            label={renderCustomizedLabel}
            labelLine={false}
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          {showTooltip && <Tooltip formatter={(value: number, name: string) => [formatAreaValue(value), name]} />}
          {showLegend && <Legend />}
        </PieChart>
      </ResponsiveContainer>
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
  color = '#0088FE',
  className
}) => {
  // 添加调试信息
  // Debug information for chart rendering

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
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis
            dataKey={xAxisKey}
            tick={{ fontSize: 12 }}
            interval={0}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(value: number) => {
              // Y轴数值格式化 - 使用激进的格式化逻辑但不显示单位
              return formatAggressive(value);
            }}
          />
          {showTooltip && <Tooltip formatter={(value: number, name: string) => [formatAreaValue(value), name]} />}
          {showLegend && <Legend />}
          <Bar
            dataKey={barKey}
            fill={color}
            radius={[4, 4, 0, 0]}
            barSize={barSize}
            label={{
              position: 'top',
              formatter: (value: number) => {
                // 格式化数据标签显示 - 使用激进的格式化去除尾随零
                return formatAggressive(value);
              },
              fontSize: 12,
              fill: '#666'
            }}
          />
        </BarChart>
      </ResponsiveContainer>
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
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis
            dataKey={xAxisKey}
            tick={{ fontSize: 12 }}
          />
          <YAxis tick={{ fontSize: 12 }} />
          {showTooltip && <Tooltip />}
          {showLegend && <Legend />}
          {lines.map((line) => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              name={line.name}
              stroke={line.color}
              strokeWidth={line.strokeWidth || 2}
              dot={showDots}
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
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
      name: item.name,
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
      name: item.name,
      value: Math.round(item.total_area * 100) / 100, // 使用round方法避免浮点精度问题
      total_area: Math.round(item.total_area * 100) / 100,
      percentage: item.area_percentage,
      average_area: item.average_area || 0
    }))
  },

  // 转换面积维度柱状图数据
  toAreaBarData: (data: Array<{ name: string; total_area: number; count?: number; average_area?: number }>): BarData[] => {
    return data.map(item => ({
      name: item.name,
      value: Math.round(item.total_area * 100) / 100, // 使用round方法避免浮点精度问题
      total_area: Math.round(item.total_area * 100) / 100,
      count: item.count || 0,
      average_area: item.average_area || 0
    }))
  },

  // 转换业态类别面积数据
  toBusinessCategoryAreaData: (data: Array<{ category: string; total_area: number; area_percentage: number; occupancy_rate?: number }>): BarData[] => {
    return data.map(item => ({
      name: item.category,
      value: Math.round(item.total_area * 100) / 100, // 使用round方法避免浮点精度问题
      total_area: Math.round(item.total_area * 100) / 100,
      area_percentage: item.area_percentage,
      occupancy_rate: item.occupancy_rate || 0
    }))
  }
}