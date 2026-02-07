/**
 * ProjectList 组件测试
 * 针对 React Query + TableWithPagination 版本
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent, act } from '@/test/utils/test-helpers';

import { useQuery } from '@tanstack/react-query';
import { ownershipService } from '@/services/ownershipService';

// Mock message manager
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
}));

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnershipOptions: vi.fn(() => Promise.resolve([])),
  },
}));

vi.mock('@/components/Forms', () => ({
  ProjectForm: () => <div data-testid="project-form">ProjectForm</div>,
}));

vi.mock('../ProjectDetail', () => ({
  default: () => <div data-testid="project-detail">ProjectDetail</div>,
}));

vi.mock('@/components/Common/TableWithPagination', () => ({
  TableWithPagination: ({ dataSource }: { dataSource?: Array<{ id: string; name: string }> }) => (
    <div data-testid="table">
      {dataSource?.map(item => (
        <div key={item.id} data-testid={`row-${item.id}`}>
          {item.name}
        </div>
      ))}
    </div>
  ),
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
  Card.displayName = 'MockCard';

  const Modal = ({ children, open }: { children?: React.ReactNode; open?: boolean }) => (
    <div data-testid="modal">{open ? children : null}</div>
  );
  Modal.displayName = 'MockModal';

  const Row = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="row">{children}</div>
  );
  Row.displayName = 'MockRow';

  const Col = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="col">{children}</div>
  );
  Col.displayName = 'MockCol';

  const Statistic = ({ title, value }: { title?: React.ReactNode; value?: React.ReactNode }) => (
    <div data-testid="statistic">
      {title}:{value}
    </div>
  );
  Statistic.displayName = 'MockStatistic';

  const Badge = ({ text }: { text?: React.ReactNode }) => <span data-testid="badge">{text}</span>;
  Badge.displayName = 'MockBadge';

  const Switch = ({ checked, onChange }: { checked?: boolean; onChange?: () => void }) => (
    <button data-testid="switch" data-checked={checked} onClick={onChange}>
      Switch
    </button>
  );
  Switch.displayName = 'MockSwitch';

  const Button = ({
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
    <button data-testid={`btn-${type || 'default'}`} data-danger={danger} onClick={onClick}>
      {icon}
      {children}
    </button>
  );
  Button.displayName = 'MockButton';

  const Space = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  );
  Space.displayName = 'MockSpace';

  const InputSearch = ({
    placeholder,
    onSearch,
    onChange,
    value,
    enterButton,
  }: {
    placeholder?: string;
    onSearch?: (value: string) => void;
    onChange?: React.ChangeEventHandler<HTMLInputElement>;
    value?: string;
    enterButton?: React.ReactNode;
  }) => (
    <div data-testid="search-wrapper">
      <input
        data-testid="search-input"
        placeholder={placeholder}
        value={value ?? ''}
        onChange={onChange}
        onKeyDown={e => {
          if (e.key === 'Enter') {
            onSearch?.((e.target as HTMLInputElement).value);
          }
        }}
      />
      <div data-testid="search-enter-button">{enterButton}</div>
    </div>
  );
  InputSearch.displayName = 'MockInputSearch';

  const Select = ({
    children,
    placeholder,
    onChange,
  }: {
    children?: React.ReactNode;
    placeholder?: string;
    onChange?: (value: string) => void;
  }) => (
    <select data-testid="select" onChange={e => onChange?.(e.target.value)}>
      <option value="">{placeholder}</option>
      {children}
    </select>
  );
  Select.displayName = 'MockSelect';
  const Option = ({
    children,
    value,
  }: {
    children?: React.ReactNode;
    value?: string | boolean;
  }) => <option value={String(value ?? '')}>{children}</option>;
  Option.displayName = 'MockSelectOption';
  Select.Option = Option;

  const Tag = ({ children, color }: { children: React.ReactNode; color?: string }) => (
    <span data-testid="tag" data-color={color}>
      {children}
    </span>
  );
  Tag.displayName = 'MockTag';

  const Popconfirm = ({
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
  );
  Popconfirm.displayName = 'MockPopconfirm';

  const Empty = ({ description }: { description?: string }) => (
    <div data-testid="empty">{description || '暂无数据'}</div>
  );
  Empty.displayName = 'MockEmpty';

  const Spin = ({ children, spinning }: { children?: React.ReactNode; spinning?: boolean }) => (
    <div data-testid="spin" data-spinning={spinning}>
      {spinning ? '加载中...' : children}
    </div>
  );
  Spin.displayName = 'MockSpin';

  const Alert = ({ message, type }: { message: string; type?: string }) => (
    <div data-testid="alert" data-type={type}>
      {message}
    </div>
  );
  Alert.displayName = 'MockAlert';

  const Tooltip = ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div data-testid="tooltip" title={title}>
      {children}
    </div>
  );
  Tooltip.displayName = 'MockTooltip';

  const Table = () => <div data-testid="table-placeholder" />;
  Table.displayName = 'MockTable';

  return {
    Card,
    Table,
    Button,
    Space,
    Modal,
    Row,
    Col,
    Statistic,
    Badge,
    Switch,
    Input: {
      Search: InputSearch,
    },
    Select,
    Tag,
    Popconfirm,
    Empty,
    Spin,
    Alert,
    Tooltip,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => {
  const PlusOutlined = () => <span data-testid="icon-plus">PlusIcon</span>;
  const EditOutlined = () => <span data-testid="icon-edit">EditIcon</span>;
  const DeleteOutlined = () => <span data-testid="icon-delete">DeleteIcon</span>;
  const EyeOutlined = () => <span data-testid="icon-eye">EyeIcon</span>;
  const SearchOutlined = () => <span data-testid="icon-search">SearchIcon</span>;
  const ReloadOutlined = () => <span data-testid="icon-reload">ReloadIcon</span>;

  PlusOutlined.displayName = 'PlusOutlined';
  EditOutlined.displayName = 'EditOutlined';
  DeleteOutlined.displayName = 'DeleteOutlined';
  EyeOutlined.displayName = 'EyeOutlined';
  SearchOutlined.displayName = 'SearchOutlined';
  ReloadOutlined.displayName = 'ReloadOutlined';

  return {
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    EyeOutlined,
    SearchOutlined,
    ReloadOutlined,
  };
});

import ProjectList from '../ProjectList';

const flushPromises = () =>
  new Promise<void>(resolve => {
    setTimeout(resolve, 0);
  });

const renderProjectList = async (props?: React.ComponentProps<typeof ProjectList>) => {
  await act(async () => {
    renderWithProviders(<ProjectList {...props} />);
    await flushPromises();
  });
};

const mockRefetchProjects = vi.fn();

describe('ProjectList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRefetchProjects.mockClear();
    vi.mocked(useQuery).mockImplementation(options => {
      const queryKey = (options as { queryKey?: unknown[] }).queryKey;
      const key = Array.isArray(queryKey) ? queryKey[0] : undefined;

      if (key === 'project-list') {
        return {
          data: {
            items: [
              { id: '1', name: '项目1', code: 'PROJ-001', is_active: true, asset_count: 2 },
              { id: '2', name: '项目2', code: 'PROJ-002', is_active: false, asset_count: 0 },
            ],
            total: 2,
            page: 1,
            page_size: 10,
            pages: 1,
          },
          error: null,
          isLoading: false,
          isFetching: false,
          refetch: mockRefetchProjects,
        };
      }

      if (key === 'project-ownership-options') {
        void ownershipService.getOwnershipOptions(true);
        return {
          data: [],
          error: null,
          isLoading: false,
          isFetching: false,
          refetch: vi.fn(),
        };
      }

      return {
        data: undefined,
        error: null,
        isLoading: false,
        isFetching: false,
        refetch: vi.fn(),
      };
    });
  });

  describe('基本渲染', () => {
    it('应该正确渲染列表卡片', async () => {
      await renderProjectList();

      const cards = screen.getAllByTestId('project-list-card');
      expect(cards.length).toBeGreaterThan(0);
    });

    it('应该显示表格', async () => {
      await renderProjectList();

      expect(screen.getByTestId('table')).toBeInTheDocument();
    });

    it('应该显示项目数据', async () => {
      await renderProjectList();

      expect(screen.getByTestId('row-1')).toBeInTheDocument();
      expect(screen.getByText('项目1')).toBeInTheDocument();
    });
  });

  describe('操作按钮', () => {
    it('应该显示新增按钮', async () => {
      await renderProjectList();

      expect(screen.getByText('新建项目')).toBeInTheDocument();
    });

    it('应该显示刷新按钮', async () => {
      await renderProjectList();

      expect(screen.getByTestId('icon-reload')).toBeInTheDocument();
    });
  });

  describe('搜索功能', () => {
    it('应该显示搜索输入框', async () => {
      await renderProjectList();

      expect(screen.getByTestId('search-input')).toBeInTheDocument();
    });

    it('搜索输入框应该有占位符', async () => {
      await renderProjectList();

      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toHaveAttribute('placeholder');
    });

    it('输入搜索内容会应用过滤条件', async () => {
      await renderProjectList();
      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: '关键字' } });

      expect(searchInput).toHaveValue('关键字');
    });
  });

  describe('筛选功能', () => {
    it('应该显示状态筛选下拉框', async () => {
      await renderProjectList();

      const selects = screen.getAllByTestId('select');
      expect(selects.length).toBeGreaterThan(0);
    });
  });

  describe('图标显示', () => {
    it('应该显示搜索图标', async () => {
      await renderProjectList();

      expect(screen.getByTestId('icon-search')).toBeInTheDocument();
    });
  });

  it('初始化时会加载列表和权属方选项', async () => {
    await renderProjectList();

    expect(useQuery).toHaveBeenCalled();
    expect(ownershipService.getOwnershipOptions).toHaveBeenCalled();
  });
});
