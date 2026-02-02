/**
 * MobileLayout 组件测试
 * 覆盖头部、面包屑、内容与页脚渲染
 */

import { describe, it, expect, vi } from 'vitest';
import { screen } from '@/test/utils/test-helpers';
import type { CSSProperties, ReactNode } from 'react';

import MobileLayout from '../MobileLayout';

interface LayoutSectionMockProps {
  children?: ReactNode;
  style?: CSSProperties;
}

interface ButtonMockProps {
  children?: ReactNode;
  icon?: ReactNode;
  type?: string;
  size?: number | string;
  style?: CSSProperties;
}

interface SpaceMockProps {
  children?: ReactNode;
  size?: number | string;
}

interface AvatarMockProps {
  children?: ReactNode;
  size?: number | string;
  icon?: ReactNode;
  style?: CSSProperties;
}

interface TypographyTextMockProps {
  children?: ReactNode;
  strong?: boolean;
  type?: string;
  style?: CSSProperties;
}

vi.mock('antd', () => {
  const MockLayout = Object.assign(
    ({ children, style }: LayoutSectionMockProps) => (
      <div data-testid="layout" style={style}>
        {children}
      </div>
    ),
    {
      Header: ({ children, style }: LayoutSectionMockProps) => (
        <div data-testid="header" style={style}>
          {children}
        </div>
      ),
      Content: ({ children, style }: LayoutSectionMockProps) => (
        <div data-testid="content" style={style}>
          {children}
        </div>
      ),
      Footer: ({ children, style }: LayoutSectionMockProps) => (
        <div data-testid="footer" style={style}>
          {children}
        </div>
      ),
    }
  );

  return {
    Layout: MockLayout,
    Button: ({ children, icon, type, size, style }: ButtonMockProps) => (
      <button data-testid="button" data-type={type} data-size={size} style={style}>
        {icon}
        {children}
      </button>
    ),
    Space: ({ children, size }: SpaceMockProps) => (
      <div data-testid="space" data-size={size}>
        {children}
      </div>
    ),
    Avatar: ({ children, size, icon, style }: AvatarMockProps) => (
      <div data-testid="avatar" data-size={size} style={style}>
        {icon}
        {children}
      </div>
    ),
    Typography: {
      Text: ({ children, strong, type, style }: TypographyTextMockProps) => (
        <span data-testid="text" data-strong={strong} data-type={type} style={style}>
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

vi.mock('../AppBreadcrumb', () => ({
  default: () => <div data-testid="app-breadcrumb">AppBreadcrumb</div>,
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
    expect(screen.getByText('资产管理')).toBeInTheDocument();
    expect(screen.getByTestId('icon-bell')).toBeInTheDocument();
    expect(screen.getByTestId('icon-user')).toBeInTheDocument();
  });

  it('renders breadcrumb section', () => {
    renderWithProviders(
      <MobileLayout>
        <div>Content</div>
      </MobileLayout>
    );

    expect(screen.getByTestId('app-breadcrumb')).toBeInTheDocument();
  });

  it('renders footer text', () => {
    renderWithProviders(
      <MobileLayout>
        <div>Content</div>
      </MobileLayout>
    );

    expect(screen.getByText('资产管理系统 ©2024')).toBeInTheDocument();
  });

  it('applies header fixed styles', () => {
    renderWithProviders(
      <MobileLayout>
        <div>Content</div>
      </MobileLayout>
    );

    const header = screen.getByTestId('header');
    expect(header).toHaveStyle({ position: 'fixed', height: '56px' });
  });
});
