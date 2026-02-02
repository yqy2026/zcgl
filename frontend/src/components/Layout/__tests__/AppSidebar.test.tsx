/**
 * AppSidebar 组件测试
 * 测试应用侧边栏组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';

interface SiderMockProps {
  children?: React.ReactNode;
  collapsed?: boolean;
  width?: number | string;
  style?: React.CSSProperties;
}

interface MenuItemMock {
  key: string;
  label?: React.ReactNode;
  children?: MenuItemMock[];
}

interface MenuMockProps {
  selectedKeys?: string[];
  defaultOpenKeys?: string[];
  items?: MenuItemMock[];
  onClick?: (info: { key: string }) => void;
  mode?: string;
  theme?: string;
  style?: React.CSSProperties;
}

const navigateMock = vi.fn();

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useLocation: () => ({
    pathname: '/dashboard',
  }),
  useNavigate: () => navigateMock,
}));

const renderMenuItems = (items: MenuItemMock[] | undefined, onClick?: MenuMockProps['onClick']) =>
  items?.map(item => (
    <div key={item.key}>
      <div
        data-menu-key={item.key}
        role="button"
        tabIndex={0}
        onClick={() => onClick?.({ key: item.key })}
        onKeyDown={event => {
          if (event.key === 'Enter') {
            onClick?.({ key: item.key });
          }
        }}
      >
        {item.label}
      </div>
      {item.children && <div data-testid={`submenu-${item.key}`}>{renderMenuItems(item.children, onClick)}</div>}
    </div>
  ));

// Mock Ant Design components
vi.mock('antd', () => ({
  Layout: {
    Sider: ({ children, collapsed, width, style }: SiderMockProps) => (
      <div data-testid="sider" data-collapsed={collapsed} data-width={width} style={style}>
        {children}
      </div>
    ),
  },
  Menu: ({
    selectedKeys,
    defaultOpenKeys,
    items,
    onClick,
    mode,
    theme,
    style,
  }: MenuMockProps) => (
    <div
      data-testid="menu"
      data-selected-keys={JSON.stringify(selectedKeys)}
      data-default-open-keys={JSON.stringify(defaultOpenKeys)}
      data-mode={mode}
      data-theme={theme}
      data-items-count={items?.length ?? 0}
      style={style}
    >
      {renderMenuItems(items, onClick)}
    </div>
  ),
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  DashboardOutlined: () => <div data-testid="icon-dashboard" />,
  HomeOutlined: () => <div data-testid="icon-home" />,
  FileExcelOutlined: () => <div data-testid="icon-file-excel" />,
  BarChartOutlined: () => <div data-testid="icon-bar-chart" />,
  SettingOutlined: () => <div data-testid="icon-setting" />,
  PlusOutlined: () => <div data-testid="icon-plus" />,
  UnorderedListOutlined: () => <div data-testid="icon-unordered-list" />,
  UploadOutlined: () => <div data-testid="icon-upload" />,
  LineChartOutlined: () => <div data-testid="icon-line-chart" />,
  PieChartOutlined: () => <div data-testid="icon-pie-chart" />,
  UserOutlined: () => <div data-testid="icon-user" />,
  TeamOutlined: () => <div data-testid="icon-team" />,
  AuditOutlined: () => <div data-testid="icon-audit" />,
  BookOutlined: () => <div data-testid="icon-book" />,
  ApartmentOutlined: () => <div data-testid="icon-apartment" />,
  TagsOutlined: () => <div data-testid="icon-tags" />,
  IdcardOutlined: () => <div data-testid="icon-idcard" />,
  AccountBookOutlined: () => <div data-testid="icon-account-book" />,
  FileTextOutlined: () => <div data-testid="icon-file-text" />,
  AppstoreOutlined: () => <div data-testid="icon-appstore" />,
  FileAddOutlined: () => <div data-testid="icon-file-add" />,
}));

describe('AppSidebar - 组件导入测试', () => {
  it('应该能够导入AppSidebar组件', async () => {
    const module = await import('../AppSidebar');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });
});

describe('AppSidebar - 渲染与交互测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigateMock.mockClear();
  });

  it('应该渲染主要菜单项与子菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    renderWithProviders(<AppSidebar collapsed={false} />);

    expect(screen.getByText('数据看板')).toBeInTheDocument();
    expect(screen.getAllByText('资产管理').length).toBeGreaterThan(0);
    expect(screen.getByText('资产列表')).toBeInTheDocument();
    expect(screen.getByText('租赁管理')).toBeInTheDocument();
    expect(screen.getByText('合同列表')).toBeInTheDocument();
    expect(screen.getByText('系统管理')).toBeInTheDocument();
    expect(screen.getByText('用户管理')).toBeInTheDocument();
  });

  it('应该设置选中与展开的菜单Key', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    renderWithProviders(<AppSidebar collapsed={false} />);

    const menu = screen.getByTestId('menu');
    expect(menu).toHaveAttribute('data-selected-keys', JSON.stringify(['/dashboard']));
    expect(menu).toHaveAttribute('data-default-open-keys', JSON.stringify([]));
  });

  it('折叠时隐藏Logo文本，展开时显示', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const { rerender } = renderWithProviders(<AppSidebar collapsed={true} />);

    expect(screen.getAllByText('资产管理')).toHaveLength(1);

    rerender(<AppSidebar collapsed={false} />);
    expect(screen.getAllByText('资产管理')).toHaveLength(2);
  });

  it('点击菜单项应触发导航', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    renderWithProviders(<AppSidebar collapsed={false} />);

    fireEvent.click(screen.getByText('数据看板'));
    expect(navigateMock).toHaveBeenCalledWith('/dashboard');
  });
});
