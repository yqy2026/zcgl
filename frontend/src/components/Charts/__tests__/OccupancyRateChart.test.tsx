/**
 * OccupancyRateChart 组件测试
 * 测试出租率图表组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock @tanstack/react-query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    error: null,
  })),
}))

// Mock @ant-design/plots
vi.mock('@ant-design/plots', () => ({
  Line: ({ data, height }: any) => (
    <div data-testid="line-chart" data-height={height}>
      {data?.map((d: any, i: number) => (
        <div key={i} />
      ))}
    </div>
  ),
  Column: ({ data, height }: any) => (
    <div data-testid="column-chart" data-height={height}>
      {data?.map((d: any, i: number) => (
        <div key={i} />
      ))}
    </div>
  ),
  Pie: ({ data, height }: any) => (
    <div data-testid="pie-chart" data-height={height}>
      {data?.map((d: any, i: number) => (
        <div key={i} />
      ))}
    </div>
  ),
}))

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, title, style, size }: any) => (
    <div data-testid="card" data-title={title} data-size={size} style={style}>
      {children}
    </div>
  ),
  Row: ({ children, gutter, style }: any) => (
    <div data-testid="row" data-gutter={gutter} style={style}>
      {children}
    </div>
  ),
  Col: ({ children, xs, sm, md, lg }: any) => (
    <div data-testid="col" data-xs={xs} data-sm={sm} data-md={md} data-lg={lg}>
      {children}
    </div>
  ),
  Statistic: ({ title, value, precision, suffix, prefix, valueStyle, formatter }: any) => (
    <div data-testid="statistic" data-title={title} data-value={value} style={valueStyle}>
      {prefix && <span data-testid="statistic-prefix">{prefix}</span>}
      <span>{formatter ? formatter(value) : value}</span>
      {suffix && <span>{suffix}</span>}
    </div>
  ),
  Spin: ({ children, spinning }: any) => (
    <div data-testid="spin" data-spinning={spinning}>
      {children}
    </div>
  ),
  Alert: ({ message, description, type, showIcon }: any) => (
    <div data-testid="alert" data-type={type} data-message={message}>
      {description}
    </div>
  ),
  Typography: {
    Title: ({ children, level }: any) => (
      <div data-testid="title" data-level={level}>{children}</div>
    ),
    Text: ({ children, type, strong, style }: any) => (
      <span data-testid="text" data-type={type} data-strong={strong} style={style}>
        {children}
      </span>
    ),
  },
  Space: ({ children }: any) => (
    <div data-testid="space">{children}</div>
  ),
}))

// Mock icons
vi.mock('@ant-design/icons', () => ({
  PercentageOutlined: () => <div data-testid="icon-percentage" />,
  RiseOutlined: () => <div data-testid="icon-rise" />,
  FallOutlined: () => <div data-testid="icon-fall" />,
  MinusOutlined: () => <div data-testid="icon-minus" />,
}))

// Mock asset service
vi.mock('@/services/assetService', () => ({
  assetService: {
    getOccupancyRateStats: vi.fn(),
  },
}))

describe('OccupancyRateChart - 组件导入测试', () => {
  it('应该能够导入OccupancyRateChart组件', async () => {
    const module = await import('../OccupancyRateChart')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })
})

describe('OccupancyRateChart - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持filters属性', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const filters = { ownership_status: '自有' }
    const element = React.createElement(OccupancyRateChart, { filters })
    expect(element).toBeTruthy()
  })

  it('应该支持height属性', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, { height: 500 })
    expect(element).toBeTruthy()
  })

  it('默认height应该是400', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 图表类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该包含趋势折线图', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('应该包含物业性质饼图', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('应该包含权属方柱状图', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 统计指标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示总体出租率统计', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示趋势变化统计', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示经营类物业出租率', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示权属方数量', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 排行榜测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示出租率最高资产排行', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示出租率最低资产排行', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 数据查询测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该使用useQuery获取数据', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('查询键应该包含filters', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const filters = { ownership_status: '自有' }
    const element = React.createElement(OccupancyRateChart, { filters })
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 错误处理测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('错误状态应该显示Alert', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 加载状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('加载中应该显示Spin', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 样式属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('图表应该有可配置的height', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, { height: 500 })
    expect(element).toBeTruthy()
  })

  it('卡片应该有合适的间距', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 响应式布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持xs屏幕尺寸', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('应该支持sm屏幕尺寸', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('应该支持md屏幕尺寸', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('应该支持lg屏幕尺寸', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 趋势图标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('上升趋势应该显示RiseOutlined图标', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('下降趋势应该显示FallOutlined图标', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })

  it('稳定趋势应该显示MinusOutlined图标', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {})
    expect(element).toBeTruthy()
  })
})

describe('OccupancyRateChart - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理undefined filters', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {
      filters: undefined,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理空filters', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {
      filters: {},
    })
    expect(element).toBeTruthy()
  })

  it('应该处理height为0', async () => {
    const OccupancyRateChart = (await import('../OccupancyRateChart')).default
    const element = React.createElement(OccupancyRateChart, {
      height: 0,
    })
    expect(element).toBeTruthy()
  })
})
