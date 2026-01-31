/**
 * EnumValuePreview 组件测试
 * 覆盖空状态、排序、默认值与数量提示
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { CSSProperties, ReactNode } from 'react';

import EnumValuePreview from '../EnumValuePreview';

interface TagMockProps {
  children?: ReactNode;
  color?: string;
  style?: CSSProperties;
}

interface TooltipMockProps {
  children: ReactNode;
  title?: ReactNode;
}

interface SpaceMockProps {
  children?: ReactNode;
}

vi.mock('antd', () => ({
  Tag: ({ children, color, style }: TagMockProps) => (
    <span data-testid="tag" data-color={color} style={style}>
      {children}
    </span>
  ),
  Tooltip: ({ children, title }: TooltipMockProps) => (
    <div data-testid="tooltip" data-has-title={title != null}>
      {children}
    </div>
  ),
  Space: ({ children }: SpaceMockProps) => <div data-testid="space">{children}</div>,
}));

describe('EnumValuePreview', () => {
  it('renders empty state when no values', () => {
    render(<EnumValuePreview values={[]} />);

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

    render(<EnumValuePreview values={values} />);

    const tags = screen.getAllByTestId('tag');
    expect(tags[0]).toHaveTextContent('B');
    expect(tags[0]).toHaveTextContent('★');
    expect(tags[1]).toHaveTextContent('A');
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

    render(<EnumValuePreview values={values} maxDisplay={2} />);

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

    render(<EnumValuePreview values={values} maxDisplay={1} />);

    const tags = screen.getAllByTestId('tag');
    const defaultTag = tags.find(tag => tag.textContent?.includes('默认值'));
    const remainingTag = tags.find(tag => tag.textContent?.includes('+2'));

    expect(defaultTag).toBeDefined();
    expect(defaultTag).toHaveAttribute('data-color', 'gold');
    expect(remainingTag).toHaveAttribute('data-color', 'processing');
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

    render(<EnumValuePreview values={values} _showInactiveCount={false} />);

    expect(screen.queryByText('1 个已禁用')).toBeNull();
  });
});
