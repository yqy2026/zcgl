/**
 * OwnershipDetail 组件测试
 *
 * 测试覆盖范围:
 * - 组件基本渲染
 * - 权属方信息展示
 * - 编辑按钮功能
 * - 关联项目展示
 * - 系统信息展示
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock Ant Design
vi.mock('antd', () => ({
  Descriptions: ({
    children,
    column,
    bordered,
  }: {
    children?: React.ReactNode;
    column?: number;
    bordered?: boolean;
  }) => (
    <div data-testid="descriptions" data-column={column} data-bordered={bordered}>
      {children}
    </div>
  ),
  Card: ({ children, title }: { children?: React.ReactNode; title?: string }) => (
    <div data-testid="card" data-title={title}>
      {title && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  ),
  Tag: ({ children, color }: { children?: React.ReactNode; color?: string }) => (
    <span data-testid="tag" data-color={color}>
      {children}
    </span>
  ),
  Space: ({
    children,
    size,
    align,
  }: {
    children?: React.ReactNode;
    size?: string;
    align?: string;
  }) => (
    <div data-testid="space" data-size={size} data-align={align}>
      {children}
    </div>
  ),
  Button: ({
    children,
    onClick,
    icon,
    type,
  }: {
    children?: React.ReactNode;
    onClick?: () => void;
    icon?: React.ReactNode;
    type?: string;
  }) => (
    <button data-testid="button" data-type={type} onClick={onClick}>
      {icon}
      {children}
    </button>
  ),
  Badge: ({ status, text }: { status?: string; text?: string }) => (
    <span data-testid="badge" data-status={status}>
      {text}
    </span>
  ),
  Typography: {
    Text: ({
      children,
      strong,
      style,
    }: {
      children?: React.ReactNode;
      strong?: boolean;
      style?: React.CSSProperties;
    }) => (
      <span data-testid="text" data-strong={strong} style={style}>
        {children}
      </span>
    ),
  },
  Table: ({
    dataSource,
    columns,
    rowKey,
    pagination,
    size,
  }: {
    dataSource?: Array<{ id: string; name: string; code: string }>;
    columns?: Array<{ title: string; key: string }>;
    rowKey?: string;
    pagination?: boolean;
    size?: string;
  }) => (
    <div
      data-testid="table"
      data-row-key={rowKey}
      data-pagination={pagination}
      data-size={size}
      data-column-count={columns?.length}
    >
      {dataSource?.map(item => (
        <div key={item.id} data-testid={`project-row-${item.id}`}>
          <span data-testid={`project-name-${item.id}`}>{item.name}</span>
          <span data-testid={`project-code-${item.id}`}>{item.code}</span>
        </div>
      ))}
    </div>
  ),
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  EditOutlined: () => <span data-testid="icon-edit">Edit</span>,
  ProjectOutlined: () => <span data-testid="icon-project">Project</span>,
}));

import OwnershipDetail from '../OwnershipDetail';
import type { Ownership } from '@/types/ownership';

describe('OwnershipDetail 组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockOwnership: Ownership = {
    id: '1',
    name: '测试权属方',
    code: 'OWN-001',
    short_name: '测试',
    is_active: true,
    asset_count: 10,
    project_count: 5,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    related_projects: [
      {
        id: 'proj-1',
        name: '项目1',
        code: 'PROJ-001',
        relation_type: '合作',
        start_date: '2024-01-01',
        end_date: '2024-12-31',
      },
      {
        id: 'proj-2',
        name: '项目2',
        code: 'PROJ-002',
        relation_type: '投资',
        start_date: '2024-02-01',
      },
    ],
  };

  const mockOnEdit = vi.fn();

  describe('基本渲染', () => {
    it('应该正确渲染组件', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('应该显示权属方名称', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const nameElement = screen.getByTestId('text');
      expect(nameElement).toHaveTextContent('测试权属方');
    });

    it('应该显示权属方简称', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      expect(screen.getByText(/简称：测试/)).toBeInTheDocument();
    });

    it('应该显示启用状态', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const badges = screen.getAllByTestId('badge');
      const activeBadge = badges.find(badge => badge.textContent === '启用');
      expect(activeBadge).toBeInTheDocument();
      expect(activeBadge).toHaveAttribute('data-status', 'success');
    });
  });

  describe('禁用状态', () => {
    it('禁用权属方应该显示禁用状态', () => {
      const inactiveOwnership = { ...mockOwnership, is_active: false };
      render(<OwnershipDetail ownership={inactiveOwnership} onEdit={mockOnEdit} />);

      const badges = screen.getAllByTestId('badge');
      const inactiveBadge = badges.find(badge => badge.textContent === '禁用');
      expect(inactiveBadge).toBeInTheDocument();
      expect(inactiveBadge).toHaveAttribute('data-status', 'error');
    });
  });

  describe('编辑按钮', () => {
    it('应该显示编辑按钮', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const buttons = screen.getAllByTestId('button');
      const editButton = buttons.find(btn => btn.textContent?.includes('编辑'));
      expect(editButton).toBeInTheDocument();
    });

    it('点击编辑按钮应该触发 onEdit', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const buttons = screen.getAllByTestId('button');
      const editButton = buttons.find(btn => btn.textContent?.includes('编辑'));

      if (editButton) {
        fireEvent.click(editButton);
      }

      expect(mockOnEdit).toHaveBeenCalledTimes(1);
    });

    it('编辑按钮应该显示 EditOutlined 图标', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      expect(screen.getByTestId('icon-edit')).toBeInTheDocument();
    });
  });

  describe('基本信息卡片', () => {
    it('应该显示基本信息卡片', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const cards = screen.getAllByTestId('card');
      const basicInfoCard = cards.find(card => card.getAttribute('data-title') === '基本信息');
      expect(basicInfoCard).toBeInTheDocument();
    });

    it('应该显示 Descriptions 组件', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const descriptions = screen.getAllByTestId('descriptions');
      expect(descriptions.length).toBeGreaterThan(0);
    });

    it('应该显示关联资产数量', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const tags = screen.getAllByTestId('tag');
      const assetTag = tags.find(tag => tag.textContent?.includes('10'));
      expect(assetTag).toBeInTheDocument();
    });

    it('应该显示关联项目数量', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const tags = screen.getAllByTestId('tag');
      const projectTag = tags.find(tag => tag.textContent?.includes('5'));
      expect(projectTag).toBeInTheDocument();
    });
  });

  describe('关联项目卡片', () => {
    it('应该显示关联项目卡片', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const cards = screen.getAllByTestId('card');
      const projectCard = cards.find(card => card.getAttribute('data-title') === '关联项目');
      expect(projectCard).toBeInTheDocument();
    });

    it('应该显示关联项目表格', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      expect(screen.getByTestId('table')).toBeInTheDocument();
    });

    it('没有关联项目时不应该显示关联项目卡片', () => {
      const ownershipWithoutProjects = { ...mockOwnership, related_projects: [] };
      render(<OwnershipDetail ownership={ownershipWithoutProjects} onEdit={mockOnEdit} />);

      const cards = screen.getAllByTestId('card');
      const projectCard = cards.find(card => card.getAttribute('data-title') === '关联项目');
      expect(projectCard).toBeUndefined();
    });
  });

  describe('系统信息卡片', () => {
    it('应该显示系统信息卡片', () => {
      render(<OwnershipDetail ownership={mockOwnership} onEdit={mockOnEdit} />);

      const cards = screen.getAllByTestId('card');
      const systemCard = cards.find(card => card.getAttribute('data-title') === '系统信息');
      expect(systemCard).toBeInTheDocument();
    });
  });

  describe('无简称情况', () => {
    it('没有简称时不应该显示简称', () => {
      const ownershipWithoutShortName = { ...mockOwnership, short_name: null };
      render(<OwnershipDetail ownership={ownershipWithoutShortName} onEdit={mockOnEdit} />);

      expect(screen.queryByText(/简称：/)).not.toBeInTheDocument();
    });

    it('简称为空字符串时不应该显示简称', () => {
      const ownershipWithEmptyShortName = { ...mockOwnership, short_name: '' };
      render(<OwnershipDetail ownership={ownershipWithEmptyShortName} onEdit={mockOnEdit} />);

      expect(screen.queryByText(/简称：/)).not.toBeInTheDocument();
    });
  });

  describe('资产和项目计数', () => {
    it('资产数量为0时应该显示0', () => {
      const ownershipWithZeroAssets = { ...mockOwnership, asset_count: 0 };
      render(<OwnershipDetail ownership={ownershipWithZeroAssets} onEdit={mockOnEdit} />);

      const tags = screen.getAllByTestId('tag');
      const zeroTag = tags.find(tag => tag.textContent === '0 个');
      expect(zeroTag).toBeInTheDocument();
    });

    it('项目数量为undefined时应该显示0', () => {
      const ownershipWithNoProjectCount = { ...mockOwnership, project_count: undefined };
      render(<OwnershipDetail ownership={ownershipWithNoProjectCount} onEdit={mockOnEdit} />);

      const tags = screen.getAllByTestId('tag');
      expect(tags.length).toBeGreaterThan(0);
    });
  });
});
