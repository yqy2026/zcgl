/**
 * LoadingSpinner 组件测试
 * 覆盖默认渲染、提示文本、子内容与样式透传
 */

import { describe, it, expect, vi } from 'vitest';
import { screen } from '@/test/utils/test-helpers';
import type { CSSProperties, ReactNode } from 'react';

import LoadingSpinner from '../LoadingSpinner';

interface SpinMockProps {
  spinning?: boolean;
  tip?: string;
  size?: 'small' | 'default' | 'large';
  children?: ReactNode;
  delay?: number;
  style?: CSSProperties;
  className?: string;
}

interface TextMockProps {
  children?: ReactNode;
  type?: string;
  style?: CSSProperties;
}

vi.mock('antd', () => ({
  Spin: ({ spinning, tip, size, children, delay, style, className }: SpinMockProps) => (
    <div
      data-testid="spin"
      data-spin={spinning}
      data-size={size}
      data-delay={delay}
      data-tip={tip}
      className={className}
      style={style}
    >
      {children}
    </div>
  ),
  Typography: {
    Text: ({ children, type, style }: TextMockProps) => (
      <span data-testid="text" data-type={type} style={style}>
        {children}
      </span>
    ),
  },
}));

vi.mock('@ant-design/icons', () => ({
  LoadingOutlined: ({ spin, style }: { spin?: boolean; style?: CSSProperties }) => (
    <div data-testid="loading-icon" data-spin={spin} style={style} />
  ),
}));

describe('LoadingSpinner', () => {
  it('renders default spinner without tip', () => {
    renderWithProviders(<LoadingSpinner />);

    const spin = screen.getByTestId('spin');
    expect(spin).toHaveAttribute('data-size', 'default');
    expect(spin).toHaveAttribute('data-spin', 'true');
    expect(screen.queryByTestId('text')).toBeNull();
  });

  it.each([
    ['small', 'small'],
    ['large', 'large'],
  ])('renders size %s', (_label, size) => {
    renderWithProviders(<LoadingSpinner size={size as 'small' | 'large'} />);

    expect(screen.getByTestId('spin')).toHaveAttribute('data-size', size);
  });

  it('renders tip text when provided (no children)', () => {
    renderWithProviders(<LoadingSpinner tip="加载中..." />);

    expect(screen.getByTestId('text')).toHaveTextContent('加载中...');
    expect(screen.getByTestId('spin').getAttribute('data-tip')).toBeNull();
  });

  it('wraps children and passes tip to Spin when children provided', () => {
    renderWithProviders(
      <LoadingSpinner tip="处理" spinning={false}>
        <div data-testid="child">Content</div>
      </LoadingSpinner>
    );

    const spin = screen.getByTestId('spin');
    expect(spin).toHaveAttribute('data-spin', 'false');
    expect(spin).toHaveAttribute('data-tip', '处理');
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('passes delay to Spin', () => {
    renderWithProviders(<LoadingSpinner delay={300} />);

    expect(screen.getByTestId('spin')).toHaveAttribute('data-delay', '300');
  });

  it('applies wrapper className and style when no children', () => {
    const { container } = renderWithProviders(
      <LoadingSpinner className="custom-spinner" style={{ margin: 20 }} />
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('custom-spinner');
    expect(wrapper).toHaveStyle({ margin: '20px' });
  });

  it('applies className to Spin when children provided', () => {
    renderWithProviders(
      <LoadingSpinner className="custom-spin" spinning>
        <div>Child</div>
      </LoadingSpinner>
    );

    expect(screen.getByTestId('spin')).toHaveClass('custom-spin');
  });

  it('handles null children gracefully', () => {
    renderWithProviders(<LoadingSpinner spinning={false}>{null}</LoadingSpinner>);

    const spin = screen.getByTestId('spin');
    expect(spin).toHaveAttribute('data-spin', 'false');
  });
});
