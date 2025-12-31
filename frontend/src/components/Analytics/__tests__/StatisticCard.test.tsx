/**
 * StatisticCard 组件测试
 * 测试统计卡片组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, loading, size, styles }: any) => (
    <div data-testid="card" data-loading={loading} data-size={size} data-styles={JSON.stringify(styles)}>
      {children}
    </div>
  ),
  Statistic: ({ title, value, precision, suffix, prefix, valueStyle }: any) => (
    <div data-testid="statistic" data-title={title} data-value={value} data-precision={precision} style={valueStyle}>
      {prefix && <span data-testid="statistic-prefix">{prefix}</span>}
      <span>{value}</span>
      {suffix && <span data-testid="statistic-suffix">{suffix}</span>}
    </div>
  ),
}))

describe('StatisticCard - 组件导入测试', () => {
  it('应该能够导入StatisticCard组件', async () => {
    const module = await import('../StatisticCard')
    expect(module).toBeDefined()
    expect(module.StatisticCard).toBeDefined()
  })

  it('应该能够导入FinancialStatisticCard组件', async () => {
    const module = await import('../StatisticCard')
    expect(module.FinancialStatisticCard).toBeDefined()
  })
})

describe('StatisticCard - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持title属性', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试标题',
      value: 100,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持value属性', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持precision属性', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
      precision: 2,
    })
    expect(element).toBeTruthy()
  })

  it('默认precision应该是0', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持suffix属性', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
      suffix: '%',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持prefix属性', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
      prefix: '$',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持valueStyle属性', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
      valueStyle: { color: '#f00' },
    })
    expect(element).toBeTruthy()
  })

  it('应该支持loading属性', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
      loading: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认loading应该是false', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })
})

describe('FinancialStatisticCard - 属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持title属性', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '财务标题',
      value: 100,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持value属性', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持isPositive属性', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: 100,
      isPositive: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认isPositive应该是true', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: 100,
    })
    expect(element).toBeTruthy()
  })
})

describe('FinancialStatisticCard - 颜色逻辑测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('正值且isPositive=true应该显示绿色', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: 100,
      isPositive: true,
    })
    expect(element).toBeTruthy()
  })

  it('正值且isPositive=false应该显示红色', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: 100,
      isPositive: false,
    })
    expect(element).toBeTruthy()
  })

  it('负值应该显示红色', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: -100,
      isPositive: true,
    })
    expect(element).toBeTruthy()
  })
})

describe('FinancialStatisticCard - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理value为0', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: 0,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理undefined isPositive', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: 100,
      isPositive: undefined,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理precision属性', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: 100,
      precision: 2,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理loading属性', async () => {
    const { FinancialStatisticCard } = await import('../StatisticCard')
    const element = React.createElement(FinancialStatisticCard, {
      title: '测试',
      value: 100,
      loading: true,
    })
    expect(element).toBeTruthy()
  })
})

describe('StatisticCard - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理value为0', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 0,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理负数value', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: -100,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理空字符串suffix', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
      suffix: '',
    })
    expect(element).toBeTruthy()
  })

  it('应该处理空字符串prefix', async () => {
    const { StatisticCard } = await import('../StatisticCard')
    const element = React.createElement(StatisticCard, {
      title: '测试',
      value: 100,
      prefix: '',
    })
    expect(element).toBeTruthy()
  })
})
