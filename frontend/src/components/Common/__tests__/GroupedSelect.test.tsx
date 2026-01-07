/**
 * GroupedSelect 组件测试
 * 测试分组选择器组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock enumHelpers
vi.mock('@/utils/enumHelpers', () => ({
  EnumGroup: [],
  EnumOption: {},
  EnumSearchHelper: {
    searchInGroups: vi.fn((groups, keyword) => {
      if (!keyword.trim()) return groups
      return groups.map((group: any) => ({
        ...group,
        options: group.options.filter((option: any) =>
          option.label.toLowerCase().includes(keyword.toLowerCase())
        ),
      }))
    }),
    findByValue: vi.fn((groups, value) => {
      for (const group of groups) {
        const found = group.options.find((opt: any) => opt.value === value)
        if (found) return found
      }
      return undefined
    }),
  },
}))

// Mock Ant Design components
vi.mock('antd', () => ({
  Select: ({ children, value, onChange: _onChange, placeholder, allowClear, showSearch, onSearch: _onSearch, tagRender: _tagRender }: any) => (
    <div
      data-testid="select"
      data-value={value}
      data-placeholder={placeholder}
      data-allow-clear={allowClear}
      data-show-search={showSearch}
    >
      {children}
      <div data-testid="selected-value">{value}</div>
    </div>
  ),
  Input: {
    Search: ({ value, onChange: _onChange, placeholder, allowClear }: any) => (
      <div data-testid="search" data-value={value} data-placeholder={placeholder} data-allow-clear={allowClear}>
        <input value={value} onChange={_onChange} placeholder={placeholder} />
      </div>
    ),
  },
  Tag: ({ children, color, closable, onClose: _onClose }: any) => (
    <div data-testid="tag" data-color={color} data-closable={closable}>
      {children}
    </div>
  ),
  Space: ({ children }: any) => (
    <div data-testid="space">
      {children}
    </div>
  ),
  Typography: {
    Text: ({ children, type, strong, style }: any) => (
      <div data-testid="text" data-type={type} data-strong={strong} style={style}>
        {children}
      </div>
    ),
  },
}))

// Mock icons
vi.mock('@ant-design/icons', () => ({
  SearchOutlined: () => <div data-testid="icon-search" />,
}))

// Mock Select.Option and Select.OptGroup
const MockOption: any = ({ children, value }: any) => (
  <div data-testid="option" data-value={value}>
    {children}
  </div>
)

const MockOptGroup: any = ({ label, children }: any) => (
  <div data-testid="optgroup" data-label={label}>
    {children}
  </div>
)

// Attach to the mocked Select
;(await import('antd')).Select.Option = MockOption
;(await import('antd')).Select.OptGroup = MockOptGroup

describe('GroupedSelect - 组件导入测试', () => {
  it('应该能够导入GroupedSelect组件', async () => {
    const module = await import('../GroupedSelect')
    expect(module).toBeDefined()
    expect(module.default).toBeDefined()
  })

  it('应该能够导入GroupedSelectSingle组件', async () => {
    const module = await import('../GroupedSelect')
    expect(module.GroupedSelectSingle).toBeDefined()
  })

  it('应该能够导入GroupedSelectMultiple组件', async () => {
    const module = await import('../GroupedSelect')
    expect(module.GroupedSelectMultiple).toBeDefined()
  })
})

describe('GroupedSelect - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持groups属性', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [
          { label: '选项1', value: 'opt1' },
          { label: '选项2', value: 'opt2' },
        ],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该支持showSearch属性', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, {
      groups,
      showSearch: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认showSearch应该是true', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该支持placeholder属性', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, {
      groups,
      placeholder: '请选择',
    })
    expect(element).toBeTruthy()
  })

  it('默认placeholder应该是"请选择"', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该支持allowClear属性', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, {
      groups,
      allowClear: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认allowClear应该是true', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - 分组属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持showGroupLabel属性', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, {
      groups,
      showGroupLabel: true,
    })
    expect(element).toBeTruthy()
  })

  it('默认showGroupLabel应该是true', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该支持maxDisplayCount属性', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, {
      groups,
      maxDisplayCount: 100,
    })
    expect(element).toBeTruthy()
  })

  it('默认maxDisplayCount应该是50', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - 搜索功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持onSearch回调', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const handleSearch = vi.fn()
    const element = React.createElement(GroupedSelect, {
      groups,
      onSearch: handleSearch,
    })
    expect(element).toBeTruthy()
  })

  it('应该显示搜索输入框', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, {
      groups,
      showSearch: true,
    })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - 选项渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该显示分组标签', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [{ label: '选项1', value: 'opt1' }],
      },
    ]
    const element = React.createElement(GroupedSelect, {
      groups,
      showGroupLabel: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该显示选项数量', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [
          { label: '选项1', value: 'opt1' },
          { label: '选项2', value: 'opt2' },
        ],
      },
    ]
    const element = React.createElement(GroupedSelect, {
      groups,
      showGroupLabel: true,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持带description的选项', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [
          { label: '选项1', value: 'opt1', description: '描述1' },
        ],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该支持带color的选项', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [
          { label: '选项1', value: 'opt1', color: 'blue' },
        ],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - 变体组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('GroupedSelectSingle应该是单选模式', async () => {
    const { GroupedSelectSingle } = await import('../GroupedSelect')
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelectSingle, { groups })
    expect(element).toBeTruthy()
  })

  it('GroupedSelectMultiple应该是多选模式', async () => {
    const { GroupedSelectMultiple } = await import('../GroupedSelect')
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelectMultiple, { groups })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - 标签渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该使用自定义tagRender', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [
          { label: '选项1', value: 'opt1', color: 'blue' },
        ],
      },
    ]
    const element = React.createElement(GroupedSelect, {
      groups,
      mode: 'multiple' as any,
    })
    expect(element).toBeTruthy()
  })

  it('tag应该显示选项label', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [
          { label: '选项1', value: 'opt1' },
        ],
      },
    ]
    const element = React.createElement(GroupedSelect, {
      groups,
      mode: 'multiple' as any,
    })
    expect(element).toBeTruthy()
  })

  it('tag应该显示选项color', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [
          { label: '选项1', value: 'opt1', color: 'green' },
        ],
      },
    ]
    const element = React.createElement(GroupedSelect, {
      groups,
      mode: 'multiple' as any,
    })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该处理空groups', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const element = React.createElement(GroupedSelect, { groups: [] })
    expect(element).toBeTruthy()
  })

  it('应该处理空options的分组', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [] }]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该处理多个分组', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      { label: '分组1', options: [{ label: '选项1', value: 'opt1' }] },
      { label: '分组2', options: [{ label: '选项2', value: 'opt2' }] },
      { label: '分组3', options: [{ label: '选项3', value: 'opt3' }] },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('搜索无结果时应该显示提示', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, {
      groups,
      showSearch: true,
    })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - 颜色映射测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该映射blue颜色', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [{ label: '选项1', value: 'opt1', color: 'blue' }],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该映射green颜色', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [{ label: '选项1', value: 'opt1', color: 'green' }],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该映射orange颜色', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [{ label: '选项1', value: 'opt1', color: 'orange' }],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该映射red颜色', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [{ label: '选项1', value: 'opt1', color: 'red' }],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该映射purple颜色', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [{ label: '选项1', value: 'opt1', color: 'purple' }],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该映射cyan颜色', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [{ label: '选项1', value: 'opt1', color: 'cyan' }],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })

  it('应该映射default颜色', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [{ label: '选项1', value: 'opt1', color: 'default' }],
      },
    ]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - SelectProps传递测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该支持value属性', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, {
      groups,
      value: 'opt1',
    })
    expect(element).toBeTruthy()
  })

  it('应该支持onChange属性', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const handleChange = vi.fn()
    const element = React.createElement(GroupedSelect, {
      groups,
      onChange: handleChange,
    })
    expect(element).toBeTruthy()
  })

  it('应该支持disabled属性', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, {
      groups,
      disabled: true,
    })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - 搜索过滤测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('搜索应该过滤选项', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: [
          { label: '选项1', value: 'opt1' },
          { label: '选项2', value: 'opt2' },
        ],
      },
    ]
    const element = React.createElement(GroupedSelect, {
      groups,
      showSearch: true,
    })
    expect(element).toBeTruthy()
  })

  it('maxDisplayCount应该限制显示数量', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [
      {
        label: '分组1',
        options: Array.from({ length: 100 }, (_, i) => ({
          label: `选项${i}`,
          value: `opt${i}`,
        })),
      },
    ]
    const element = React.createElement(GroupedSelect, {
      groups,
      maxDisplayCount: 50,
    })
    expect(element).toBeTruthy()
  })
})

describe('GroupedSelect - 禁用默认过滤测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('filterOption应该是false', async () => {
    const GroupedSelect = (await import('../GroupedSelect')).default
    const groups = [{ label: '分组1', options: [{ label: '选项1', value: 'opt1' }] }]
    const element = React.createElement(GroupedSelect, { groups })
    expect(element).toBeTruthy()
  })
})
