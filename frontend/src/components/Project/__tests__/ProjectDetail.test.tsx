/**
 * ProjectDetail 组件测试
 * 测试项目详情展示
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock services
vi.mock('@/services/projectService', () => ({
  projectService: {
    getProjectDetail: vi.fn(() =>
      Promise.resolve({
        id: '1',
        name: '测试项目',
        code: 'PROJ-001',
        type: '商业',
        status: 'active',
        description: '项目描述',
        total_area: 100000,
        rented_area: 60000,
      })
    ),
    getProjectAssets: vi.fn(() => Promise.resolve([])),
    getProjectChildren: vi.fn(() => Promise.resolve([])),
  },
}));

// Mock @tanstack/react-query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: {
      id: '1',
      name: '测试项目',
      code: 'PROJ-001',
      type: '商业',
      status: 'active',
      description: '项目描述',
      total_area: 100000,
      rented_area: 60000,
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
}));

// Mock Ant Design
vi.mock('antd', () => {
  const Card = ({
    children,
    title,
    extra,
  }: {
    children: React.ReactNode;
    title?: React.ReactNode;
    extra?: React.ReactNode;
  }) => (
    <div data-testid="detail-card">
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      {children}
    </div>
  );

  const Descriptions = ({
    children,
    items,
  }: {
    children?: React.ReactNode;
    items?: Array<{ label: string; children: React.ReactNode }>;
  }) => (
    <div data-testid="descriptions">
      {items?.map((item, index) => (
        <div key={index} data-testid={`desc-item-${item.label}`}>
          <span>{item.label}</span>
          <span>{item.children}</span>
        </div>
      ))}
      {children}
    </div>
  );

  Descriptions.Item = ({
    children,
    label,
  }: {
    children: React.ReactNode;
    label: string;
  }) => (
    <div data-testid={`desc-item-${label}`}>
      <span>{label}</span>
      <span>{children}</span>
    </div>
  );

  return {
    Card,
    Descriptions,
    Button: ({
      children,
      onClick,
      icon,
      type,
      danger,
    }: {
      children?: React.ReactNode;
      onClick?: () => void;
      icon?: React.ReactNode;
      type?: string;
      danger?: boolean;
    }) => (
      <button
        data-testid={`btn-${type || 'default'}`}
        data-danger={danger}
        onClick={onClick}
      >
        {icon}
        {children}
      </button>
    ),
    Tag: ({
      children,
      color,
    }: {
      children: React.ReactNode;
      color?: string;
    }) => (
      <span data-testid="tag" data-color={color}>
        {children}
      </span>
    ),
    Statistic: ({
      title,
      value,
      suffix,
    }: {
      title: string;
      value: number;
      suffix?: string;
    }) => (
      <div data-testid={`statistic-${title}`}>
        <span>{title}</span>
        <span>
          {value}
          {suffix}
        </span>
      </div>
    ),
    Row: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="row">{children}</div>
    ),
    Col: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="col">{children}</div>
    ),
    Space: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="space">{children}</div>
    ),
    Divider: () => <hr data-testid="divider" />,
    Spin: ({
      children,
      spinning,
    }: {
      children?: React.ReactNode;
      spinning?: boolean;
    }) => (
      <div data-testid="spin" data-spinning={spinning}>
        {spinning ? '加载中...' : children}
      </div>
    ),
    Alert: ({
      message,
      type,
    }: {
      message: string;
      type?: string;
    }) => (
      <div data-testid="alert" data-type={type}>
        {message}
      </div>
    ),
    Empty: ({ description }: { description?: string }) => (
      <div data-testid="empty">{description}</div>
    ),
    Progress: ({
      percent,
      status,
    }: {
      percent: number;
      status?: string;
    }) => (
      <div data-testid="progress" data-percent={percent} data-status={status}>
        {percent}%
      </div>
    ),
    Tabs: ({
      children,
      items,
    }: {
      children?: React.ReactNode;
      items?: Array<{ key: string; label: string; children: React.ReactNode }>;
    }) => (
      <div data-testid="tabs">
        {items?.map(item => (
          <div key={item.key} data-testid={`tab-${item.key}`}>
            {item.label}
          </div>
        ))}
        {children}
      </div>
    ),
    Table: ({
      dataSource,
    }: {
      dataSource?: Array<{ id: string }>;
    }) => (
      <div data-testid="table">
        {dataSource?.map(item => (
          <div key={item.id}>{item.id}</div>
        ))}
      </div>
    ),
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  EditOutlined: () => <span data-testid="icon-edit">EditIcon</span>,
  DeleteOutlined: () => <span data-testid="icon-delete">DeleteIcon</span>,
  InfoCircleOutlined: () => <span data-testid="icon-info">InfoIcon</span>,
  FolderOutlined: () => <span data-testid="icon-folder">FolderIcon</span>,
}));

import ProjectDetail from '../ProjectDetail';

describe('ProjectDetail', () => {
  const defaultProps = {
    projectId: '1',
    onEdit: vi.fn(),
    onDelete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染详情卡片', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('detail-card')).toBeInTheDocument();
    });

    it('应该显示项目名称', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByText('测试项目')).toBeInTheDocument();
    });

    it('应该显示项目编号', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByText('PROJ-001')).toBeInTheDocument();
    });

    it('应该显示项目状态标签', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('tag')).toBeInTheDocument();
    });
  });

  describe('项目信息', () => {
    it('应该显示描述信息', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('descriptions')).toBeInTheDocument();
    });

    it('应该显示项目类型', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByText('商业')).toBeInTheDocument();
    });
  });

  describe('统计数据', () => {
    it('应该显示总面积统计', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('statistic-总面积')).toBeInTheDocument();
    });

    it('应该显示已出租面积', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('statistic-已出租面积')).toBeInTheDocument();
    });

    it('应该显示出租率进度条', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('progress')).toBeInTheDocument();
    });
  });

  describe('操作按钮', () => {
    it('应该显示编辑按钮', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByText('编辑')).toBeInTheDocument();
    });

    it('点击编辑按钮应该触发onEdit', () => {
      const handleEdit = vi.fn();
      render(<ProjectDetail {...defaultProps} onEdit={handleEdit} />);

      const editButton = screen.getByText('编辑');
      fireEvent.click(editButton);

      expect(handleEdit).toHaveBeenCalled();
    });

    it('应该显示删除按钮', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByText('删除')).toBeInTheDocument();
    });

    it('readonly模式不显示编辑按钮', () => {
      render(<ProjectDetail {...defaultProps} readonly={true} />);

      expect(screen.queryByText('编辑')).not.toBeInTheDocument();
    });
  });

  describe('加载状态', () => {
    it('加载时应该显示Spin', () => {
      const { useQuery } = require('@tanstack/react-query');
      vi.mocked(useQuery).mockReturnValueOnce({
        data: undefined,
        isLoading: true,
        isError: false,
        refetch: vi.fn(),
      });

      render(<ProjectDetail {...defaultProps} />);

      const spin = screen.getByTestId('spin');
      expect(spin).toHaveAttribute('data-spinning', 'true');
    });
  });

  describe('错误处理', () => {
    it('错误时应该显示Alert', () => {
      const { useQuery } = require('@tanstack/react-query');
      vi.mocked(useQuery).mockReturnValueOnce({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error('加载失败'),
        refetch: vi.fn(),
      });

      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('alert')).toBeInTheDocument();
    });
  });

  describe('标签页', () => {
    it('应该显示标签页', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('tabs')).toBeInTheDocument();
    });
  });

  describe('图标显示', () => {
    it('应该显示编辑图标', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('icon-edit')).toBeInTheDocument();
    });

    it('应该显示删除图标', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('icon-delete')).toBeInTheDocument();
    });
  });

  describe('布局', () => {
    it('应该使用Row和Col布局', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getAllByTestId('row').length).toBeGreaterThan(0);
      expect(screen.getAllByTestId('col').length).toBeGreaterThan(0);
    });

    it('应该使用Divider分隔内容', () => {
      render(<ProjectDetail {...defaultProps} />);

      expect(screen.getByTestId('divider')).toBeInTheDocument();
    });
  });
});
