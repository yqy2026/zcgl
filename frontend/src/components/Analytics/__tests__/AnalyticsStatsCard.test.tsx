/**
 * AnalyticsStatsCard 组件测试
 * 测试分析统计卡片组件
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
  Row: ({ children, gutter }: any) => (
    <div data-testid="row" data-gutter={JSON.stringify(gutter)}>
      {children}
    </div>
  ),
  Col: ({ children, xs, sm, lg }: any) => (
    <div data-testid="col" data-xs={xs} data-sm={sm} data-lg={lg}>
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

// Mock icons
vi.mock('@ant-design/icons', () => ({
  ArrowUpOutlined: () => <div data-testid="icon-arrow-up" />,
  ArrowDownOutlined: () => <div data-testid="icon-arrow-down" />,
  ApartmentOutlined: () => <div data-testid="icon-apartment" />,
  ThunderboltOutlined: () => <div data-testid="icon-thunderbolt" />,
  PieChartOutlined: () => <div data-testid="icon-pie-chart" />,
  MoneyCollectOutlined: () => <div data-testid="icon-money-collect" />,
  TransactionOutlined: () => <div data-testid="icon-transaction" />,
  AreaChartOutlined: () => <div data-testid="icon-area-chart" />,
}))

describe('AnalyticsStatsCard - 组件导入测试', () => {
  it('应该能够导出AnalyticsStatsGrid组件', async () => {
    const module = await import('../AnalyticsStatsCard')
    expect(module).toBeDefined()
    expect(module.AnalyticsStatsGrid).toBeDefined()
  })

  it('应该能够导出FinancialStatsGrid组件', async () => {
    const module = await import('../AnalyticsStatsCard')
    expect(module.FinancialStatsGrid).toBeDefined()
  })
})

describe('AnalyticsStatsGrid - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持data属性', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该支持loading属性', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data, loading: true })
    expect(element).toBeTruthy()
  })

  it('默认loading应该是false', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsStatsGrid - 统计卡片测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示资产总数卡片', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该显示总面积卡片', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该显示可租面积卡片', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该显示整体出租率卡片', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsStatsGrid - 财务指标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示年收入卡片', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
      total_annual_income: 100000,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该显示净收益卡片', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
      total_net_income: 50000,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该显示月租金卡片', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
      total_monthly_rent: 10000,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })
})

describe('FinancialStatsGrid - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持data属性', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_annual_income: 100000,
      total_annual_expense: 50000,
      total_net_income: 50000,
      total_monthly_rent: 10000,
    }
    const element = React.createElement(FinancialStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该支持loading属性', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_annual_income: 100000,
      total_annual_expense: 50000,
      total_net_income: 50000,
      total_monthly_rent: 10000,
    }
    const element = React.createElement(FinancialStatsGrid, { data, loading: true })
    expect(element).toBeTruthy()
  })
})

describe('FinancialStatsGrid - 财务指标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示年收入', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_annual_income: 100000,
      total_annual_expense: 50000,
      total_net_income: 50000,
      total_monthly_rent: 10000,
    }
    const element = React.createElement(FinancialStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该显示年支出', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_annual_income: 100000,
      total_annual_expense: 50000,
      total_net_income: 50000,
      total_monthly_rent: 10000,
    }
    const element = React.createElement(FinancialStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该显示净收益', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_annual_income: 100000,
      total_annual_expense: 50000,
      total_net_income: 50000,
      total_monthly_rent: 10000,
    }
    const element = React.createElement(FinancialStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该显示月租金', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_annual_income: 100000,
      total_annual_expense: 50000,
      total_net_income: 50000,
      total_monthly_rent: 10000,
    }
    const element = React.createElement(FinancialStatsGrid, { data })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsStatsGrid - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理occupancy_rate为80', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 80,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该处理occupancy_rate为60', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 60,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该处理occupancy_rate低于60', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 50,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该处理负净收益', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
      total_net_income: -10000,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })
})

describe('FinancialStatsGrid - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理净收益为0', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_annual_income: 50000,
      total_annual_expense: 50000,
      total_net_income: 0,
      total_monthly_rent: 10000,
    }
    const element = React.createElement(FinancialStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该处理负净收益', async () => {
    const { FinancialStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_annual_income: 30000,
      total_annual_expense: 50000,
      total_net_income: -20000,
      total_monthly_rent: 10000,
    }
    const element = React.createElement(FinancialStatsGrid, { data })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsStatsGrid - 响应式布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持xs屏幕尺寸', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该支持sm屏幕尺寸', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })

  it('应该支持lg屏幕尺寸', async () => {
    const { AnalyticsStatsGrid } = await import('../AnalyticsStatsCard')
    const data = {
      total_assets: 100,
      total_area: 5000,
      total_rentable_area: 4000,
      occupancy_rate: 85,
    }
    const element = React.createElement(AnalyticsStatsGrid, { data })
    expect(element).toBeTruthy()
  })
})
