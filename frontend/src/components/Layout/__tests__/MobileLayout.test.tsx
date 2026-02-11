/**
 * MobileLayout 组件测试
 * 覆盖头部、面包屑、内容与页脚渲染
 */

import { describe, it, expect, vi } from 'vitest';
import { screen } from '@/test/utils/test-helpers';
import type { CSSProperties, ReactNode } from 'react';

import MobileLayout from '../MobileLayout';
import styles from '../MobileLayout.module.css';

interface LayoutSectionMockProps {
  children?: ReactNode;
  style?: CSSProperties;
  className?: string;
}

interface ButtonMockProps {
  children?: ReactNode;
  icon?: ReactNode;
  type?: string;
  size?: number | string;
  style?: CSSProperties;
  className?: string;
}

interface SpaceMockProps {
  children?: ReactNode;
  size?: number | string;
  className?: string;
}

interface AvatarMockProps {
  children?: ReactNode;
  size?: number | string;
  icon?: ReactNode;
  style?: CSSProperties;
  className?: string;
}

interface TypographyTextMockProps {
  children?: ReactNode;
  strong?: boolean;
  type?: string;
  style?: CSSProperties;
  className?: string;
}

vi.mock('antd', () => {
  const MockLayout = Object.assign(
    ({ children, style, className }: LayoutSectionMockProps) => (
      <div data-testid="layout" style={style} className={className}>
        {children}
      </div>
    ),
    {
      Header: ({ children, style, className }: LayoutSectionMockProps) => (
        <div data-testid="header" style={style} className={className}>
          {children}
        </div>
      ),
      Content: ({ children, style, className }: LayoutSectionMockProps) => (
        <div data-testid="content" style={style} className={className}>
          {children}
        </div>
      ),
      Footer: ({ children, style, className }: LayoutSectionMockProps) => (
        <div data-testid="footer" style={style} className={className}>
          {children}
        </div>
      ),
    }
  );

  return {
    Layout: MockLayout,
    Button: ({ children, icon, type, size, style, className }: ButtonMockProps) => (
      <button data-testid="button" data-type={type} data-size={size} style={style} className={className}>
        {icon}
        {children}
      </button>
    ),
    Space: ({ children, size, className }: SpaceMockProps) => (
      <div data-testid="space" data-size={size} className={className}>
        {children}
      </div>
    ),
    Avatar: ({ children, size, icon, style, className }: AvatarMockProps) => (
      <div data-testid="avatar" data-size={size} style={style} className={className}>
        {icon}
        {children}
      </div>
    ),
    Typography: {
      Text: ({ children, strong, type, style, className }: TypographyTextMockProps) => (
        <span data-testid="text" data-strong={strong} data-type={type} style={style} className={className}>
          {children}
        </span>
      ),
    },
  };
});

vi.mock('@ant-design/icons', () => ({
  UserOutlined: () => <div data-testid="icon-user" />,
  BellOutlined: () => <div data-testid="icon-bell" />,
}));

vi.mock('../MobileMenu', () => ({
  default: () => <div data-testid="mobile-menu">MobileMenu</div>,
}));

describe('MobileLayout', () => {
  it('renders header, content, footer, and children', () => {
    renderWithProviders(
      <MobileLayout>
        <div data-testid="child">Content</div>
      </MobileLayout>
    );

    expect(screen.getByTestId('header')).toBeInTheDocument();
    expect(screen.getByTestId('content')).toBeInTheDocument();
    expect(screen.getByTestId('footer')).toBeInTheDocument();
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('renders mobile menu, title, notification, and avatar in header', () => {
    renderWithProviders(
      <MobileLayout>
        <div>Content</div>
      </MobileLayout>
    );

    expect(screen.getByTestId('mobile-menu')).toBeInTheDocument();
    expect(screen.getByText('资产管理系统')).toBeInTheDocument();
    expect(screen.getByTestId('icon-bell')).toBeInTheDocument();
    expect(screen.getByTestId('icon-user')).toBeInTheDocument();
  });

  it('renders content area container', () => {
    renderWithProviders(
      <MobileLayout>
        <div data-testid="mobile-content">Content</div>
      </MobileLayout>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
    expect(screen.getByTestId('mobile-content')).toBeInTheDocument();
  });

  it('renders footer text', () => {
    renderWithProviders(
      <MobileLayout>
        <div>Content</div>
      </MobileLayout>
    );

    expect(screen.getByText('资产管理系统 ©2024')).toBeInTheDocument();
  });

  it('applies semantic class names to key sections', () => {
    renderWithProviders(
      <MobileLayout>
        <div>Content</div>
      </MobileLayout>
    );

    expect(screen.getByTestId('layout')).toHaveClass(styles.mobileLayout);
    expect(screen.getByTestId('header')).toHaveClass(styles.mobileHeader);
    expect(screen.getByTestId('content')).toHaveClass(styles.mobileContent);
    expect(screen.getByTestId('footer')).toHaveClass(styles.mobileFooter);
  });
});
