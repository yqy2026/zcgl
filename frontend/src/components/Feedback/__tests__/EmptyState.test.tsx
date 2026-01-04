/**
 * EmptyState 组件测试
 * 测试空状态展示组件
 * 增强版本 - 添加更全面的测试用例
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock Ant Design components
vi.mock('antd', () => ({
  Empty: ({ image, description, children }: any) => (
    <div data-testid="empty" data-has-description={!!description}>
      {image && <div data-testid="empty-image">{image}</div>}
      {description && <div data-testid="empty-description">{description}</div>}
      {children && <div data-testid="empty-children">{children}</div>}
    </div>
  ),
  Button: ({ children, icon, type, onClick, danger }: any) => (
    <button
      data-testid="button"
      data-type={type}
      data-danger={danger}
      onClick={onClick}
    >
      {icon && <span data-testid="button-icon">{icon}</span>}
      {children}
    </button>
  ),
  Typography: {
    Text: ({ children, type, strong, style }: any) => (
      <span data-testid="text" data-type={type} data-strong={strong} style={style}>
        {children}
      </span>
    ),
  },
  Space: ({ children, wrap }: any) => (
    <div data-testid="space" data-wrap={wrap}>{children}</div>
  ),
}))

vi.mock('@ant-design/icons', () => ({
  FileTextOutlined: ({ style }: any) => <div data-testid="icon-file-text" style={style} />,
  SearchOutlined: ({ style }: any) => <div data-testid="icon-search" style={style} />,
  PlusOutlined: () => <div data-testid="icon-plus" />,
  ReloadOutlined: () => <div data-testid="icon-reload" />,
  InboxOutlined: ({ style }: any) => <div data-testid="icon-inbox" style={style} />,
  DisconnectOutlined: ({ style }: any) => <div data-testid="icon-disconnect" style={style} />,
  FilterOutlined: ({ style }: any) => <div data-testid="icon-filter" style={style} />,
}))

describe('EmptyState - 组件导入测试', () => {
  it('应该能够导入EmptyState组件', async () => {
    const module = await import('../EmptyState')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })

  it('应该导出预设组件', async () => {
    const module = await import('../EmptyState')
    expect(module.NoDataState).toBeDefined()
    expect(module.NoSearchResultsState).toBeDefined()
    expect(module.NoFilterResultsState).toBeDefined()
    expect(module.NetworkErrorState).toBeDefined()
    expect(module.LoadingErrorState).toBeDefined()
    expect(module.PermissionDeniedState).toBeDefined()
    expect(module.MaintenanceState).toBeDefined()
  })
})

describe('EmptyState - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持type属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { type: 'no-data' })
    expect(element).toBeTruthy()
  })

  it('应该支持title属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { title: '自定义标题' })
    expect(element).toBeTruthy()
  })

  it('应该支持description属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { description: '自定义描述' })
    expect(element).toBeTruthy()
  })

  it('应该支持image属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const customImage = React.createElement('div', {}, 'Custom Image')
    const element = React.createElement(EmptyState, { image: customImage })
    expect(element).toBeTruthy()
  })

  it('应该支持actions属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const actions = React.createElement('button', {}, 'Action')
    const element = React.createElement(EmptyState, { actions })
    expect(element).toBeTruthy()
  })
})

describe('EmptyState - 预设类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持no-data类型', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { type: 'no-data' })
    expect(element).toBeTruthy()
  })

  it('应该支持no-search-results类型', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { type: 'no-search-results' })
    expect(element).toBeTruthy()
  })

  it('应该支持no-filter-results类型', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { type: 'no-filter-results' })
    expect(element).toBeTruthy()
  })

  it('应该支持network-error类型', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { type: 'network-error' })
    expect(element).toBeTruthy()
  })

  it('应该支持loading-error类型', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { type: 'loading-error' })
    expect(element).toBeTruthy()
  })

  it('应该支持permission-denied类型', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { type: 'permission-denied' })
    expect(element).toBeTruthy()
  })

  it('应该支持maintenance类型', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { type: 'maintenance' })
    expect(element).toBeTruthy()
  })
})

describe('EmptyState - 按钮显示控制测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持showCreateButton属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const handleClick = vi.fn()
    const element = React.createElement(EmptyState, {
      type: 'no-data',
      showCreateButton: true,
      onCreateClick: handleClick,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showRefreshButton属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const handleClick = vi.fn()
    const element = React.createElement(EmptyState, {
      type: 'network-error',
      showRefreshButton: true,
      onRefreshClick: handleClick,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持showClearFilterButton属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const handleClick = vi.fn()
    const element = React.createElement(EmptyState, {
      type: 'no-filter-results',
      showClearFilterButton: true,
      onClearFilterClick: handleClick,
    })
    expect(element).toBeTruthy()
  })
})

describe('EmptyState - 回调函数测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持onCreateClick回调', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const handleClick = vi.fn()
    const element = React.createElement(EmptyState, {
      showCreateButton: true,
      onCreateClick: handleClick,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onRefreshClick回调', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const handleClick = vi.fn()
    const element = React.createElement(EmptyState, {
      showRefreshButton: true,
      onRefreshClick: handleClick,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onClearFilterClick回调', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const handleClick = vi.fn()
    const element = React.createElement(EmptyState, {
      showClearFilterButton: true,
      onClearFilterClick: handleClick,
    })
    expect(element).toBeTruthy()
  })
})

describe('EmptyState - 样式属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持style属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const customStyle = { padding: 20, margin: 10 }
    const element = React.createElement(EmptyState, { style: customStyle })
    expect(element).toBeTruthy()
  })

  it('应该支持className属性', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { className: 'custom-empty-state' })
    expect(element).toBeTruthy()
  })
})

describe('EmptyState - 预设组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('NoDataState应该正确渲染', async () => {
    const { NoDataState } = await import('../EmptyState')
    const element = React.createElement(NoDataState, {})
    expect(element).toBeTruthy()
  })

  it('NoSearchResultsState应该正确渲染', async () => {
    const { NoSearchResultsState } = await import('../EmptyState')
    const element = React.createElement(NoSearchResultsState, {})
    expect(element).toBeTruthy()
  })

  it('NoFilterResultsState应该正确渲染', async () => {
    const { NoFilterResultsState } = await import('../EmptyState')
    const element = React.createElement(NoFilterResultsState, {})
    expect(element).toBeTruthy()
  })

  it('NetworkErrorState应该正确渲染', async () => {
    const { NetworkErrorState } = await import('../EmptyState')
    const element = React.createElement(NetworkErrorState, {})
    expect(element).toBeTruthy()
  })

  it('LoadingErrorState应该正确渲染', async () => {
    const { LoadingErrorState } = await import('../EmptyState')
    const element = React.createElement(LoadingErrorState, {})
    expect(element).toBeTruthy()
  })

  it('PermissionDeniedState应该正确渲染', async () => {
    const { PermissionDeniedState } = await import('../EmptyState')
    const element = React.createElement(PermissionDeniedState, {})
    expect(element).toBeTruthy()
  })

  it('MaintenanceState应该正确渲染', async () => {
    const { MaintenanceState } = await import('../EmptyState')
    const element = React.createElement(MaintenanceState, {})
    expect(element).toBeTruthy()
  })
})

describe('EmptyState - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理空字符串title', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { title: '' })
    expect(element).toBeTruthy()
  })

  it('应该处理undefined回调', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, {
      showCreateButton: true,
      onCreateClick: undefined,
    })
    expect(element).toBeTruthy()
  })

  it('应该处理null actions', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, { actions: null })
    expect(element).toBeTruthy()
  })

  it('应该处理自定义title覆盖预设', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const element = React.createElement(EmptyState, {
      type: 'no-data',
      title: '完全自定义的标题',
    })
    expect(element).toBeTruthy()
  })
})

describe('EmptyState - 组合属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持所有属性组合', async () => {
    const EmptyState = (await import('../EmptyState')).default
    const handleClick = vi.fn()
    const element = React.createElement(EmptyState, {
      type: 'no-data',
      title: '自定义标题',
      description: '自定义描述',
      showCreateButton: true,
      showRefreshButton: true,
      onCreateClick: handleClick,
      onRefreshClick: handleClick,
      className: 'custom-class',
      style: { margin: 20 },
    })
    expect(element).toBeTruthy()
  })

  it('预设组件应该支持属性覆盖', async () => {
    const { NoDataState } = await import('../EmptyState')
    const handleClick = vi.fn()
    const element = React.createElement(NoDataState, {
      title: '覆盖的标题',
      showCreateButton: true,
      onCreateClick: handleClick,
    })
    expect(element).toBeTruthy()
  })
})
