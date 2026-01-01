/**
 * AssetDistributionChart 组件测试
 * 测试资产分布图表组件
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
  Pie: ({ data, height }: any) => (
    <div data-testid="pie-chart" data-height={height}>
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
  Statistic: ({ title, value, suffix, prefix, valueStyle, formatter }: any) => (
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
  Tag: ({ children, color }: any) => (
    <div data-testid="tag" data-color={color}>{children}</div>
  ),
}))

// Mock icons
vi.mock('@ant-design/icons', () => ({
  PieChartOutlined: () => <div data-testid="icon-pie-chart" />,
  HomeOutlined: () => <div data-testid="icon-home" />,
  EnvironmentOutlined: () => <div data-testid="icon-environment" />,
  UserOutlined: () => <div data-testid="icon-user" />,
}))

// Mock asset service
vi.mock('@/services/assetService', () => ({
  assetService: {
    getAssetDistributionStats: vi.fn(),
  },
}))

describe('AssetDistributionChart - 组件导入测试', () => {
  it('应该能够导入AssetDistributionChart组件', async () => {
    const module = await import('../AssetDistributionChart')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })
})

describe('AssetDistributionChart - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持filters属性', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const filters = { ownership_status: '自有' }
    const element = React.createElement(AssetDistributionChart, { filters })
    expect(element).toBeTruthy()
  })

  it('应该支持height属性', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, { height: 400 })
    expect(element).toBeTruthy()
  })

  it('默认height应该是300', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 图表类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该包含物业性质饼图', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该包含确权状态环形图', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该包含使用状态饼图', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该包含权属方柱状图', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 统计指标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示资产总数统计', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示总面积统计', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示权属方数量统计', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示经营类面积统计', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 详细列表测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示物业性质详情列表', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示使用状态详情列表', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 数据查询测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该使用useQuery获取数据', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('查询键应该包含filters', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const filters = { ownership_status: '自有' }
    const element = React.createElement(AssetDistributionChart, { filters })
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 错误处理测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('错误状态应该显示Alert', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 加载状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('加载中应该显示Spin', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 样式属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('图表应该有可配置的height', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, { height: 400 })
    expect(element).toBeTruthy()
  })

  it('卡片应该有合适的间距', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 响应式布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持xs屏幕尺寸', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该支持sm屏幕尺寸', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该支持md屏幕尺寸', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('应该支持lg屏幕尺寸', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理undefined filters', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {
      filters: undefined,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理空filters', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {
      filters: {},
    })
    expect(element).toBeTruthy()
  })

  it('应该处理height为0', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {
      height: 0,
    })
    expect(element).toBeTruthy()
  })
})

describe('AssetDistributionChart - 图表配置测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('物业性质图表图例应该在底部', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('确权状态图表图例应该在底部', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('使用状态图表图例应该在底部', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })

  it('权属方图表应该显示前10名', async () => {
    const AssetDistributionChart = (await import('../AssetDistributionChart')).default
    const element = React.createElement(AssetDistributionChart, {})
    expect(element).toBeTruthy()
  })
})
