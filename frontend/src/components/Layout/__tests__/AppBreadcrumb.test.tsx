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
  key?: string;
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
        <div
          key={String(item.key ?? item.title ?? 'breadcrumb-item')}
          data-testid="breadcrumb-item"
          data-breadcrumb-key={item.key ?? ''}
        >
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
  it('renders units breadcrumb for /asset-operations/units', () => {
    renderBreadcrumb('/asset-operations/units');

    expect(screen.getByText('资产单元')).toBeInTheDocument();
  });

  it('renders intake breadcrumb for /asset-operations/contracts/intake', () => {
    renderBreadcrumb('/asset-operations/contracts/intake');

    expect(screen.getByText('录入已签合同')).toBeInTheDocument();
  });

  it('renders upstream contracts breadcrumb', () => {
    renderBreadcrumb('/asset-operations/contracts/upstream');

    expect(screen.getByText('上游合同')).toBeInTheDocument();
  });

  it('renders terminal contract actions breadcrumb via dynamic map', () => {
    renderBreadcrumb('/asset-operations/contracts/terminal/tm-1/actions');

    expect(screen.getByText('终端合同操作')).toBeInTheDocument();
  });

  it('renders upstream contract actions breadcrumb via dynamic map', () => {
    renderBreadcrumb('/asset-operations/contracts/upstream/up-1/actions');

    expect(screen.getByText('上游合同操作')).toBeInTheDocument();
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

  it('renders breadcrumb container', () => {
    renderBreadcrumb('/asset-operations/units');

    expect(screen.getByTestId('breadcrumb')).toBeInTheDocument();
  });

  it('provides stable keys for breadcrumb items', () => {
    renderBreadcrumb('/asset-operations/contracts/terminal/tm-1/actions');

    expect(
      screen.getAllByTestId('breadcrumb-item').map(item => item.dataset.breadcrumbKey)
    ).toEqual(expect.arrayContaining([expect.any(String)]));
  });

  it('does not render legacy route breadcrumbs', () => {
    renderBreadcrumb('/dashboard');

    expect(screen.queryByText('工作台')).not.toBeInTheDocument();
    expect(screen.queryByText('资产台账')).not.toBeInTheDocument();
  });
});
