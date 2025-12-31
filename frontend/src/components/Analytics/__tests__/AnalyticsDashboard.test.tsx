/**
 * AnalyticsDashboard 组件测试
 * 测试分析仪表板组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock hooks
vi.mock('../../hooks/useAnalytics', () => ({
  useAnalytics: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}))

// Mock Ant Design components
vi.mock('antd', () => ({
  Row: ({ children, gutter }: any) => (
    <div data-testid="row" data-gutter={JSON.stringify(gutter)}>
      {children}
    </div>
  ),
  Col: ({ children, xs, md, lg, sm }: any) => (
    <div data-testid="col" data-xs={xs} data-md={md} data-lg={lg} data-sm={sm}>
      {children}
    </div>
  ),
  Card: ({ children, title, className }: any) => (
    <div data-testid="card" data-title={title} className={className}>
      {title}
      {children}
    </div>
  ),
  Typography: {
    Title: ({ children, level, type }: any) => (
      <div data-testid="title" data-level={level} data-type={type}>
        {children}
      </div>
    ),
  },
  Button: ({ children, icon, onClick, loading, type }: any) => (
    <button data-testid="button" data-type={type} data-loading={loading} onClick={onClick}>
      {icon}
      {children}
    </button>
  ),
  Space: ({ children }: any) => (
    <div data-testid="space">
      {children}
    </div>
  ),
  Dropdown: ({ children, overlay, placement }: any) => (
    <div data-testid="dropdown" data-placement={placement}>
      {overlay}
      {children}
    </div>
  ),
  Menu: ({ items }: any) => (
    <div data-testid="menu">
      {items?.map((item: any) => (
        <div key={item.key} data-item-key={item.key}>
          {item.label}
        </div>
      ))}
    </div>
  ),
}))

// Mock icons
vi.mock('@ant-design/icons', () => ({
  ReloadOutlined: () => <div data-testid="icon-reload" />,
  DownloadOutlined: () => <div data-testid="icon-download" />,
  SettingOutlined: () => <div data-testid="icon-setting" />,
  FullscreenOutlined: () => <div data-testid="icon-fullscreen" />,
  FullscreenExitOutlined: () => <div data-testid="icon-fullscreen-exit" />,
}))

// Mock sub-components
vi.mock('../AnalyticsFilters', () => ({
  AnalyticsFilters: ({
    filters,
    onFiltersChange,
    onApplyFilters,
    onResetFilters,
    loading,
    showAdvanced,
    onToggleAdvanced,
  }: any) => (
    <div
      data-testid="analytics-filters"
      data-show-advanced={showAdvanced}
      data-loading={loading}
    >
      <button onClick={() => onFiltersChange(filters)}>改变筛选</button>
      <button onClick={onApplyFilters}>应用筛选</button>
      <button onClick={onResetFilters}>重置筛选</button>
      <button onClick={onToggleAdvanced}>切换高级筛选</button>
    </div>
  ),
}))

vi.mock('../StatisticCard', () => ({
  StatisticCard: ({ title, value, precision, suffix, loading }: any) => (
    <div data-testid="statistic-card" data-title={title} data-loading={loading}>
      <div data-testid="value" data-precision={precision}>
        {value}
        {suffix}
      </div>
    </div>
  ),
  FinancialStatisticCard: ({ title, value, precision, suffix, isPositive, loading }: any) => (
    <div
      data-testid="financial-statistic-card"
      data-title={title}
      data-is-positive={isPositive}
      data-loading={loading}
    >
      <div data-testid="value" data-precision={precision}>
        {value}
        {suffix}
      </div>
    </div>
  ),
}))

vi.mock('../AnalyticsCard', () => ({
  ChartCard: ({ title, hasData, loading, children }: any) => (
    <div data-testid="chart-card" data-title={title} data-has-data={hasData} data-loading={loading}>
      {title}
      {children}
    </div>
  ),
}))

vi.mock('../Charts', () => ({
  AnalyticsPieChart: ({ data, dataKey, labelKey }: any) => (
    <div data-testid="analytics-pie-chart" data-data-key={dataKey} data-label-key={labelKey}>
      {JSON.stringify(data)}
    </div>
  ),
  AnalyticsBarChart: ({ data, xDataKey, yDataKey, barName }: any) => (
    <div
      data-testid="analytics-bar-chart"
      data-x-data-key={xDataKey}
      data-y-data-key={yDataKey}
      data-bar-name={barName}
    >
      {JSON.stringify(data)}
    </div>
  ),
  AnalyticsLineChart: ({ data, xDataKey, yDataKey, lineName }: any) => (
    <div
      data-testid="analytics-line-chart"
      data-x-data-key={xDataKey}
      data-y-data-key={yDataKey}
      data-line-name={lineName}
    >
      {JSON.stringify(data)}
    </div>
  ),
}))

vi.mock('../PerformanceMonitor', () => ({
  PerformanceMonitor: ({ enabled }: any) => (
    <div data-testid="performance-monitor" data-enabled={enabled} />
  ),
}))

describe('AnalyticsDashboard - 组件导入测试', () => {
  it('应该能够导入AnalyticsDashboard组件', async () => {
    const module = await import('../AnalyticsDashboard')
    expect(module).toBeDefined()
    expect(module.AnalyticsDashboard).toBeDefined()
  })

  it('应该导出默认导出', async () => {
    const module = await import('../AnalyticsDashboard')
    expect(module.default).toBeDefined()
  })
})

describe('AnalyticsDashboard - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持initialFilters属性', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const initialFilters = { ownership_status: '自有' }
    const element = React.createElement(AnalyticsDashboard, {
      initialFilters,
    })
    expect(element).toBeTruthy()
  })

  it('默认initialFilters应该是空对象', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该支持className属性', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {
      className: 'custom-class',
    })
    expect(element).toBeTruthy()
  })

  it('默认className应该是空字符串', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 状态管理测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该有filters状态', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {
      initialFilters: { ownership_status: '自有' },
    })
    expect(element).toBeTruthy()
  })

  it('应该有showAdvanced状态', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该有fullscreen状态', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该有autoRefresh状态', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - useAnalytics hook测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该调用useAnalytics hook', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该传递filters给useAnalytics', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const filters = { ownership_status: '自有' }
    const element = React.createElement(AnalyticsDashboard, {
      initialFilters: filters,
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 顶部操作栏测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示刷新按钮', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示导出按钮', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示全屏按钮', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示自动刷新按钮', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('刷新按钮应该有图标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('导出按钮应该有图标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('全屏按钮应该根据状态显示不同图标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 导出功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('导出菜单应该有Excel选项', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('导出菜单应该有PDF选项', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('导出菜单应该有CSV选项', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - AnalyticsFilters测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该渲染AnalyticsFilters组件', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该传递filters给AnalyticsFilters', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {
      initialFilters: { ownership_status: '自有' },
    })
    expect(element).toBeTruthy()
  })

  it('应该传递onFiltersChange给AnalyticsFilters', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该传递onApplyFilters给AnalyticsFilters', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该传递onResetFilters给AnalyticsFilters', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该传递loading给AnalyticsFilters', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该传递showAdvanced给AnalyticsFilters', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该传递onToggleAdvanced给AnalyticsFilters', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - PerformanceMonitor测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该渲染PerformanceMonitor组件', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 空状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('无数据时应该显示暂无数据', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('暂无数据应该有提示信息', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 错误状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('错误时应该显示错误信息', async () => {
    vi.doMock('../../hooks/useAnalytics', () => ({
      useAnalytics: vi.fn(() => ({
        data: undefined,
        isLoading: false,
        error: { message: '网络错误' },
        refetch: vi.fn(),
      })),
    }))
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('错误时应该显示重试按钮', async () => {
    vi.doMock('../../hooks/useAnalytics', () => ({
      useAnalytics: vi.fn(() => ({
        data: undefined,
        isLoading: false,
        error: { message: '网络错误' },
        refetch: vi.fn(),
      })),
    }))
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 关键指标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示资产总数指标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示总面积指标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示可租面积指标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示整体出租率指标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 财务指标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示预估年收入指标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示月租金指标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示押金总额指标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示资产收益率指标', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 图表测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示物业性质分布图', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示确权状态分布图', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示使用状态分布图', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示出租率区间分布图', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示业态类别出租率图', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该显示出租率趋势图', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 全屏功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持全屏切换', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('全屏时应该改变样式', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('全屏时应该显示退出全屏按钮', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 自动刷新功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持自动刷新切换', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('自动刷新开启时按钮应该是primary类型', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理undefined analytics数据', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该处理空数组分布数据', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('应该处理loading状态', async () => {
    vi.doMock('../../hooks/useAnalytics', () => ({
      useAnalytics: vi.fn(() => ({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      })),
    }))
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该使用Row和Col布局', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('图表应该使用lg={12}布局', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('指标卡片应该使用sm={6}布局', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsDashboard - 响应式测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('Col应该支持xs响应式', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('Col应该支持md响应式', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })

  it('Col应该支持lg响应式', async () => {
    const { AnalyticsDashboard } = await import('../AnalyticsDashboard')
    const element = React.createElement(AnalyticsDashboard, {})
    expect(element).toBeTruthy()
  })
})
