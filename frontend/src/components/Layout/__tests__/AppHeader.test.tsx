/**
 * AppHeader 组件测试
 * 测试应用头部组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';

interface HeaderMockProps {
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

interface ButtonMockProps {
  children?: React.ReactNode;
  icon?: React.ReactNode;
  type?: string;
  onClick?: () => void;
  style?: React.CSSProperties;
}

interface SpaceMockProps {
  children?: React.ReactNode;
  size?: number | string;
}

interface AvatarMockProps {
  children?: React.ReactNode;
  size?: number | string;
  icon?: React.ReactNode;
  style?: React.CSSProperties;
}

interface MenuItemMock {
  key?: string;
  label?: React.ReactNode;
  type?: string;
}

interface DropdownMenuMockProps {
  items?: MenuItemMock[];
  onClick?: (info: { key: string }) => void;
}

interface DropdownMockProps {
  children?: React.ReactNode;
  menu?: DropdownMenuMockProps;
  placement?: string;
  trigger?: string[];
}

interface TypographyTextMockProps {
  children?: React.ReactNode;
  strong?: boolean;
  type?: string;
  style?: React.CSSProperties;
}

interface TooltipMockProps {
  children?: React.ReactNode;
  title?: React.ReactNode;
}

interface ModalConfirmMockProps {
  onOk?: () => void | Promise<void>;
  title?: React.ReactNode;
  content?: React.ReactNode;
  okText?: React.ReactNode;
  cancelText?: React.ReactNode;
  okType?: string;
}

const navigateMock = vi.fn();
const confirmSpy = vi.fn();
const messageInfoSpy = vi.fn();

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useNavigate: () => navigateMock,
}));

// Mock NotificationCenter
vi.mock('../../Notification', () => ({
  NotificationCenter: () => <div data-testid="notification-center" />,
}));

// Mock MessageManager
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    info: (...args: unknown[]) => messageInfoSpy(...args),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    loading: vi.fn(),
  },
}));

// Mock AuthService
vi.mock('../../../services/authService', () => ({
  AuthService: {
    getLocalUser: () => ({
      id: '1',
      username: 'testuser',
      full_name: '测试用户',
      email: 'test@example.com',
    }),
    logout: vi.fn().mockResolvedValue(undefined),
  },
}));

const renderMenuItems = (menu?: DropdownMenuMockProps) => {
  if (!menu?.items) return null;
  return menu.items.map((item, index) => {
    if (!item) return null;
    if (item.type === 'divider') {
      return <div key={`divider-${index}`} data-testid="menu-divider" />;
    }
    const key = String(item.key ?? index);
    return (
      <button key={key} data-testid={`menu-item-${key}`} onClick={() => menu.onClick?.({ key })}>
        {item.label}
      </button>
    );
  });
};

// Mock Ant Design components
vi.mock('antd', () => ({
  Layout: {
    Header: ({ children, style }: HeaderMockProps) => (
      <div data-testid="header" style={style}>
        {children}
      </div>
    ),
  },
  Button: ({ children, icon, type, onClick, style }: ButtonMockProps) => (
    <button data-testid="button" data-type={type} onClick={onClick} style={style}>
      {icon && <span data-testid="button-icon">{icon}</span>}
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
  Dropdown: ({ children, menu, placement }: DropdownMockProps) => (
    <div data-testid="dropdown" data-placement={placement}>
      <div data-testid="dropdown-trigger">{children}</div>
      <div data-testid="dropdown-menu">{renderMenuItems(menu)}</div>
    </div>
  ),
  Tooltip: ({ children, title }: TooltipMockProps) => (
    <div data-testid="tooltip" data-title={title}>
      {children}
    </div>
  ),
  Modal: {
    confirm: (config: ModalConfirmMockProps) => {
      confirmSpy(config);
      return config;
    },
  },
  Typography: {
    Text: ({ children, strong, type, style }: TypographyTextMockProps) => (
      <span data-testid="text" data-strong={strong} data-type={type} style={style}>
        {children}
      </span>
    ),
  },
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  MenuFoldOutlined: () => <div data-testid="icon-menu-fold" />,
  MenuUnfoldOutlined: () => <div data-testid="icon-menu-unfold" />,
  LogoutOutlined: () => <div data-testid="icon-logout" />,
  UserOutlined: () => <div data-testid="icon-user" />,
  SettingOutlined: () => <div data-testid="icon-setting" />,
  QuestionCircleOutlined: () => <div data-testid="icon-question" />,
  ExclamationCircleOutlined: () => <div data-testid="icon-exclamation" />,
  GlobalOutlined: () => <div data-testid="icon-global" />,
}));

describe('AppHeader - 组件导入测试', () => {
  it('应该能够导入AppHeader组件', async () => {
    const module = await import('../AppHeader');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });
});

describe('AppHeader - 渲染与交互测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigateMock.mockClear();
    confirmSpy.mockClear();
    messageInfoSpy.mockClear();
  });

  it('应该显示标题、用户名与通知中心', async () => {
    const AppHeader = (await import('../AppHeader')).default;
    renderWithProviders(<AppHeader collapsed={false} onToggleCollapsed={vi.fn()} />);

    expect(screen.getByText('土地房产资产管理系统')).toBeInTheDocument();
    expect(screen.getByText('测试用户')).toBeInTheDocument();
    expect(screen.getByTestId('notification-center')).toBeInTheDocument();
  });

  it('折叠按钮应显示正确图标并触发回调', async () => {
    const AppHeader = (await import('../AppHeader')).default;
    const handleToggle = vi.fn();
    const { rerender } = renderWithProviders(
      <AppHeader collapsed={false} onToggleCollapsed={handleToggle} />
    );

    expect(screen.getByTestId('icon-menu-fold')).toBeInTheDocument();
    const collapseButton = screen.getByTestId('icon-menu-fold').closest('button');
    expect(collapseButton).not.toBeNull();
    if (collapseButton != null) {
      fireEvent.click(collapseButton);
    }
    expect(handleToggle).toHaveBeenCalledTimes(1);

    rerender(<AppHeader collapsed={true} onToggleCollapsed={handleToggle} />);
    expect(screen.queryByTestId('icon-menu-fold')).not.toBeInTheDocument();
    expect(screen.getByTestId('icon-menu-unfold')).toBeInTheDocument();
  });

  it('用户菜单点击应触发导航与提示', async () => {
    const AppHeader = (await import('../AppHeader')).default;
    renderWithProviders(<AppHeader collapsed={false} onToggleCollapsed={vi.fn()} />);

    fireEvent.click(screen.getByTestId('menu-item-profile'));
    expect(navigateMock).toHaveBeenCalledWith('/profile');

    fireEvent.click(screen.getByTestId('menu-item-settings'));
    expect(messageInfoSpy).toHaveBeenCalledWith('系统设置功能开发中');

    fireEvent.click(screen.getByTestId('menu-item-help'));
    expect(messageInfoSpy).toHaveBeenCalledWith('帮助中心功能开发中');
  });

  it('退出登录应触发确认并执行登出流程', async () => {
    const AppHeader = (await import('../AppHeader')).default;
    const { AuthService } = await import('../../../services/authService');

    renderWithProviders(<AppHeader collapsed={false} onToggleCollapsed={vi.fn()} />);
    fireEvent.click(screen.getByTestId('menu-item-logout'));

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    const config = confirmSpy.mock.calls[0][0] as ModalConfirmMockProps;
    expect(config.title).toBe('确认退出登录');
    expect(config.okText).toBe('确认退出');
    expect(config.cancelText).toBe('取消');
    expect(config.okType).toBe('danger');

    await config.onOk?.();
    expect(AuthService.logout).toHaveBeenCalledTimes(1);
    expect(navigateMock).toHaveBeenCalledWith('/login');
  });
});
