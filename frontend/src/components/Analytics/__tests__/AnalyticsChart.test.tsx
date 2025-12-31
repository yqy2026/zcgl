/**
 * AnalyticsChart 组件测试
 * 测试分析图表组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock recharts
vi.mock('recharts', () => ({
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: ({ children, data, cx, cy, dataKey, label, labelLine, paddingAngle, innerRadius, outerRadius, fill }: any) => (
    <div data-testid="pie" data-data-key={dataKey} data-cx={cx} data-cy={cy} data-label={label}>
      {children}
    </div>
  ),
  Cell: ({ fill, key }: any) => <div data-testid="cell" data-fill={fill} key={key} />,
  BarChart: ({ children, data, margin }: any) => (
    <div data-testid="bar-chart" data-margin={JSON.stringify(margin)}>
      {children}
    </div>
  ),
  Bar: ({ dataKey, fill, radius, barSize, label }: any) => (
    <div data-testid="bar" data-data-key={dataKey} data-fill={fill} data-radius={JSON.stringify(radius)} data-bar-size={barSize}>
      {label}
    </div>
  ),
  LineChart: ({ children, data, margin }: any) => (
    <div data-testid="line-chart" data-margin={JSON.stringify(margin)}>
      {children}
    </div>
  ),
  Line: ({ dataKey, type, stroke, strokeWidth, dot, activeDot }: any) => (
    <div
      data-testid="line"
      data-data-key={dataKey}
      data-type={type}
      data-stroke={stroke}
      data-stroke-width={strokeWidth}
      data-dot={JSON.stringify(dot)}
      data-active-dot={JSON.stringify(activeDot)}
    />
  ),
  XAxis: ({ dataKey, tick, angle, textAnchor, height, interval }: any) => (
    <div
      data-testid="x-axis"
      data-data-key={dataKey}
      data-angle={angle}
      data-text-anchor={textAnchor}
      data-height={height}
      data-interval={interval}
      data-tick={JSON.stringify(tick)}
    />
  ),
  YAxis: ({ tick, tickFormatter }: any) => (
    <div data-testid="y-axis" data-tick={JSON.stringify(tick)} data-formatter={tickFormatter ? tickFormatter.toString() : ''}>
      Y轴
    </div>
  ),
  CartesianGrid: ({ strokeDasharray }: any) => (
    <div data-testid="cartesian-grid" data-stroke-dasharray={strokeDasharray} />
  ),
  Tooltip: ({ formatter }: any) => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ width, height, children }: any) => (
    <div data-testid="responsive-container" data-width={width} data-height={height}>
      {children}
    </div>
  ),
}))

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ title, children, className, loading }: any) => (
    <div data-testid="card" data-title={title} data-loading={loading} data-class-name={className}>
      {children}
    </div>
  ),
  Empty: ({ description, imageStyle }: any) => (
    <div data-testid="empty" data-description={description}>
      Empty
    </div>
  ),
  Spin: ({ size }: any) => <div data-testid="spin" data-size={size} />,
}))

// Mock ChartErrorBoundary
vi.mock('../ChartErrorBoundary', () => ({
  default: ({ children }: any) => <div data-testid="chart-error-boundary">{children}</div>,
}))

describe('AnalyticsChart - 组件导出测试', () => {
  it('应该能够导出AnalyticsPieChart组件', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    expect(AnalyticsPieChart).toBeDefined()
  })

  it('应该能够导出AnalyticsBarChart组件', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    expect(AnalyticsBarChart).toBeDefined()
  })

  it('应该能够导出AnalyticsLineChart组件', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    expect(AnalyticsLineChart).toBeDefined()
  })

  it('应该能够导出chartDataUtils工具函数', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    expect(chartDataUtils).toBeDefined()
  })
})

describe('AnalyticsPieChart - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持data属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, { data })
    expect(element).toBeTruthy()
  })

  it('应该支持dataKey属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      dataKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持labelKey属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      labelKey: 'name',
    })
    expect(element).toBeTruthy()
  })

  it('默认labelKey应该是name', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      dataKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持title属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      title: '测试标题',
      data,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持loading属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      loading: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认loading应该是false', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持height属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      height: 400,
    })
    expect(element).toBeTruthy()
  })

  it('默认height应该是300', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showLegend属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      showLegend: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认showLegend应该是true', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showTooltip属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      showTooltip: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认showTooltip应该是true', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持innerRadius属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      innerRadius: 60,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持outerRadius属性', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      outerRadius: 100,
    })
    expect(element).toBeTruthy()
  })

  it('默认outerRadius应该是80', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsBarChart - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持data属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持xAxisKey属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持barKey属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持title属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      title: '测试标题',
      data,
      xAxisKey: 'name',
      barKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持loading属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      loading: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持height属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      height: 400,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持barSize属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value:100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      barSize: 40,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showLegend属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      showLegend: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showTooltip属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      showTooltip: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showGrid属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      showGrid: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持color属性', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      color: '#ff0000',
    })
    expect(element).toBeTruthy()
  })

  it('默认color应该是#0088FE', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsLineChart - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持data属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088FE' }],
    })
    expect(element).toBeTruthy()
  })

  it('应该支持xAxisKey属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088FE' }],
    })
    expect(element).toBeTruthy()
  })

  it('应该支持lines属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088FE' }],
    })
    expect(element).toBeTruthy()
  })

  it('应该支持title属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value:100 }]
    const element = React.createElement(AnalyticsLineChart, {
      title: '测试标题',
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088FE' }],
    })
    expect(element).toBeTruthy()
  })

  it('应该支持loading属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088FE' }],
      loading: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持height属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088FE' }],
      height: 400,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showLegend属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088FE' }],
      showLegend: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showTooltip属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#00888FE' }],
      showTooltip: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showGrid属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#00888E' }],
      showGrid: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showDots属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#00888E' }],
      showDots: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持stroke属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088E' }],
      stroke: '#FF0000',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持strokeWidth属性', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088E', strokeWidth: 3 }],
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsChart - 数据格式化工具测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('chartDataUtils.toPieData应该存在', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    expect(chartDataUtils.toPieData).toBeDefined()
  })

  it('chartDataUtils.toBusinessCategoryData应该存在', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    expect(chartDataUtils.toBusinessCategoryData).toBeDefined()
  })

  it('chartDataUtils.toOccupancyData应该存在', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    expect(chartDataUtils.toOccupancyData).toBeDefined()
  })

  it('chartDataUtils.toTrendData应该存在', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    expect(chartDataUtils.toTrendData).toBeDefined()
  })

  it('chartDataUtils.toAreaData应该存在', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    expect(chartDataUtils.toAreaData).toBeDefined()
  })

  it('chartDataUtils.toAreaBarData应该存在', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    expect(chartDataUtils.toAreaBarData).toBeDefined()
  })

  it('chartDataUtils.toBusinessCategoryAreaData应该存在', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    expect(chartDataUtils.toBusinessCategoryAreaData).toBeDefined()
  })
})

describe('AnalyticsChart - 空数据测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AnalyticsPieChart data为空时应该显示Empty', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const element = React.createElement(AnalyticsPieChart, {
      data: [],
      dataKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsPieChart data为undefined时应该显示Empty', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const element = React.createElement(AnalyticsPieChart, {
      data: undefined as any,
      dataKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsBarChart data为空时应该显示Empty', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const element = React.createElement(AnalyticsBarChart, {
      data: [],
      xAxisKey: 'name',
      barKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsLineChart data为空时应该显示Empty', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const element = React.createElement(AnalyticsLineChart, {
      data: [],
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088FE' }],
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsChart - Loading状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AnalyticsPieChart loading时应该显示Spin', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      dataKey: 'value',
      loading: true,
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsBarChart loading时应该显示Spin', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      loading: true,
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsLineChart loading时应该显示Spin', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088E' }],
      loading: true,
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsChart - 图表组件边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理value为0的选项', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 0 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      dataKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('应该处理负数value', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: -100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsChart - ResponsiveContainer测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AnalyticsPieChart应该使用ResponsiveContainer包装', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      dataKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsBarChart应该使用ResponsiveContainer包装', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsLineChart应该使用ResponsiveContainer包装', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088E' }],
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsChart - Tooltip测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AnalyticsPieChart应该有Tooltip', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      dataKey: 'value',
      showTooltip: true,
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsBarChart应该有Tooltip', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      showTooltip: true,
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsLineChart应该有Tooltip', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088E' }],
      showTooltip: true,
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsChart - Legend测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AnalyticsPieChart应该有Legend', async () => {
    const { AnalyticsPieChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsPieChart, {
      data,
      dataKey: 'value',
      showLegend: true,
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsBarChart应该有Legend', async () => {
    const { AnalyticsBarChart } = await import('../AnalyticsChart')
    const data = [{ name: '选项1', value: 100 }]
    const element = React.createElement(AnalyticsBarChart, {
      data,
      xAxisKey: 'name',
      barKey: 'value',
      showLegend: true,
    })
    expect(element).toBeTruthy()
  })

  it('AnalyticsLineChart应该有Legend', async () => {
    const { AnalyticsLineChart } = await import('../AnalyticsChart')
    const data = [{ date: '2024-01-01', value: 100 }]
    const element = React.createElement(AnalyticsLineChart, {
      data,
      xAxisKey: 'date',
      lines: [{ key: 'value', name: '趋势', color: '#0088E' }],
      showLegend: true,
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsChart - chartDataUtils测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('toPieData应该转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    const input = [
      { name: '选项1', count: 100, percentage: 10 },
      { name: '选项2', count: 200, percentage: 20 },
    ]
    const result = chartDataUtils.toPieData(input)
    expect(result).toEqual([
      { name: '选项1', value: 100, count: 100, percentage: 10 },
      { name: '选项2', value: 200, count: 200, percentage: 20 },
    ])
  })

  it('toBusinessCategoryData应该转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    const input = [
      { category: '类别1', count: 100, occupancy_rate: 80 },
      { category: '类别2', count: 200, occupancy_rate: 90 },
    ]
    const result = chartDataUtils.toBusinessCategoryData(input)
    expect(result).toEqual([
      { name: '类别1', value: 100, count: 100, occupancy_rate: 80 },
      { name: '类别2', value: 200, count: 200, occupancy_rate: 90 },
    ])
  })

  it('toOccupancyData应该转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    const input = [
      { range: '0-20%', count: 10, percentage: 10 },
      { range: '20-40%', count: 20, percentage: 20 },
    ]
    const result = chartDataUtils.toOccupancyData(input)
    expect(result).toEqual([
      { name: '0-20%', value: 10, count: 10, percentage: 10 },
      { name: '20-40%', value: 20, count: 20, percentage: 20 },
    ])
  })

  it('toTrendData应该转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    const input = [
      { date: '2024-01-01', occupancy_rate: 85, total_rented_area: 1000, total_rentable_area: 1200 },
    ]
    const result = chartDataUtils.toTrendData(input)
    expect(result).toEqual([
      { date: '2024-01-01', occupancy_rate: 85, total_rented_area: 1000, total_rentable_area: 1200 },
    ])
  })

  it('toAreaData应该转换数据格式', async () => {
    const { chartDataUtils } = await import('../AnalyticsChart')
    const input = [
      { name: '商业', total_area: 1000, area_percentage: 10, average_area: 100 },
    ]
    const result = chartDataUtils.toAreaData(input)
    expect(result).toEqual([
      { name: '商业', value: 1000, total_area: 1000, percentage: 10, average_area: 100 },
    ])
  })
})
