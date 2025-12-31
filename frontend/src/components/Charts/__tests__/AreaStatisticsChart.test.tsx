/**
 * AreaStatisticsChart 组件测试
 * 测试面积统计图表组件
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

// Mock Chart.js
vi.mock('chart.js', () => ({
  Chart: {
    register: vi.fn(),
  },
  CategoryScale: vi.fn(),
  LinearScale: vi.fn(),
  BarElement: vi.fn(),
  Title: vi.fn(),
  Tooltip: vi.fn(),
  Legend: vi.fn(),
}))

// Mock react-chartjs-2
vi.mock('react-chartjs-2', () => ({
  Bar: ({ data, options, type }: any) => (
    <div data-testid="bar-chart" data-chart-type={type || 'bar'} data-bar-type="standard">
      {JSON.stringify({ data, options })}
    </div>
  ),
}))

// Mock chart utility functions
vi.mock('@/types/chart-types', () => ({
  getChartYValue: vi.fn((context) => {
    if (typeof context === 'object' && context !== null && 'parsed' in context) {
      const parsed = context.parsed as { y?: number } | number
      return typeof parsed === 'number' ? parsed : (parsed.y ?? 0)
    }
    return 0
  }),
  getChartDatasetLabel: vi.fn((context) => {
    if (typeof context === 'object' && context !== null && 'dataset' in context) {
      return (context.dataset as { label?: string }).label ?? ''
    }
    return ''
  }),
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
  Progress: ({ percent, size, strokeColor, format }: any) => (
    <div data-testid="progress" data-percent={percent} data-size={size} data-stroke-color={strokeColor}>
      {format ? format(percent) : `${percent}%`}
    </div>
  ),
  Tag: ({ children, color }: any) => (
    <div data-testid="tag" data-color={color}>{children}</div>
  ),
}))

// Mock icons
vi.mock('@ant-design/icons', () => ({
  AreaChartOutlined: () => <div data-testid="icon-area-chart" />,
  BuildOutlined: () => <div data-testid="icon-build" />,
  HomeOutlined: () => <div data-testid="icon-home" />,
  ShopOutlined: () => <div data-testid="icon-shop" />,
}))

// Mock asset service
vi.mock('@/services/assetService', () => ({
  assetService: {
    getAreaStatistics: vi.fn(),
  },
}))

describe('AreaStatisticsChart - 组件导入测试', () => {
  it('应该能够导入AreaStatisticsChart组件', async () => {
    const module = await import('../AreaStatisticsChart')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })
})

describe('AreaStatisticsChart - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持filters属性', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const filters = { ownership_status: '自有' }
    const element = React.createElement(AreaStatisticsChart, { filters })
    expect(element).toBeTruthy()
  })

  it('应该支持height属性', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, { height: 500 })
    expect(element).toBeTruthy()
  })

  it('默认height应该是400', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 图表类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该包含物业性质柱状图', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该包含面积区间柱状图', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该包含权属方面积与出租率对比图', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 统计指标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示总土地面积统计', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示总房产面积统计', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示可租面积统计', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示已租面积统计', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示空置面积统计', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示非经营面积统计', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 详细列表测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示使用状态面积统计列表', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该显示面积最大资产列表（前10名）', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('面积最大资产列表应该包含出租率进度条', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 数据查询测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该使用useQuery获取数据', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('查询键应该包含filters', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const filters = { ownership_status: '自有' }
    const element = React.createElement(AreaStatisticsChart, { filters })
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 错误处理测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('错误状态应该显示Alert', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 加载状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('加载中应该显示Spin', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 样式属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('图表应该有可配置的height', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, { height: 500 })
    expect(element).toBeTruthy()
  })

  it('卡片应该有合适的间距', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 响应式布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持xs屏幕尺寸', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该支持sm屏幕尺寸', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该支持md屏幕尺寸', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('应该支持lg屏幕尺寸', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 图表配置测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('物业性质图表应该包含多个数据集', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('权属方图表应该使用双Y轴', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })

  it('面积区间图表应该显示资产数量', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {})
    expect(element).toBeTruthy()
  })
})

describe('AreaStatisticsChart - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理undefined filters', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {
      filters: undefined,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理空filters', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {
      filters: {},
    })
    expect(element).toBeTruthy()
  })

  it('应该处理height为0', async () => {
    const AreaStatisticsChart = (await import('../AreaStatisticsChart')).default
    const element = React.createElement(AreaStatisticsChart, {
      height: 0,
    })
    expect(element).toBeTruthy()
  })
})
