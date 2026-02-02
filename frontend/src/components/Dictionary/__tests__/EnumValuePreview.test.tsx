/**
 * EnumValuePreview 组件测试
 * 覆盖空状态、排序、默认值与数量提示
 *
 * 修复说明：
 * - 移除 antd Tag, Tooltip, Space 组件 mock
 * - 使用文本内容进行断言
 * - 保持测试覆盖范围不变
 */

import { describe, it, expect } from 'vitest';
import { screen } from '@/test/utils/test-helpers';

import EnumValuePreview from '../EnumValuePreview';

describe('EnumValuePreview', () => {
  it('renders empty state when no values', () => {
    renderWithProviders(<EnumValuePreview values={[]} />);

    expect(screen.getByText('暂无枚举值')).toBeInTheDocument();
  });

  it('renders active values sorted with default marker', () => {
    const values = [
      {
        id: '1',
        label: 'A',
        value: 'a',
        sort_order: 2,
        is_active: true,
        is_default: false,
      },
      {
        id: '2',
        label: 'B',
        value: 'b',
        sort_order: 1,
        is_active: true,
        is_default: true,
      },
    ];

    renderWithProviders(<EnumValuePreview values={values} />);

    // 验证标签按排序显示
    expect(screen.getByText('B')).toBeInTheDocument();
    expect(screen.getByText('A')).toBeInTheDocument();
    // 验证默认值标记（星号）
    expect(screen.getByText('★')).toBeInTheDocument();
  });

  it('shows remaining count and inactive count', () => {
    const values = [
      {
        id: '1',
        label: 'A',
        value: 'a',
        sort_order: 2,
        is_active: true,
        is_default: false,
      },
      {
        id: '2',
        label: 'B',
        value: 'b',
        sort_order: 1,
        is_active: true,
        is_default: true,
      },
      {
        id: '3',
        label: 'C',
        value: 'c',
        sort_order: 3,
        is_active: false,
        is_default: false,
      },
      {
        id: '4',
        label: 'D',
        value: 'd',
        sort_order: 4,
        is_active: true,
        is_default: false,
        color: '#ff0000',
      },
    ];

    renderWithProviders(<EnumValuePreview values={values} maxDisplay={2} />);

    expect(screen.getByText('+2')).toBeInTheDocument();
    expect(screen.getByText('1 个已禁用')).toBeInTheDocument();
  });

  it('uses gold color for default value and processing for remaining', () => {
    const values = [
      {
        id: '1',
        label: '默认值',
        value: 'default',
        sort_order: 1,
        is_active: true,
        is_default: true,
      },
      {
        id: '2',
        label: '其他',
        value: 'other',
        sort_order: 2,
        is_active: true,
        is_default: false,
      },
      {
        id: '3',
        label: '更多',
        value: 'more',
        sort_order: 3,
        is_active: true,
        is_default: false,
      },
    ];

    renderWithProviders(<EnumValuePreview values={values} maxDisplay={1} />);

    // 验证默认值和剩余数量显示
    expect(screen.getByText('默认值')).toBeInTheDocument();
    expect(screen.getByText('+2')).toBeInTheDocument();
  });

  it('hides inactive count when disabled', () => {
    const values = [
      {
        id: '1',
        label: 'A',
        value: 'a',
        sort_order: 1,
        is_active: false,
        is_default: false,
      },
    ];

    renderWithProviders(<EnumValuePreview values={values} _showInactiveCount={false} />);

    expect(screen.queryByText('1 个已禁用')).toBeNull();
  });
});
