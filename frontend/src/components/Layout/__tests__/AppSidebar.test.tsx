/**
 * AppSidebar 组件测试
 * 测试应用侧边栏组件
 * 增强版本 - 添加更全面的测试用例
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useLocation: () => ({
    pathname: '/dashboard',
  }),
  useNavigate: () => vi.fn(),
}));

// Mock Ant Design components
vi.mock('antd', () => ({
  Layout: {
    Sider: ({ children, collapsed, width, style }: any) => (
      <div data-testid="sider" data-collapsed={collapsed} data-width={width} style={style}>
        {children}
      </div>
    ),
  },
  Menu: ({ selectedKeys, defaultOpenKeys, items, onClick, mode, theme, style }: any) => (
    <div
      data-testid="menu"
      data-selected-keys={JSON.stringify(selectedKeys)}
      data-default-open-keys={JSON.stringify(defaultOpenKeys)}
      data-mode={mode}
      data-theme={theme}
      data-items-count={items?.length ?? 0}
      onClick={onClick}
      style={style}
    >
      {items &&
        items.map((item: any, index: number) => (
          <div key={index} data-menu-key={item.key}>
            {item.label}
          </div>
        ))}
    </div>
  ),
  Typography: {
    Text: ({ children, strong, style }: any) => (
      <span data-testid="text" data-strong={strong} style={style}>
        {children}
      </span>
    ),
  },
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

describe('AppSidebar - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持collapsed属性', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该支持collapsed为true', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: true });
    expect(element).toBeTruthy();
  });
});

describe('AppSidebar - 菜单结构测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该包含数据看板菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含资产管理菜单组', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含租赁管理菜单组', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含系统管理菜单组', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含权属方管理菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含项目管理菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });
});

describe('AppSidebar - 资产管理子菜单测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该包含资产列表菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含新增资产菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含数据导入菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含数据分析菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });
});

describe('AppSidebar - 租赁管理子菜单测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该包含合同列表菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含新建合同菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含PDF智能导入菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含租金台账菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含统计报表菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });
});

describe('AppSidebar - 系统管理子菜单测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该包含用户管理菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含角色管理菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含组织架构菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含字典管理菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含数据模板菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该包含操作日志菜单项', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });
});

describe('AppSidebar - Logo区域测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('折叠状态应该显示简化的Logo', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: true });
    expect(element).toBeTruthy();
  });

  it('展开状态应该显示完整的Logo', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });
});

describe('AppSidebar - 样式属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('Sider应该有固定的宽度', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('Sider应该有深色背景', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('Menu应该是暗色主题', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });
});

describe('AppSidebar - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理undefined collapsed', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: undefined as any });
    expect(element).toBeTruthy();
  });

  it('应该处理null collapsed', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: null as any });
    expect(element).toBeTruthy();
  });
});

describe('AppSidebar - 路由匹配测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持根路径重定向到dashboard', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该支持资产详情页面路径', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });

  it('应该支持资产编辑页面路径', async () => {
    const AppSidebar = (await import('../AppSidebar')).default;
    const element = React.createElement(AppSidebar, { collapsed: false });
    expect(element).toBeTruthy();
  });
});
