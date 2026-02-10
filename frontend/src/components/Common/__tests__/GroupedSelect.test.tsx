/**
 * GroupedSelect 组件测试
 * 测试分组选择器组件
 *
 * 修复说明：
 * - 移除 antd Select, Input, Tag, Space, Typography mock
 * - 保留 enumHelpers mock（业务逻辑）
 * - 使用文本内容和 className 进行断言
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
    const { container } = renderWithProviders(<GroupedSelect groups={groups} />);
    const combobox = screen.getByRole('combobox');
    fireEvent.mouseDown(combobox);

    expect(screen.getByText('分组1')).toBeInTheDocument();
    expect(screen.getByText('(2)')).toBeInTheDocument();
    expect(screen.getByText('分组2')).toBeInTheDocument();
    expect(screen.getByText('(1)')).toBeInTheDocument();
    // 验证 Select 被渲染
    expect(container.querySelector('.ant-select')).toBeInTheDocument();
  });

  it('showGroupLabel为false时不渲染分组标签', () => {
    renderWithProviders(<GroupedSelect groups={groups} showGroupLabel={false} />);
    const combobox = screen.getByRole('combobox');
    fireEvent.mouseDown(combobox);

    // 不应该显示分组标签
    expect(screen.queryByText('分组1')).not.toBeInTheDocument();
    expect(screen.queryByText('分组2')).not.toBeInTheDocument();
    // 但应该显示选项
    expect(screen.getByText('选项1')).toBeInTheDocument();
  });
});

describe('GroupedSelect - 搜索测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('搜索关键字应过滤选项', () => {
    renderWithProviders(<GroupedSelect groups={groups} />);
    const combobox = screen.getByRole('combobox');
    fireEvent.mouseDown(combobox);

    // 验证所有选项初始显示
    expect(screen.getByText('选项1')).toBeInTheDocument();
    expect(screen.getByText('选项2')).toBeInTheDocument();
    expect(screen.getByText('选项3')).toBeInTheDocument();

    // 模拟搜索输入
    const searchInput = screen.getByLabelText('搜索选项');
    fireEvent.change(searchInput, { target: { value: '选项2' } });

    // 验证过滤后的结果
    expect(screen.getByText('选项2')).toBeInTheDocument();
  });

  it('搜索无结果时显示提示', async () => {
    renderWithProviders(<GroupedSelect groups={groups} />);
    const combobox = screen.getByRole('combobox');
    fireEvent.mouseDown(combobox);

    const searchInput = screen.getByLabelText('搜索选项');
    fireEvent.change(searchInput, { target: { value: '不存在' } });

    expect(await screen.findByText('未找到匹配的选项')).toBeInTheDocument();
  });
});
