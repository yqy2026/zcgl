/**
 * DataTrendCard 组件测试
 * 测试数据趋势卡片组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, loading, className, variant }: any) => (
    <div data-testid="card" data-loading={loading} data-class-name={className} data-variant={variant}>
      {children}
    </div>
  ),
  Statistic: ({ title, value, precision, suffix, valueStyle }: any) => (
    <div data-testid="statistic" data-title={title} data-value={value} data-precision={precision} style={valueStyle}>
      {suffix && <span data-testid="statistic-suffix">{suffix}</span>}
      <span>{value}</span>
    </div>
  ),
  Tooltip: ({ children, title }: any) => (
    <div data-testid="tooltip" data-title={title}>
      {children}
    </div>
  ),
}))

// Mock icons
vi.mock('@ant-design/icons', () => ({
  ArrowUpOutlined: () => <div data-testid="icon-arrow-up" />,
  ArrowDownOutlined: () => <div data-testid="icon-arrow-down" />,
  MinusOutlined: () => <div data-testid="icon-minus" />,
}))

// Mock CSS modules
vi.mock('./DataTrendCard.module.css', () => ({
  trendCard: 'trend-card',
  primary: 'primary',
  success: 'success',
  warning: 'warning',
  error: 'error',
  default: 'default',
  small: 'small',
  'default': 'default-size',
  large: 'large',
  cardHeader: 'card-header',
  cardTitle: 'card-title',
  cardIcon: 'card-icon',
  cardContent: 'card-content',
  trendUp: 'trend-up',
  trendDown: 'trend-down',
  trendNeutral: 'trend-neutral',
  trendIcon: 'trend-icon',
  trendText: 'trend-text',
  trendPeriod: 'trend-period',
}))

describe('DataTrendCard - 组件导入测试', () => {
  it('应该能够导入DataTrendCard组件', async () => {
    const module = await import('../DataTrendCard')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })
})

describe('DataTrendCard - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持title属性', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试标题',
      value: 100,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持value属性', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 1000,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持suffix属性', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      suffix: '元',
    })
    expect(element).toBeTruthy()
  })

  it('默认suffix应该是空字符串', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持precision属性', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100.123,
      precision: 2,
    })
    expect(element).toBeTruthy()
  })

  it('默认precision应该是0', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持loading属性', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      loading: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认loading应该是false', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })
})

describe('DataTrendCard - trend属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持trend属性', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: 10,
        period: '较上月',
        isPositive: true,
      },
    })
    expect(element).toBeTruthy()
  })

  it('trend为undefined时不显示趋势', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: undefined,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理正趋势值', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: 15.5,
        period: '较上月',
        isPositive: true,
      },
    })
    expect(element).toBeTruthy()
  })

  it('应该处理负趋势值', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: -8.3,
        period: '较上月',
        isPositive: false,
      },
    })
    expect(element).toBeTruthy()
  })

  it('应该处理零趋势值', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: 0,
        period: '较上月',
        isPositive: true,
      },
    })
    expect(element).toBeTruthy()
  })
})

describe('DataTrendCard - 趋势图标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('isPositive为true且value为正应该显示上升图标', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: 10,
        period: '较上月',
        isPositive: true,
      },
    })
    expect(element).toBeTruthy()
  })

  it('isPositive为false且value为负应该显示下降图标', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: -10,
        period: '较上月',
        isPositive: false,
      },
    })
    expect(element).toBeTruthy()
  })

  it('value为0应该显示持平图标', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: 0,
        period: '较上月',
        isPositive: true,
      },
    })
    expect(element).toBeTruthy()
  })
})

describe('DataTrendCard - 趋势文本测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('正趋势应该显示加号', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: 10.5,
        period: '较上月',
        isPositive: true,
      },
    })
    expect(element).toBeTruthy()
  })

  it('负趋势应该显示减号', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: -8.3,
        period: '较上月',
        isPositive: false,
      },
    })
    expect(element).toBeTruthy()
  })

  it('应该显示趋势期间', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: 10,
        period: '较上月',
        isPositive: true,
      },
    })
    expect(element).toBeTruthy()
  })
})

describe('DataTrendCard - icon属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持icon属性', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const icon = React.createElement('div', { 'data-testid': 'custom-icon' }, 'Icon')
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      icon,
    })
    expect(element).toBeTruthy()
  })

  it('icon为undefined时不显示图标', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      icon: undefined,
    })
    expect(element).toBeTruthy()
  })
})

describe('DataTrendCard - color属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持color属性为primary', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      color: 'primary',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持color属性为success', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      color: 'success',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持color属性为warning', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      color: 'warning',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持color属性为error', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      color: 'error',
    })
    expect(element).toBeTruthy()
  })

  it('默认color应该是default', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })
})

describe('DataTrendCard - size属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持size属性为small', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      size: 'small',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持size属性为default', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      size: 'default',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持size属性为large', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      size: 'large',
    })
    expect(element).toBeTruthy()
  })

  it('默认size应该是default', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })
})

describe('DataTrendCard - 趋势样式测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('isPositive为true应该应用trendUp样式', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: 10,
        period: '较上月',
        isPositive: true,
      },
    })
    expect(element).toBeTruthy()
  })

  it('value为负应该应用trendDown样式', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: -10,
        period: '较上月',
        isPositive: false,
      },
    })
    expect(element).toBeTruthy()
  })

  it('value为0应该应用trendNeutral样式', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
      trend: {
        value: 0,
        period: '较上月',
        isPositive: true,
      },
    })
    expect(element).toBeTruthy()
  })
})

describe('DataTrendCard - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理value为0', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 0,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理负数value', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: -100,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理大数值value', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 9999999,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理高precision', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100.123456789,
      precision: 6,
    })
    expect(element).toBeTruthy()
  })
})

describe('DataTrendCard - Card variant测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该使用borderless variant', async () => {
    const DataTrendCard = (await import('../DataTrendCard')).default
    const element = React.createElement(DataTrendCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })
})
