/**
 * MobileMenu 组件测试
 * 覆盖打开/关闭、菜单点击与路由联动
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@/test/utils/test-helpers';
import type { CSSProperties, ReactNode } from 'react';

import MobileMenu from '../MobileMenu';
import { getOpenKeys, getSelectedKeys, MENU_ITEMS } from '@/config/menuConfig';

interface DrawerMockProps {
  children?: ReactNode;
  title?: ReactNode;
  placement?: string;
  onClose?: () => void;
  open?: boolean;
  width?: number | string;
  styles?: CSSProperties;
  extra?: ReactNode;
}

interface MenuItemMock {
  key?: string;
  label?: ReactNode;
}

interface MenuMockProps {
  selectedKeys?: string[];
  defaultOpenKeys?: string[];
  items?: MenuItemMock[];
  onClick?: (info: { key: string }) => void;
  mode?: string;
  style?: CSSProperties;
}

interface ButtonMockProps {
  children?: ReactNode;
  icon?: ReactNode;
  type?: string;
  onClick?: () => void;
  style?: CSSProperties;
}

interface SpaceMockProps {
  children?: ReactNode;
}

interface TextMockProps {
  children?: ReactNode;
  strong?: boolean;
}

const navigateMock = vi.fn();

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: '/dashboard' }),
  useNavigate: () => navigateMock,
}));

vi.mock('@/config/menuConfig', () => ({
  MENU_ITEMS: [
    { key: '/dashboard', label: '工作台' },
    { key: '/assets/list', label: '资产列表' },
  ],
  getSelectedKeys: vi.fn(() => ['/dashboard']),
  getOpenKeys: vi.fn(() => ['/assets']),
}));

vi.mock('antd', () => ({
  Drawer: ({ children, title, placement, onClose, open, width, extra }: DrawerMockProps) => (
    <div
      data-testid="drawer"
      data-placement={placement}
      data-open={open}
      data-width={width}
    >
      {title && <div data-testid="drawer-title">{title}</div>}
      {extra && <div data-testid="drawer-extra">{extra}</div>}
      {children}
      {onClose && (
        <button data-testid="drawer-close" type="button" onClick={onClose}>
          Close
        </button>
      )}
    </div>
  ),
  Menu: ({ selectedKeys, defaultOpenKeys, items, onClick, mode }: MenuMockProps) => (
    <div
      data-testid="menu"
      data-selected-keys={JSON.stringify(selectedKeys)}
      data-default-open-keys={JSON.stringify(defaultOpenKeys)}
      data-mode={mode}
    >
      {items?.map(item => (
        <button
          key={item.key}
          type="button"
          data-testid="menu-item"
          data-key={item.key}
          onClick={() => item.key && onClick?.({ key: item.key })}
        >
          {item.label}
        </button>
      ))}
    </div>
  ),
  Button: ({ children, icon, type, onClick, style }: ButtonMockProps) => (
    <button data-testid="button" data-type={type} onClick={onClick} style={style}>
      {icon}
      {children}
    </button>
  ),
  Space: ({ children }: SpaceMockProps) => <div data-testid="space">{children}</div>,
  Typography: {
    Text: ({ children, strong }: TextMockProps) => (
      <span data-testid="text" data-strong={strong}>
        {children}
      </span>
    ),
  },
}));

vi.mock('@ant-design/icons', () => ({
  MenuOutlined: () => <div data-testid="icon-menu" />,
  CloseOutlined: () => <div data-testid="icon-close" />,
  HomeOutlined: () => <div data-testid="icon-home" />,
}));

describe('MobileMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders menu trigger button and closed drawer by default', () => {
    renderWithProviders(<MobileMenu />);

    const triggerButton = screen.getByTestId('icon-menu').closest('button');
    expect(triggerButton).not.toBeNull();
    expect(screen.getByTestId('drawer')).toHaveAttribute('data-open', 'false');
  });

  it('opens drawer when trigger button clicked', () => {
    renderWithProviders(<MobileMenu />);

    const triggerButton = screen.getByTestId('icon-menu').closest('button');
    if (triggerButton) {
      fireEvent.click(triggerButton);
    }
    expect(screen.getByTestId('drawer')).toHaveAttribute('data-open', 'true');
  });

  it('closes drawer when close button clicked', () => {
    renderWithProviders(<MobileMenu />);

    const triggerButton = screen.getByTestId('icon-menu').closest('button');
    if (triggerButton) {
      fireEvent.click(triggerButton);
    }
    expect(screen.getByTestId('drawer')).toHaveAttribute('data-open', 'true');

    fireEvent.click(screen.getByTestId('drawer-close'));
    expect(screen.getByTestId('drawer')).toHaveAttribute('data-open', 'false');
  });

  it('navigates and closes drawer when menu item clicked', () => {
    renderWithProviders(<MobileMenu />);

    const triggerButton = screen.getByTestId('icon-menu').closest('button');
    if (triggerButton) {
      fireEvent.click(triggerButton);
    }

    const menuItems = screen.getAllByTestId('menu-item');
    fireEvent.click(menuItems[1]);

    expect(navigateMock).toHaveBeenCalledWith('/assets/list');
    expect(screen.getByTestId('drawer')).toHaveAttribute('data-open', 'false');
  });

  it('passes selected/open keys to Menu based on location', () => {
    renderWithProviders(<MobileMenu />);

    expect(getSelectedKeys).toHaveBeenCalledWith('/dashboard');
    expect(getOpenKeys).toHaveBeenCalledWith('/dashboard');

    const menu = screen.getByTestId('menu');
    expect(menu).toHaveAttribute('data-selected-keys', JSON.stringify(['/dashboard']));
    expect(menu).toHaveAttribute('data-default-open-keys', JSON.stringify(['/assets']));
  });

  it('renders drawer title with Home icon', () => {
    renderWithProviders(<MobileMenu />);

    const title = screen.getByTestId('drawer-title');
    expect(title).toBeInTheDocument();
    expect(screen.getByTestId('icon-home')).toBeInTheDocument();
  });

  it('uses menu items from config', () => {
    renderWithProviders(<MobileMenu />);

    const items = screen.getAllByTestId('menu-item');
    expect(items).toHaveLength(MENU_ITEMS.length);
  });
});
