/**
 * ProjectList 组件测试
 * 测试项目列表的渲染和交互
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock services
vi.mock('@/services/projectService', () => ({
  projectService: {
    getProjectList: vi.fn(() => Promise.resolve({ items: [], total: 0 })),
    deleteProject: vi.fn(() => Promise.resolve({ success: true })),
  },
}));

// Mock @tanstack/react-query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: {
      items: [
        { id: '1', name: '项目1', code: 'PROJ-001', status: 'active' },
        { id: '2', name: '项目2', code: 'PROJ-002', status: 'planning' },
      ],
      total: 2,
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
  useMutation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

// Mock message manager
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
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
    <div data-testid="project-list-card">
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      {children}
    </div>
  );

  return {
    Card,
    Table: ({
      dataSource,
      loading,
      pagination,
    }: {
      dataSource?: Array<{ id: string; name: string }>;
      loading?: boolean;
      pagination?: object;
    }) => (
      <div
        data-testid="table"
        data-loading={loading}
        data-has-pagination={!!pagination}
      >
        {dataSource?.map(item => (
          <div key={item.id} data-testid={`row-${item.id}`}>
            {item.name}
          </div>
        ))}
      </div>
    ),
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
    Space: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="space">{children}</div>
    ),
    Input: {
      Search: ({
        placeholder,
        onSearch,
      }: {
        placeholder?: string;
        onSearch?: (value: string) => void;
      }) => (
        <input
          data-testid="search-input"
          placeholder={placeholder}
          onChange={e => onSearch?.(e.target.value)}
        />
      ),
    },
    Select: ({
      children,
      placeholder,
      onChange,
    }: {
      children?: React.ReactNode;
      placeholder?: string;
      onChange?: (value: string) => void;
    }) => (
      <select
        data-testid="select"
        onChange={e => onChange?.(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {children}
      </select>
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
    Popconfirm: ({
      children,
      onConfirm,
      title,
    }: {
      children: React.ReactNode;
      onConfirm?: () => void;
      title?: string;
    }) => (
      <div data-testid="popconfirm" data-title={title} onClick={onConfirm}>
        {children}
      </div>
    ),
    Empty: ({ description }: { description?: string }) => (
      <div data-testid="empty">{description || '暂无数据'}</div>
    ),
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
    Tooltip: ({
      children,
      title,
    }: {
      children: React.ReactNode;
      title: string;
    }) => (
      <div data-testid="tooltip" title={title}>
        {children}
      </div>
    ),
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span data-testid="icon-plus">PlusIcon</span>,
  EditOutlined: () => <span data-testid="icon-edit">EditIcon</span>,
  DeleteOutlined: () => <span data-testid="icon-delete">DeleteIcon</span>,
  EyeOutlined: () => <span data-testid="icon-eye">EyeIcon</span>,
  SearchOutlined: () => <span data-testid="icon-search">SearchIcon</span>,
  ReloadOutlined: () => <span data-testid="icon-reload">ReloadIcon</span>,
}));

import ProjectList from '../ProjectList';

describe('ProjectList', () => {
  const defaultProps = {
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onView: vi.fn(),
    onAdd: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染列表卡片', () => {
      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('project-list-card')).toBeInTheDocument();
    });

    it('应该显示表格', () => {
      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('table')).toBeInTheDocument();
    });

    it('应该显示项目数据', () => {
      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('row-1')).toBeInTheDocument();
      expect(screen.getByText('项目1')).toBeInTheDocument();
    });
  });

  describe('操作按钮', () => {
    it('应该显示新增按钮', () => {
      render(<ProjectList {...defaultProps} />);

      expect(screen.getByText('新增')).toBeInTheDocument();
    });

    it('新增按钮应该有PlusOutlined图标', () => {
      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('icon-plus')).toBeInTheDocument();
    });

    it('点击新增按钮应该触发onAdd', () => {
      const handleAdd = vi.fn();
      render(<ProjectList {...defaultProps} onAdd={handleAdd} />);

      const addButton = screen.getByText('新增');
      fireEvent.click(addButton);

      expect(handleAdd).toHaveBeenCalled();
    });

    it('应该显示刷新按钮', () => {
      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('icon-reload')).toBeInTheDocument();
    });
  });

  describe('搜索功能', () => {
    it('应该显示搜索输入框', () => {
      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('search-input')).toBeInTheDocument();
    });

    it('搜索输入框应该有占位符', () => {
      render(<ProjectList {...defaultProps} />);

      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toHaveAttribute('placeholder');
    });
  });

  describe('筛选功能', () => {
    it('应该显示状态筛选下拉框', () => {
      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('select')).toBeInTheDocument();
    });
  });

  describe('加载状态', () => {
    it('加载时表格应该显示loading', () => {
      const { useQuery } = require('@tanstack/react-query');
      vi.mocked(useQuery).mockReturnValueOnce({
        data: undefined,
        isLoading: true,
        isError: false,
        refetch: vi.fn(),
      });

      render(<ProjectList {...defaultProps} />);

      const table = screen.getByTestId('table');
      expect(table).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('空状态', () => {
    it('没有数据时应该显示空状态', () => {
      const { useQuery } = require('@tanstack/react-query');
      vi.mocked(useQuery).mockReturnValueOnce({
        data: { items: [], total: 0 },
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      });

      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('empty')).toBeInTheDocument();
    });
  });

  describe('错误处理', () => {
    it('错误时应该显示错误提示', () => {
      const { useQuery } = require('@tanstack/react-query');
      vi.mocked(useQuery).mockReturnValueOnce({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error('加载失败'),
        refetch: vi.fn(),
      });

      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('alert')).toBeInTheDocument();
    });
  });

  describe('图标显示', () => {
    it('应该显示搜索图标', () => {
      render(<ProjectList {...defaultProps} />);

      expect(screen.getByTestId('icon-search')).toBeInTheDocument();
    });
  });
});
