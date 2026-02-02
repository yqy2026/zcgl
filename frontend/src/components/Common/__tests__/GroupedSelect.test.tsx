/**
 * GroupedSelect 组件测试
 * 测试分组选择器组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';
import type { EnumGroup, EnumOption } from '@/utils/enumHelpers';
import GroupedSelect, { GroupedSelectMultiple, GroupedSelectSingle } from '../GroupedSelect';

// Mock enumHelpers
vi.mock('@/utils/enumHelpers', () => ({
  EnumGroup: [],
  EnumOption: {},
  EnumSearchHelper: {
    searchInGroups: vi.fn((groups: EnumGroup[], keyword: string) => {
      if (!keyword.trim()) return groups;
      return groups.map((group: EnumGroup) => ({
        ...group,
        options: group.options.filter((option: EnumOption) =>
          option.label.toLowerCase().includes(keyword.toLowerCase())
        ),
      }));
    }),
    findByValue: vi.fn((groups: EnumGroup[], value: string) => {
      for (const group of groups) {
        const found = group.options.find((opt: EnumOption) => opt.value === value);
        if (found) return found;
      }
      return undefined;
    }),
  },
}));

// Mock Ant Design components
interface SelectMockProps {
  children?: React.ReactNode;
  value?: string | string[];
  onChange?: (value: string | string[]) => void;
  placeholder?: string;
  allowClear?: boolean;
  showSearch?: boolean;
  onSearch?: (value: string) => void;
  filterOption?: boolean;
  popupRender?: (menu: React.ReactElement) => React.ReactElement;
  mode?: string;
}

interface InputSearchMockProps {
  value?: string;
  onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  allowClear?: boolean;
}

interface TagMockProps {
  children?: React.ReactNode;
  color?: string;
  closable?: boolean;
  onClose?: () => void;
}

interface SpaceMockProps {
  children?: React.ReactNode;
}

interface TypographyTextMockProps {
  children?: React.ReactNode;
  type?: string;
  strong?: boolean;
  style?: React.CSSProperties;
}

interface OptionMockProps {
  children?: React.ReactNode;
  value?: string;
}

interface OptGroupMockProps {
  label?: React.ReactNode;
  children?: React.ReactNode;
}

vi.mock('antd', () => {
  const MockOption = ({ children, value }: OptionMockProps) => (
    <div data-testid="option" data-value={value}>
      {children}
    </div>
  );

  const MockOptGroup = ({ label, children }: OptGroupMockProps) => (
    <div data-testid="optgroup">
      <div data-testid="optgroup-label">{label}</div>
      {children}
    </div>
  );

  const Select = ({
    children,
    placeholder,
    allowClear,
    showSearch,
    filterOption,
    popupRender,
    mode,
  }: SelectMockProps) => (
    <div
      data-testid="select"
      data-placeholder={placeholder}
      data-allow-clear={allowClear}
      data-show-search={showSearch}
      data-filter-option={String(filterOption)}
      data-mode={mode}
    >
      {popupRender ? (
        <div data-testid="select-popup">{popupRender(<div data-testid="select-menu" />)}</div>
      ) : null}
      {children}
    </div>
  );

  Select.Option = MockOption;
  Select.OptGroup = MockOptGroup;

  return {
    Select,
    Input: {
      Search: ({ value, onChange, placeholder, allowClear }: InputSearchMockProps) => (
        <div data-testid="search">
          <input
            data-testid="search-input"
            value={value}
            onChange={onChange}
            placeholder={placeholder}
          />
          <span data-testid="search-allow-clear">{String(allowClear)}</span>
        </div>
      ),
    },
    Tag: ({ children, color, closable }: TagMockProps) => (
      <div data-testid="tag" data-color={color} data-closable={closable}>
        {children}
      </div>
    ),
    Space: ({ children }: SpaceMockProps) => <div data-testid="space">{children}</div>,
    Typography: {
      Text: ({ children, type, strong, style }: TypographyTextMockProps) => (
        <span data-testid="text" data-type={type} data-strong={strong} style={style}>
          {children}
        </span>
      ),
    },
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  SearchOutlined: () => <div data-testid="icon-search" />,
}));

const groups: EnumGroup[] = [
  {
    label: '分组1',
    options: [
      { label: '选项1', value: 'opt1' },
      { label: '选项2', value: 'opt2' },
    ],
  },
  {
    label: '分组2',
    options: [{ label: '选项3', value: 'opt3', description: '描述3', color: 'blue' }],
  },
];

describe('GroupedSelect - 组件导入测试', () => {
  it('应该能够导入GroupedSelect组件', () => {
    expect(GroupedSelect).toBeDefined();
  });

  it('应该能够导出变体组件', () => {
    expect(GroupedSelectSingle).toBeDefined();
    expect(GroupedSelectMultiple).toBeDefined();
  });
});

describe('GroupedSelect - 渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该渲染分组标签与选项', () => {
    renderWithProviders(<GroupedSelect groups={groups} />);

    expect(screen.getByText('分组1')).toBeInTheDocument();
    expect(screen.getByText('(2)')).toBeInTheDocument();
    expect(screen.getByText('分组2')).toBeInTheDocument();
    expect(screen.getByText('(1)')).toBeInTheDocument();
    expect(screen.getAllByTestId('option')).toHaveLength(3);
    expect(screen.getByTestId('select')).toHaveAttribute('data-filter-option', 'false');
  });

  it('showGroupLabel为false时不渲染分组标签', () => {
    renderWithProviders(<GroupedSelect groups={groups} showGroupLabel={false} />);

    expect(screen.queryByTestId('optgroup')).not.toBeInTheDocument();
    expect(screen.getAllByTestId('option')).toHaveLength(3);
  });
});

describe('GroupedSelect - 搜索测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('搜索关键字应过滤选项', () => {
    renderWithProviders(<GroupedSelect groups={groups} />);
    expect(screen.getAllByTestId('option')).toHaveLength(3);

    fireEvent.change(screen.getByTestId('search-input'), { target: { value: '选项2' } });
    const options = screen.getAllByTestId('option');
    expect(options).toHaveLength(1);
    expect(options[0].getAttribute('data-value')).toBe('opt2');
  });

  it('搜索无结果时显示提示', async () => {
    renderWithProviders(<GroupedSelect groups={groups} />);

    fireEvent.change(screen.getByTestId('search-input'), { target: { value: '不存在' } });
    expect(await screen.findByText('未找到匹配的选项')).toBeInTheDocument();
  });
});
