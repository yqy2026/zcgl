/**
 * AppBreadcrumb 组件测试
 * 覆盖常见路径与特殊路径的面包屑生成
 */

import { describe, it, expect, vi } from 'vitest';
import { screen } from '@/test/utils/test-helpers';
import type { CSSProperties, ReactNode } from 'react';

import AppBreadcrumb from '../AppBreadcrumb';

let mockPathname = '/dashboard';

interface LinkMockProps {
  to: string;
  children?: ReactNode;
}

interface BreadcrumbItem {
  title?: ReactNode;
}

interface BreadcrumbMockProps {
  items?: BreadcrumbItem[];
  style?: CSSProperties;
}

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: mockPathname }),
  Link: ({ children, to }: LinkMockProps) => (
    <a href={to} data-testid="link" data-link-to={to}>
      {children}
    </a>
  ),
}));

vi.mock('antd', () => ({
  Breadcrumb: ({ items, style }: BreadcrumbMockProps) => (
    <div data-testid="breadcrumb" style={style}>
      {items?.map(item => (
        <div key={String(item.title ?? 'breadcrumb-item')} data-testid="breadcrumb-item">
          {item.title}
        </div>
      ))}
    </div>
  ),
}));

vi.mock('@ant-design/icons', () => ({
  HomeOutlined: () => <span data-testid="icon-home" />,
  DashboardOutlined: () => <span data-testid="icon-dashboard" />,
  UnorderedListOutlined: () => <span data-testid="icon-unordered-list" />,
  PlusOutlined: () => <span data-testid="icon-plus" />,
  SearchOutlined: () => <span data-testid="icon-search" />,
  FileExcelOutlined: () => <span data-testid="icon-file-excel" />,
  UploadOutlined: () => <span data-testid="icon-upload" />,
  DownloadOutlined: () => <span data-testid="icon-download" />,
  BarChartOutlined: () => <span data-testid="icon-bar-chart" />,
  LineChartOutlined: () => <span data-testid="icon-line-chart" />,
  PieChartOutlined: () => <span data-testid="icon-pie-chart" />,
  SettingOutlined: () => <span data-testid="icon-setting" />,
  EditOutlined: () => <span data-testid="icon-edit" />,
  EyeOutlined: () => <span data-testid="icon-eye" />,
  FileTextOutlined: () => <span data-testid="icon-file-text" />,
}));

const renderBreadcrumb = (pathname: string) => {
  mockPathname = pathname;
  return renderWithProviders(<AppBreadcrumb />);
};

describe('AppBreadcrumb', () => {
  it('renders dashboard breadcrumb for /dashboard', () => {
    renderBreadcrumb('/dashboard');

    expect(screen.getByText('仪表盘')).toBeInTheDocument();
    expect(screen.getByTestId('icon-home')).toBeInTheDocument();
  });

  it('renders asset list breadcrumb path', () => {
    renderBreadcrumb('/assets/list');

    expect(screen.getByText('资产管理')).toBeInTheDocument();
    expect(screen.getByText('资产列表')).toBeInTheDocument();
  });

  it('renders asset detail breadcrumb path', () => {
    renderBreadcrumb('/assets/123');

    expect(screen.getByText('资产详情')).toBeInTheDocument();
    expect(screen.getByText('资产管理')).toBeInTheDocument();
  });

  it('renders asset edit breadcrumb path', () => {
    renderBreadcrumb('/assets/123/edit');

    expect(screen.getByText('编辑资产')).toBeInTheDocument();
    expect(screen.getByText('资产详情')).toBeInTheDocument();
  });

  it('renders data import breadcrumb with category', () => {
    renderBreadcrumb('/assets/import');

    expect(screen.getByText('资产管理')).toBeInTheDocument();
    expect(screen.getByText('数据导入')).toBeInTheDocument();
  });

  it('renders system users breadcrumb with category', () => {
    renderBreadcrumb('/system/users');

    expect(screen.getByText('系统管理')).toBeInTheDocument();
    expect(screen.getByText('用户管理')).toBeInTheDocument();
  });

  it('renders system party detail breadcrumb path', () => {
    renderBreadcrumb('/system/parties/party-1');

    expect(screen.getByText('系统管理')).toBeInTheDocument();
    expect(screen.getByText('主体详情')).toBeInTheDocument();
  });

  it('uses manager-prefixed project list link for legacy project detail breadcrumbs', () => {
    renderBreadcrumb('/project/project-1');

    const links = screen.getAllByTestId('link');
    expect(links.map(link => link.getAttribute('data-link-to'))).toEqual(
      expect.arrayContaining(['/manager/projects'])
    );
  });

  it('uses owner-prefixed certificate list link for legacy property certificate detail breadcrumbs', () => {
    renderBreadcrumb('/property-certificates/cert-1');

    const links = screen.getAllByTestId('link');
    expect(links.map(link => link.getAttribute('data-link-to'))).toEqual(
      expect.arrayContaining(['/owner/property-certificates'])
    );
  });

  it('renders breadcrumb container', () => {
    renderBreadcrumb('/assets/list');

    expect(screen.getByTestId('breadcrumb')).toBeInTheDocument();
  });
});
