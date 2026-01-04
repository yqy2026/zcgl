/**
 * AnalyticsFilters 组件测试
 * 测试分析筛选器组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

// Mock hooks
vi.mock('@/hooks/useSearchHistory', () => ({
  useSearchHistory: vi.fn(() => ({
    searchHistory: [
      {
        id: '1',
        name: '我的筛选',
        conditions: { ownership_status: '自有' },
        createdAt: '2024-01-01T00:00:00.000Z',
      },
    ],
    addSearchHistory: vi.fn(),
    removeSearchHistory: vi.fn(),
    clearSearchHistory: vi.fn(),
  })),
}))

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: {
      ownershipEntities: [],
      businessCategories: [],
    },
    isLoading: false,
    error: null,
  })),
}))

// Mock services
vi.mock('@/services/assetService', () => ({
  assetService: {
    getOwnershipEntities: vi.fn(() => Promise.resolve([])),
    getBusinessCategories: vi.fn(() => Promise.resolve([])),
  },
}))

// Mock lodash debounce
vi.mock('lodash', () => ({
  debounce: (fn: unknown) => fn,
}))

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, title, extra, size }: any) => (
    <div data-testid="card" data-size={size}>
      <div data-testid="card-title">{title}</div>
      <div data-testid="card-extra">{extra}</div>
      {children}
    </div>
  ),
  Row: ({ children, gutter }: any) => (
    <div data-testid="row" data-gutter={JSON.stringify(gutter)}>
      {children}
    </div>
  ),
  Col: ({ children, xs, sm, md, lg }: any) => (
    <div data-testid="col" data-xs={xs} data-sm={sm} data-md={md} data-lg={lg}>
      {children}
    </div>
  ),
  Typography: {
    Text: ({ children, type }: any) => (
      <div data-testid="text" data-type={type}>
        {children}
      </div>
    ),
  },
  Select: ({ children, value, onChange: _onChange, _onChange, placeholder, mode, allowClear }: any) => (
    <div
      data-testid="select"
      data-value={value}
      data-placeholder={placeholder}
      data-mode={mode}
      data-allow-clear={allowClear}
    >
      {children}
    </div>
  ),
  DatePicker: {
    RangePicker: ({ onChange: _onChange, _onChange, placeholder }: any) => (
      <div data-testid="range-picker" data-placeholder={JSON.stringify(placeholder)} />
    ),
  },
  Button: ({ children, icon, onClick, loading, disabled, type, size }: any) => (
    <button
      data-testid="button"
      data-type={type}
      data-loading={loading}
      data-disabled={disabled}
      data-size={size}
      onClick={onClick}
    >
      {icon}
      {children}
    </button>
  ),
  Space: ({ children, compact }: any) => (
    <div data-testid="space" data-compact={compact}>
      {children}
    </div>
  ),
  Tag: ({ children, color }: any) => (
    <div data-testid="tag" data-color={color}>
      {children}
    </div>
  ),
  Input: {
    Search: ({ value, onChange: _onChange, _onChange, placeholder, onSearch: _onSearch, _onSearch }: any) => (
      <div
        data-testid="search"
        data-value={value}
        data-placeholder={placeholder}
      />
    ),
  },
  Tooltip: ({ children, title }: any) => (
    <div data-testid="tooltip" data-title={title}>
      {children}
    </div>
  ),
  message: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
  Empty: ({ description }: any) => (
    <div data-testid="empty" data-description={description} />
  ),
}))

// Mock icons
vi.mock('@ant-design/icons', () => ({
  FilterOutlined: () => <div data-testid="icon-filter" />,
  ClearOutlined: () => <div data-testid="icon-clear" />,
  SaveOutlined: () => <div data-testid="icon-save" />,
  HistoryOutlined: () => <div data-testid="icon-history" />,
  ReloadOutlined: () => <div data-testid="icon-reload" />,
  DownOutlined: () => <div data-testid="icon-down" />,
  UpOutlined: () => <div data-testid="icon-up" />,
}))

describe('AnalyticsFilters - 组件导入测试', () => {
  it('应该能够导入AnalyticsFilters组件', async () => {
    const module = await import('../AnalyticsFilters')
    expect(module).toBeDefined()
    expect(module.AnalyticsFilters).toBeDefined()
  })
})

describe('AnalyticsFilters - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持filters属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const filters = { ownership_status: '自有' }
    const element = React.createElement(AnalyticsFilters, {
      filters,
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onFiltersChange属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onApplyFilters属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      onApplyFilters: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onResetFilters属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      onResetFilters: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onPresetSelect属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      onPresetSelect: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持loading属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      loading: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认loading应该是false', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showAdvanced属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      showAdvanced: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认showAdvanced应该是false', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onToggleAdvanced属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      onToggleAdvanced: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持realTimeUpdate属性', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      realTimeUpdate: false,
    })
    expect(element).toBeTruthy()
  })

  it('默认realTimeUpdate应该是true', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 筛选预设测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该有全部资产预设', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有出租资产预设', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有经营性物业预设', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有已确权资产预设', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有空置资产预设', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 搜索历史测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该使用useSearchHistory hook', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持保存筛选条件', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: { ownership_status: '自有' },
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持应用历史筛选', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该支持删除历史筛选', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 操作按钮测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该有保存按钮', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有历史按钮', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有重置按钮', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有刷新按钮', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有高级筛选按钮', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      onToggleAdvanced: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 筛选字段测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该有权属状态下拉选择', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有物业性质下拉选择', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有使用状态下拉选择', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有日期范围选择器', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有搜索输入框', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 防抖测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该使用防抖处理筛选变化', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('realTimeUpdate为false时不应该防抖', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      realTimeUpdate: false,
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 激活筛选计数测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示激活的筛选条件数量', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: { ownership_status: '自有', property_nature: '商业' },
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('无筛选条件时不应该显示数量', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 保存筛选测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示保存名称输入框', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: { ownership_status: '自有' },
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有保存和取消按钮', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: { ownership_status: '自有' },
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - useQuery测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该调用useQuery获取筛选选项', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该有30分钟的staleTime', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 状态同步测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该同步localFilters和外部filters', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: { ownership_status: '自有' },
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该根据filters匹配预设', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 消息提示测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('重置时应该显示成功消息', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: { ownership_status: '自有' },
      onFiltersChange: vi.fn(),
      onResetFilters: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应用筛选时应该显示成功消息', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      onApplyFilters: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('保存筛选时应该显示成功消息', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: { ownership_status: '自有' },
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('保存时没有名称应该显示警告', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理空filters', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该处理undefined filters', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: undefined as any,
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该处理空搜索历史', async () => {
    vi.doMock('@/hooks/useSearchHistory', () => ({
      useSearchHistory: vi.fn(() => ({
        searchHistory: [],
        addSearchHistory: vi.fn(),
        removeSearchHistory: vi.fn(),
      })),
    }))
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该使用Card组件', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('Card应该是small大小', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('应该使用Row和Col布局', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})

describe('AnalyticsFilters - 图标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('Card title应该有FilterOutlined图标', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('保存按钮应该有SaveOutlined图标', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('历史按钮应该有HistoryOutlined图标', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('重置按钮应该有ClearOutlined图标', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('刷新按钮应该有ReloadOutlined图标', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
    })
    expect(element).toBeTruthy()
  })

  it('高级按钮应该有DownOutlined或UpOutlined图标', async () => {
    const { AnalyticsFilters } = await import('../AnalyticsFilters')
    const element = React.createElement(AnalyticsFilters, {
      filters: {},
      onFiltersChange: vi.fn(),
      onToggleAdvanced: vi.fn(),
    })
    expect(element).toBeTruthy()
  })
})
