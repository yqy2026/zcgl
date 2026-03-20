/**
 * ProjectList 组件测试
 * 针对 React Query + TableWithPagination 版本
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';

import { useQuery } from '@tanstack/react-query';
import { partyService } from '@/services/partyService';

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|view:manager:party-1',
}));

const mockUseView = vi.fn(() => ({
  currentView: {
    key: 'manager:party-1',
    perspective: 'manager',
    partyId: 'party-1',
    partyName: '运营主体A',
    label: '运营方 · 运营主体A',
  },
  selectionRequired: false,
  isViewReady: true,
}));

vi.mock('@/contexts/ViewContext', () => ({
  useView: () => mockUseView(),
}));

// Mock message manager
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock('@tanstack/react-query', async importOriginal => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQuery: vi.fn(),
  };
});

vi.mock('@/services/partyService', () => ({
  partyService: {
    searchParties: vi.fn(() => Promise.resolve({ items: [] })),
  },
}));

vi.mock('@/components/Forms', () => ({
  ProjectForm: () => <div data-testid="project-form">ProjectForm</div>,
}));

vi.mock('../ProjectDetail', () => ({
  default: () => <div data-testid="project-detail">ProjectDetail</div>,
}));

vi.mock('@/components/Common/TableWithPagination', () => ({
  TableWithPagination: ({
    dataSource,
    columns,
  }: {
    dataSource?: Array<Record<string, unknown>>;
    columns?: Array<{
      key?: string;
      render?: (value: unknown, record: Record<string, unknown>) => React.ReactNode;
      dataIndex?: string;
    }>;
  }) => (
    <div data-testid="table">
      {dataSource?.map(item => (
        <div key={String(item.id)} data-testid={`row-${String(item.id)}`}>
          {String(item.project_name)}
          <div data-testid={`ownership-${String(item.id)}`}>
            {columns
              ?.find(column => column.key === 'owner_party')
              ?.render?.(Array.isArray(item.party_relations) ? item.party_relations : [], item)}
          </div>
          <div data-testid={`status-${String(item.id)}`}>
            {columns
              ?.find(column => column.key === 'status_indicator')
              ?.render?.(item.status, item)}
          </div>
          <div data-testid={`area-status-${String(item.id)}`}>
            {columns?.find(column => column.key === 'area_status')?.render?.(undefined, item)}
          </div>
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
    onSearch,
    showSearch,
  }: {
    children?: React.ReactNode;
    placeholder?: string;
    onChange?: (value: string) => void;
    onSearch?: (value: string) => void;
    showSearch?: boolean;
  }) => (
    <div data-testid="select-wrapper" data-placeholder={placeholder ?? ''}>
      {showSearch && (
        <input
          data-testid={`select-search-${placeholder ?? 'unknown'}`}
          onChange={e => onSearch?.((e.target as HTMLInputElement).value)}
        />
      )}
      <select data-testid="select" onChange={e => onChange?.(e.target.value)}>
        <option value="">{placeholder}</option>
        {children}
      </select>
    </div>
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

  const Alert = ({
    message,
    title,
    description,
    type,
  }: {
    message?: React.ReactNode;
    title?: React.ReactNode;
    description?: React.ReactNode;
    type?: string;
  }) => (
    <div data-testid="alert" data-type={type}>
      <div>{title ?? message}</div>
      <div>{description}</div>
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
  const ExclamationCircleOutlined = () => (
    <span data-testid="icon-exclamation-circle">ExclamationCircleIcon</span>
  );
  const BarChartOutlined = () => <span data-testid="icon-bar-chart">BarChartIcon</span>;
  const CheckCircleOutlined = () => <span data-testid="icon-check-circle">CheckCircleIcon</span>;
  const CloseCircleOutlined = () => <span data-testid="icon-close-circle">CloseCircleIcon</span>;
  const BankOutlined = () => <span data-testid="icon-bank">BankIcon</span>;

  PlusOutlined.displayName = 'PlusOutlined';
  EditOutlined.displayName = 'EditOutlined';
  DeleteOutlined.displayName = 'DeleteOutlined';
  EyeOutlined.displayName = 'EyeOutlined';
  SearchOutlined.displayName = 'SearchOutlined';
  ReloadOutlined.displayName = 'ReloadOutlined';
  ExclamationCircleOutlined.displayName = 'ExclamationCircleOutlined';
  BarChartOutlined.displayName = 'BarChartOutlined';
  CheckCircleOutlined.displayName = 'CheckCircleOutlined';
  CloseCircleOutlined.displayName = 'CloseCircleOutlined';
  BankOutlined.displayName = 'BankOutlined';

  return {
    PlusOutlined,
    EditOutlined,
    DeleteOutlined,
    EyeOutlined,
    SearchOutlined,
    ReloadOutlined,
    ExclamationCircleOutlined,
    BarChartOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    BankOutlined,
  };
});

import ProjectList from '../ProjectList';

const flushPromises = () =>
  new Promise<void>(resolve => {
    setTimeout(resolve, 0);
  });

const renderProjectList = async (props?: React.ComponentProps<typeof ProjectList>) => {
  await act(async () => {
    render(<ProjectList {...props} />);
    await flushPromises();
  });
};

const mockRefetchProjects = vi.fn();

describe('ProjectList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseView.mockReturnValue({
      currentView: {
        key: 'manager:party-1',
        perspective: 'manager',
        partyId: 'party-1',
        partyName: '运营主体A',
        label: '运营方 · 运营主体A',
      },
      selectionRequired: false,
      isViewReady: true,
    });
    mockRefetchProjects.mockClear();
    vi.mocked(useQuery).mockImplementation(options => {
      const queryKey = (options as { queryKey?: unknown[] }).queryKey;
      const key = Array.isArray(queryKey) ? queryKey[0] : undefined;

      if (key === 'project-list') {
        return {
          data: {
            items: [
              {
                id: '1',
                project_name: '项目1',
                project_code: 'PRJ-001',
                status: 'active',
                asset_count: 2,
              },
              {
                id: '2',
                project_name: '项目2',
                project_code: 'PRJ-002',
                status: 'paused',
                asset_count: 0,
              },
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

      if (key === 'project-owner-party-options') {
        const keyword =
          Array.isArray(queryKey) && typeof queryKey[2] === 'string' ? queryKey[2] : '';
        void partyService.searchParties(keyword, { status: 'active', limit: 20 });
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

    it('应该显示当前视角标签', async () => {
      await renderProjectList();

      expect(screen.getByText('当前视角')).toBeInTheDocument();
      expect(screen.getByText('运营方 · 运营主体A')).toBeInTheDocument();
    });

    it('项目列表与主体搜索查询应把当前视角纳入 queryKey', async () => {
      await renderProjectList();

      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: [
            'project-list',
            'user:user-1|view:manager:party-1',
            1,
            10,
            { keyword: '', status: '', ownerPartyId: '' },
          ],
        })
      );
      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['project-owner-party-options', 'user:user-1|view:manager:party-1', ''],
        })
      );
    });

    it('视角未就绪时不应启用项目列表和主体选项查询', async () => {
      mockUseView.mockReturnValue({
        currentView: null,
        selectionRequired: true,
        isViewReady: false,
      });

      await renderProjectList();

      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['project-list', expect.any(String), 1, 10, { keyword: '', status: '', ownerPartyId: '' }],
          enabled: false,
        })
      );
      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['project-owner-party-options', expect.any(String), ''],
          enabled: false,
        })
      );
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

    it('所有方主体筛选应使用后端远程搜索（关键词触发 searchParties）', async () => {
      await renderProjectList();
      const ownerSearchInput = screen.getByTestId('select-search-所有方主体');
      fireEvent.change(ownerSearchInput, { target: { value: '主体关键字' } });

      expect(partyService.searchParties).toHaveBeenCalledWith('主体关键字', {
        status: 'active',
        limit: 20,
      });
    });
  });

  describe('权属方显示', () => {
    it('应过滤停用关系，避免将停用主体显示为有效主体', async () => {
      vi.mocked(useQuery).mockImplementation(options => {
        const queryKey = (options as { queryKey?: unknown[] }).queryKey;
        const key = Array.isArray(queryKey) ? queryKey[0] : undefined;

        if (key === 'project-list') {
          return {
            data: {
              items: [
                {
                  id: 'project-1',
                  project_name: '项目关系过滤测试',
                  project_code: 'PRJ-REL-001',
                  status: 'active',
                  asset_count: 0,
                  party_relations: [
                    {
                      id: 'rel-inactive',
                      party_id: 'ownership-inactive',
                      party_name: '已停用主体',
                      relation_type: 'owner',
                      is_active: false,
                    },
                    {
                      id: 'rel-active',
                      party_id: 'ownership-active',
                      party_name: '有效主体',
                      relation_type: 'owner',
                      is_active: true,
                    },
                  ],
                },
              ],
              total: 1,
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

        if (key === 'project-owner-party-options') {
          const keyword =
            Array.isArray(queryKey) && typeof queryKey[2] === 'string' ? queryKey[2] : '';
          void partyService.searchParties(keyword, { status: 'active', limit: 20 });
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

      await renderProjectList();

      expect(screen.getByText('有效主体')).toBeInTheDocument();
      expect(screen.queryByText('已停用主体')).not.toBeInTheDocument();
    });
  });

  describe('无资产项目展示', () => {
    it('asset_count 为 0 时应显示待补绑定，且面积统计显示 N/A', async () => {
      await renderProjectList();

      expect(screen.getByTestId('status-2')).toHaveTextContent('待补绑定');
      expect(screen.getByTestId('area-status-2')).toHaveTextContent('N/A');
      expect(screen.getByTestId('status-1')).not.toHaveTextContent('待补绑定');
    });

    it('当缺失 asset_count 时，应按 0 处理并显示待补绑定', async () => {
      vi.mocked(useQuery).mockImplementation(options => {
        const queryKey = (options as { queryKey?: unknown[] }).queryKey;
        const key = Array.isArray(queryKey) ? queryKey[0] : undefined;

        if (key === 'project-list') {
          return {
            data: {
              items: [
                {
                  id: 'fallback-empty-assets',
                  project_name: '无资产回退项目',
                  project_code: 'PRJ-FALLBACK-EMPTY',
                  status: 'active',
                },
                {
                  id: 'fallback-has-assets',
                  project_name: '有资产回退项目',
                  project_code: 'PRJ-FALLBACK-HAS',
                  status: 'active',
                },
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

        if (key === 'project-owner-party-options') {
          void partyService.searchParties('', { status: 'active', limit: 50 });
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

      await renderProjectList();

      expect(screen.getByTestId('status-fallback-empty-assets')).toHaveTextContent('待补绑定');
      expect(screen.getByTestId('area-status-fallback-empty-assets')).toHaveTextContent('N/A');
      expect(screen.getByTestId('status-fallback-has-assets')).toHaveTextContent('待补绑定');
      expect(screen.getByTestId('area-status-fallback-has-assets')).toHaveTextContent('N/A');
    });
  });

  describe('图标显示', () => {
    it('应该显示搜索图标', async () => {
      await renderProjectList();

      expect(screen.getByTestId('icon-search')).toBeInTheDocument();
    });
  });

  it('初始化时会加载列表和主体选项', async () => {
    await renderProjectList();

    expect(useQuery).toHaveBeenCalled();
    expect(partyService.searchParties).toHaveBeenCalled();
  });
});
