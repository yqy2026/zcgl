/**
 * AssetHistory 组件测试
 * 测试资产历史记录的渲染和交互
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent, waitFor } from '@/test/utils/test-helpers';

// Mock @tanstack/react-query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
  })),
}));

// Mock list hook
vi.mock('@/hooks/useListData', () => ({
  useListData: vi.fn(),
}));

// Mock format utilities
vi.mock('@/utils/format', () => ({
  formatDateTime: (date: string) => (date ? '2024-01-01 12:00:00' : '-'),
  formatDate: (date: string) => (date ? '2024-01-01' : '-'),
  getChangeTypeLabel: (type: string) => {
    const labels: Record<string, string> = {
      create: '创建',
      update: '更新',
      delete: '删除',
    };
    return labels[type] || type;
  },
  getChangeTypeColor: (type: string) => {
    const colors: Record<string, string> = {
      create: 'green',
      update: 'blue',
      delete: 'red',
    };
    return colors[type] || 'default';
  },
}));

// Mock services
vi.mock('@/services/assetService', () => ({
  assetService: {
    getAssetHistory: vi.fn(() =>
      Promise.resolve({ data: { items: [], pagination: { total: 0, pages: 0 } } })
    ),
    getHistoryDetail: vi.fn(() => Promise.resolve({})),
  },
}));

// Mock Ant Design components
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
    <div data-testid="history-card">
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      {children}
    </div>
  );

  const Timeline = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="timeline">{children}</div>
  );
  const TimelineItem = ({
    children,
    dot,
  }: {
    children: React.ReactNode;
    dot?: React.ReactNode;
  }) => (
    <div data-testid="timeline-item">
      {dot}
      <div data-testid="timeline-content">{children}</div>
    </div>
  );
  TimelineItem.displayName = 'MockTimelineItem';
  Timeline.Item = TimelineItem;

  const Select = ({
    children,
    placeholder,
    onChange,
    value,
    allowClear,
  }: {
    children?: React.ReactNode;
    placeholder?: string;
    onChange?: (value: string) => void;
    value?: string;
    allowClear?: boolean;
  }) => (
    <select
      data-testid="select"
      data-placeholder={placeholder}
      data-allow-clear={allowClear}
      value={value}
      onChange={e => onChange?.(e.target.value)}
    >
      <option value="">{placeholder}</option>
      {children}
    </select>
  );
  const SelectOption = ({
    children,
    value,
  }: {
    children: React.ReactNode;
    value?: string;
  }) => <option value={value}>{children}</option>;
  SelectOption.displayName = 'MockSelectOption';
  Select.Option = SelectOption;

  const Descriptions = ({
    children,
    items,
  }: {
    children?: React.ReactNode;
    items?: Array<{ label: string; children: React.ReactNode }>;
  }) => (
    <div data-testid="descriptions">
      {items?.map((item, index) => (
        <div key={index} data-testid="descriptions-item">
          <span data-testid="descriptions-label">{item.label}</span>
          <span data-testid="descriptions-value">{item.children}</span>
        </div>
      ))}
      {children}
    </div>
  );
  const DescriptionsItem = ({
    children,
    label,
  }: {
    children: React.ReactNode;
    label?: React.ReactNode;
  }) => (
    <div data-testid="descriptions-item">
      <span data-testid="descriptions-label">{label}</span>
      <span data-testid="descriptions-value">{children}</span>
    </div>
  );
  DescriptionsItem.displayName = 'MockDescriptionsItem';
  Descriptions.Item = DescriptionsItem;

  return {
    Card,
    Timeline,
    Select,
    DatePicker: {
      RangePicker: ({ placeholder }: { placeholder?: [string, string] }) => (
        <div data-testid="range-picker">
          <input data-testid="date-start" placeholder={placeholder?.[0]} />
          <input data-testid="date-end" placeholder={placeholder?.[1]} />
        </div>
      ),
    },
    Button: ({
      children,
      onClick,
      icon,
      type,
      loading,
    }: {
      children?: React.ReactNode;
      onClick?: () => void;
      icon?: React.ReactNode;
      type?: string;
      loading?: boolean;
    }) => (
      <button
        data-testid={`btn-${type || 'default'}`}
        data-loading={loading}
        onClick={onClick}
      >
        {icon}
        {children}
      </button>
    ),
    Modal: ({
      children,
      open,
      title,
      onCancel,
    }: {
      children: React.ReactNode;
      open?: boolean;
      title?: string;
      onCancel?: () => void;
    }) =>
      open ? (
        <div data-testid="modal" data-title={title}>
          <div data-testid="modal-title">{title}</div>
          <div data-testid="modal-content">{children}</div>
          <button data-testid="modal-close" onClick={onCancel}>
            关闭
          </button>
        </div>
      ) : null,
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
    Empty: ({ description }: { description?: string }) => (
      <div data-testid="empty">{description || '暂无数据'}</div>
    ),
    Spin: ({
      children,
      spinning,
      tip,
    }: {
      children?: React.ReactNode;
      spinning?: boolean;
      tip?: string;
    }) => (
      <div data-testid="spin" data-spinning={spinning}>
        {spinning ? <div data-testid="spin-tip">{tip || '加载中...'}</div> : children}
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
    Pagination: ({
      current,
      total,
      pageSize,
      onChange,
    }: {
      current?: number;
      total?: number;
      pageSize?: number;
      onChange?: (page: number) => void;
    }) => (
      <div
        data-testid="pagination"
        data-current={current}
        data-total={total}
        data-page-size={pageSize}
      >
        <button onClick={() => onChange?.(1)}>上一页</button>
        <span>
          {current} / {Math.ceil((total || 0) / (pageSize || 10))}
        </span>
        <button onClick={() => onChange?.((current || 1) + 1)}>下一页</button>
      </div>
    ),
    Descriptions,
    Space: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="space">{children}</div>
    ),
    Row: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="row">{children}</div>
    ),
    Col: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="col">{children}</div>
    ),
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  ClockCircleOutlined: () => <span data-testid="icon-clock">ClockIcon</span>,
  FilterOutlined: () => <span data-testid="icon-filter">FilterIcon</span>,
  ReloadOutlined: () => <span data-testid="icon-reload">ReloadIcon</span>,
  EyeOutlined: () => <span data-testid="icon-eye">EyeIcon</span>,
  CloseOutlined: () => <span data-testid="icon-close">CloseIcon</span>,
  UserOutlined: () => <span data-testid="icon-user">UserIcon</span>,
  CalendarOutlined: () => <span data-testid="icon-calendar">CalendarIcon</span>,
  HistoryOutlined: () => <span data-testid="icon-history">HistoryIcon</span>,
  EditOutlined: () => <span data-testid="icon-edit">EditIcon</span>,
  PlusOutlined: () => <span data-testid="icon-plus">PlusIcon</span>,
  DeleteOutlined: () => <span data-testid="icon-delete">DeleteIcon</span>,
}));

import AssetHistory from '../AssetHistory';
import { useListData } from '@/hooks/useListData';

const mockLoadList = vi.fn();
const mockApplyFilters = vi.fn();
const mockResetFilters = vi.fn();
const mockUpdatePagination = vi.fn();

let mockData: Array<{
  id: string;
  change_type?: string;
  changed_by?: string;
  changed_at?: string;
  operation_time?: string;
  changed_fields?: string[];
}> = [];
let mockLoading = false;
let mockPagination = { current: 1, pageSize: 10, total: 20 };
let mockFilters = { changeType: undefined as string | undefined, dateRange: null as null };
let triggerError = false;

describe('AssetHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    triggerError = false;
    mockData = [
      {
        id: '1',
        change_type: 'create',
        changed_by: '张三',
        changed_at: '2024-01-01T00:00:00.000Z',
        operation_time: '2024-01-01T00:00:00.000Z',
        changed_fields: ['property_name'],
      },
      {
        id: '2',
        change_type: 'update',
        changed_by: '李四',
        changed_at: '2024-01-02T00:00:00.000Z',
        operation_time: '2024-01-02T00:00:00.000Z',
        changed_fields: ['rentable_area', 'rented_area'],
      },
    ];
    mockLoading = false;
    mockPagination = { current: 1, pageSize: 10, total: 20 };
    mockFilters = { changeType: undefined, dateRange: null };

    vi.mocked(useListData).mockImplementation(options => {
      if (triggerError && options.onError) {
        Promise.resolve().then(() => {
          options.onError?.(new Error('加载失败'));
        });
      }

      return {
        data: mockData,
        loading: mockLoading,
        pagination: mockPagination,
        filters: mockFilters,
        loadList: mockLoadList,
        applyFilters: mockApplyFilters,
        resetFilters: mockResetFilters,
        updatePagination: mockUpdatePagination,
      } as ReturnType<typeof useListData>;
    });
  });

  describe('基本渲染', () => {
    it('应该正确渲染历史记录卡片', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getAllByTestId('history-card').length).toBeGreaterThan(0);
    });

    it('应该显示卡片标题', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByText('变更历史')).toBeInTheDocument();
    });

    it('应该显示时间线组件', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByTestId('timeline')).toBeInTheDocument();
    });

    it('应该显示时间线项目', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const items = screen.getAllByTestId('timeline-item');
      expect(items.length).toBeGreaterThan(0);
    });
  });

  describe('筛选功能', () => {
    it('应该显示变更类型筛选器', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByTestId('select')).toBeInTheDocument();
    });

    it('应该显示日期范围筛选器', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByTestId('range-picker')).toBeInTheDocument();
    });

    it('变更类型选项应该包含创建、更新、删除', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getAllByText('创建').length).toBeGreaterThan(0);
      expect(screen.getAllByText('更新').length).toBeGreaterThan(0);
      expect(screen.getAllByText('删除').length).toBeGreaterThan(0);
    });
  });

  describe('刷新功能', () => {
    it('应该显示刷新按钮', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByText('刷新')).toBeInTheDocument();
    });

    it('点击刷新按钮应该触发数据重新加载', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const refreshButton = screen.getByText('刷新');
      fireEvent.click(refreshButton);

      expect(mockLoadList).toHaveBeenCalled();
    });

    it('刷新按钮应该显示刷新图标', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByTestId('icon-reload')).toBeInTheDocument();
    });
  });

  describe('变更类型标签', () => {
    it('应该显示变更类型标签', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const tags = screen.getAllByTestId('tag');
      expect(tags.length).toBeGreaterThan(0);
    });

    it('创建操作应该使用绿色标签', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const tags = screen.getAllByTestId('tag');
      const createTag = tags.find(tag => tag.getAttribute('data-color') === 'green');
      expect(createTag).toBeInTheDocument();
    });

    it('更新操作应该使用蓝色标签', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const tags = screen.getAllByTestId('tag');
      const updateTag = tags.find(tag => tag.getAttribute('data-color') === 'blue');
      expect(updateTag).toBeInTheDocument();
    });
  });

  describe('分页功能', () => {
    it('应该显示分页组件', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByTestId('pagination')).toBeInTheDocument();
    });

    it('分页应该显示正确的总数', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const pagination = screen.getByTestId('pagination');
      expect(pagination).toHaveAttribute('data-total', '20');
    });
  });

  describe('详情弹窗', () => {
    it('应该有查看详情按钮', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getAllByText('查看详情').length).toBeGreaterThan(0);
    });

    it('点击查看详情应该打开弹窗', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const viewButtons = screen.getAllByText('查看详情');
      fireEvent.click(viewButtons[0]);

      expect(screen.getByTestId('modal')).toBeInTheDocument();
    });

    it('弹窗应该有关闭按钮', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const viewButtons = screen.getAllByText('查看详情');
      fireEvent.click(viewButtons[0]);

      expect(screen.getByTestId('modal-close')).toBeInTheDocument();
    });

    it('点击关闭按钮应该关闭弹窗', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const viewButtons = screen.getAllByText('查看详情');
      fireEvent.click(viewButtons[0]);

      const closeButton = screen.getByTestId('modal-close');
      fireEvent.click(closeButton);

      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
    });
  });

  describe('用户信息显示', () => {
    it('应该显示操作人姓名', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByText('张三')).toBeInTheDocument();
      expect(screen.getByText('李四')).toBeInTheDocument();
    });
  });

  describe('加载状态', () => {
    it('加载时应该显示Spin组件', () => {
      mockLoading = true;
      mockData = [];

      renderWithProviders(<AssetHistory assetId="asset-1" />);

      const spin = screen.getByTestId('spin');
      expect(spin).toHaveAttribute('data-spinning', 'true');
    });

    it('加载时应该显示加载提示', () => {
      mockLoading = true;
      mockData = [];

      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByTestId('spin-tip')).toBeInTheDocument();
    });
  });

  describe('错误状态', () => {
    it('错误时应该显示Alert组件', async () => {
      triggerError = true;
      mockData = [];
      mockLoading = false;

      renderWithProviders(<AssetHistory assetId="asset-1" />);

      await waitFor(() => {
        expect(screen.getByTestId('alert')).toBeInTheDocument();
      });
    });

    it('错误时应该显示错误类型', async () => {
      triggerError = true;
      mockData = [];
      mockLoading = false;

      renderWithProviders(<AssetHistory assetId="asset-1" />);

      await waitFor(() => {
        const alert = screen.getByTestId('alert');
        expect(alert).toHaveAttribute('data-type', 'error');
      });
    });
  });

  describe('空状态处理', () => {
    it('没有历史记录时应该显示空状态', () => {
      mockData = [];
      mockPagination = { current: 1, pageSize: 10, total: 0 };

      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByTestId('empty')).toBeInTheDocument();
    });

    it('空状态应该有提示信息', () => {
      mockData = [];
      mockPagination = { current: 1, pageSize: 10, total: 0 };

      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByText('暂无变更历史')).toBeInTheDocument();
    });
  });

  describe('时间信息', () => {
    it('应该显示变更时间', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      // 格式化后的时间
      expect(screen.getAllByText('2024-01-01').length).toBeGreaterThan(0);
    });
  });

  describe('图标显示', () => {
    it('应该显示历史图标', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByTestId('icon-history')).toBeInTheDocument();
    });

    it('应该显示筛选图标', () => {
      renderWithProviders(<AssetHistory assetId="asset-1" />);

      expect(screen.getByTestId('icon-filter')).toBeInTheDocument();
    });
  });

  describe('属性传递', () => {
    it('应该接受assetId属性', () => {
      renderWithProviders(<AssetHistory assetId="test-asset-123" />);

      expect(screen.getAllByTestId('history-card').length).toBeGreaterThan(0);
    });
  });
});
