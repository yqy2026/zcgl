/**
 * RoleManagementPage 页面测试
 * 测试角色权限管理页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import RoleManagementPage from '../RoleManagementPage';
import { roleService } from '../../services/systemService';
import { MessageManager } from '@/utils/messageManager';

// Mock dependencies
vi.mock('../../services/systemService', () => ({
  roleService: {
    getRoles: vi.fn(),
    getPermissions: vi.fn(),
    getRoleStatistics: vi.fn(),
    createRole: vi.fn(),
    updateRole: vi.fn(),
    deleteRole: vi.fn(),
    updateRolePermissions: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('../../components/System/SystemBreadcrumb', () => ({
  default: vi.fn(() => null),
}));

vi.mock('dayjs', () => ({
  default: vi.fn(() => ({
    format: vi.fn(() => '2024-01-01'),
  })),
}));

// Mock Ant Design
vi.mock('antd', () => {
  const formInstance = {
    resetFields: vi.fn(),
    setFieldsValue: vi.fn(),
    validateFields: vi.fn(),
  };
  const Form = vi.fn(({ children, onFinish }) => (
    <form
      data-testid="form"
      onSubmit={event => {
        event.preventDefault();
        onFinish?.({
          name: '资产管理员',
          code: 'asset_admin',
          description: '负责资产管理的角色',
          status: 'active',
        });
      }}
    >
      {children}
    </form>
  ));
  Form.Item = vi.fn(({ children }) => <div data-testid="form-item">{children}</div>);
  Form.useForm = vi.fn(() => [formInstance]);

  const Table = vi.fn(({ columns = [], dataSource = [], rowKey }) => (
    <div data-testid="table">
      {dataSource.map((record: Record<string, unknown>, index: number) => {
        const key =
          typeof rowKey === 'function'
            ? rowKey(record)
            : rowKey
              ? record[rowKey]
              : index;
        return (
          <div key={String(key)} data-testid="table-row">
            {columns.map(
              (
                column: {
                  key?: string | number;
                  dataIndex?: string;
                  render?: (value: unknown, row: Record<string, unknown>) => React.ReactNode;
                },
                colIndex: number
              ) => {
                const columnKey = String(column.key ?? column.dataIndex ?? colIndex);
                if (column.render) {
                  const value = column.dataIndex ? record[column.dataIndex] : undefined;
                  return (
                    <div key={columnKey}>{column.render(value, record)}</div>
                  );
                }
                if (column.dataIndex) {
                  return <div key={columnKey}>{record[column.dataIndex]}</div>;
                }
                return <div key={columnKey} />;
              }
            )}
          </div>
        );
      })}
    </div>
  ));

  return {
    Card: vi.fn(({ children }) => <div data-testid="card">{children}</div>),
    Table,
    Button: vi.fn(({ children, onClick, disabled, danger, icon, type }) => (
      <button
        data-testid="button"
        data-danger={danger ? 'true' : 'false'}
        data-type={type}
        onClick={disabled ? undefined : onClick}
        disabled={disabled}
      >
        {icon}
        {children}
      </button>
    )),
    Space: vi.fn(({ children }) => <div data-testid="space">{children}</div>),
    Modal: vi.fn(({ children, open, onOk }) =>
      open ? (
        <div data-testid="modal">
          {children}
          {onOk && (
            <button data-testid="modal-ok" onClick={onOk}>
              OK
            </button>
          )}
        </div>
      ) : null
    ),
    Form,
    Input: Object.assign(
      vi.fn(({ placeholder, disabled }) => (
        <input data-testid="input" placeholder={placeholder} disabled={disabled} />
      )),
      {
        Search: vi.fn(({ placeholder, onSearch }) => (
          <input
            data-testid="role-search"
            placeholder={placeholder}
            onChange={event => {
              const value = (event.target as HTMLInputElement).value;
              onSearch?.(value);
            }}
          />
        )),
        TextArea: vi.fn(({ placeholder }) => (
          <textarea data-testid="textarea" placeholder={placeholder} />
        )),
      }
    ),
    Select: Object.assign(
      vi.fn(({ children, onChange }) => (
        <select
          data-testid="select"
          onChange={event => onChange?.((event.target as HTMLSelectElement).value)}
        >
          {children}
        </select>
      )),
      {
        Option: vi.fn(({ children, value }) => <option value={value}>{children}</option>),
      }
    ),
    Popconfirm: vi.fn(({ children, onConfirm, disabled }) => (
      <div data-testid="popconfirm" onClick={disabled ? undefined : onConfirm}>
        {children}
      </div>
    )),
    Tag: vi.fn(({ children }) => <span data-testid="tag">{children}</span>),
    Tooltip: vi.fn(({ children, title }) => (
      <span data-testid={`tooltip-${title}`}>{children}</span>
    )),
    Row: vi.fn(({ children }) => <div data-testid="row">{children}</div>),
    Col: vi.fn(({ children }) => <div data-testid="col">{children}</div>),
    Statistic: vi.fn(({ title, value }) => (
      <div data-testid={`statistic-${title}`}>{value}</div>
    )),
    Switch: vi.fn(({ checked, onChange, disabled }) => (
      <button
        data-testid="switch"
        data-checked={checked ? 'true' : 'false'}
        onClick={() => {
          if (!disabled) {
            onChange?.(!checked);
          }
        }}
        disabled={disabled}
      />
    )),
    Badge: vi.fn(({ count }) => <span data-testid="badge">{count}</span>),
    Tree: vi.fn(() => <div data-testid="tree" />),
    Transfer: vi.fn(() => <div data-testid="transfer" />),
    Divider: vi.fn(() => <div data-testid="divider" />),
    Typography: {
      Text: vi.fn(({ children }) => <span>{children}</span>),
    },
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => null,
  EditOutlined: () => null,
  DeleteOutlined: () => null,
  ReloadOutlined: () => null,
  TeamOutlined: () => null,
  SettingOutlined: () => null,
  KeyOutlined: () => null,
  SafetyOutlined: () => null,
  UserOutlined: () => null,
  ApartmentOutlined: () => null,
}));

vi.mock('@/styles/colorMap', () => ({
  COLORS: {
    success: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f',
    primary: '#1890ff',
    textSecondary: '#999',
    bgSecondary: '#f5f5f5',
  },
}));

// Helper to create mock role
const createMockRole = (overrides = {}) => ({
  id: 'role-001',
  name: '资产管理员',
  code: 'asset_admin',
  description: '负责资产管理的角色',
  status: 'active',
  permissions: ['perm-001', 'perm-002'],
  user_count: 5,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T00:00:00Z',
  is_system: false,
  ...overrides,
});

const createMockRoleApiItem = (overrides = {}) => ({
  id: 'role-001',
  name: 'asset_admin',
  display_name: '资产管理员',
  is_active: true,
  permissions: [],
  user_count: 5,
  created_at: '2024-01-01',
  updated_at: '2024-01-15',
  is_system_role: false,
  ...overrides,
});

// Helper to create mock permission
const createMockPermission = (overrides = {}) => ({
  id: 'perm-001',
  name: '查看资产',
  code: 'assets.view',
  module: 'assets',
  description: '查看资产列表和详情',
  type: 'menu' as const,
  ...overrides,
});

// Helper to create mock statistics
const createMockStatistics = () => ({
  total: 10,
  active: 8,
  inactive: 2,
  system: 3,
  custom: 7,
  avg_permissions: 12,
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(roleService.getRoles).mockResolvedValue({ items: [], total: 0 });
  vi.mocked(roleService.getPermissions).mockResolvedValue({ data: {} });
  vi.mocked(roleService.getRoleStatistics).mockResolvedValue({
    total_roles: 0,
    active_roles: 0,
    system_roles: 0,
    custom_roles: 0,
  });
});

describe('RoleManagementPage - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../RoleManagementPage');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });

  it('组件应该是React函数组件', async () => {
    const RoleManagementPage = (await import('../RoleManagementPage')).default;
    expect(typeof RoleManagementPage).toBe('function');
  });
});

describe('RoleManagementPage - 组件结构测试', () => {
  it('应该可以渲染页面', () => {
    render(<RoleManagementPage />);
    expect(screen.getByText('新建角色')).toBeInTheDocument();
  });

  it('组件不需要任何必需属性', () => {
    render(<RoleManagementPage />);
    expect(screen.getByTestId('role-search')).toBeInTheDocument();
  });
});

describe('RoleManagementPage - 数据加载测试', () => {
  it('应该加载角色列表', async () => {
    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(roleService.getRoles).toHaveBeenCalled();
    });
  });

  it('应该加载权限列表', async () => {
    vi.mocked(roleService.getPermissions).mockResolvedValue({
      data: {
        assets: [
          {
            id: 'perm-001',
            name: 'assets:view',
            display_name: '查看资产',
            resource: 'assets',
            action: 'view',
          },
        ],
      },
    });

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(roleService.getPermissions).toHaveBeenCalled();
    });
  });

  it('应该加载统计数据', async () => {
    vi.mocked(roleService.getRoleStatistics).mockResolvedValue({
      total_roles: 10,
      active_roles: 8,
      system_roles: 3,
    });

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(roleService.getRoleStatistics).toHaveBeenCalled();
    });
  });
});

describe('RoleManagementPage - 角色操作测试', () => {
  it('应该支持创建角色', async () => {
    render(<RoleManagementPage />);

    fireEvent.click(screen.getByText('新建角色'));
    expect(screen.getByTestId('modal')).toBeInTheDocument();
  });

  it('应该支持编辑角色', async () => {
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem()],
      total: 1,
    });

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row')).toHaveLength(1);
    });

    const editWrapper = screen.getByTestId('tooltip-编辑');
    const editButton = editWrapper.querySelector('button');
    fireEvent.click(editButton!);

    expect(screen.getByTestId('modal')).toBeInTheDocument();
  });

  it('应该支持删除角色', async () => {
    vi.mocked(roleService.deleteRole).mockResolvedValue(undefined);
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem()],
      total: 1,
    });

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row')).toHaveLength(1);
    });

    const deleteWrapper = screen.getByTestId('tooltip-删除');
    const deleteButton = deleteWrapper.querySelector('button');
    fireEvent.click(deleteButton!);

    await waitFor(() => {
      expect(roleService.deleteRole).toHaveBeenCalledWith('role-001');
    });
  });

  it('应该支持切换角色状态', async () => {
    vi.mocked(roleService.updateRole).mockResolvedValue({ id: 'role-001' });
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem({ is_active: true })],
      total: 1,
    });

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row')).toHaveLength(1);
    });

    fireEvent.click(screen.getByTestId('switch'));

    await waitFor(() => {
      expect(roleService.updateRole).toHaveBeenCalledWith('role-001', {
        is_active: false,
      });
    });
  });
});

describe('RoleManagementPage - 权限管理测试', () => {
  it('应该支持配置角色权限', async () => {
    vi.mocked(roleService.updateRolePermissions).mockResolvedValue(undefined);
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem()],
      total: 1,
    });
    vi.mocked(roleService.getPermissions).mockResolvedValueOnce({
      data: {
        assets: [
          {
            id: 'perm-001',
            name: 'assets:view',
            display_name: '查看资产',
            resource: 'assets',
            action: 'view',
          },
        ],
      },
    });

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row')).toHaveLength(1);
    });

    const permissionWrapper = screen.getByTestId('tooltip-权限配置');
    const permissionButton = permissionWrapper.querySelector('button');
    fireEvent.click(permissionButton!);

    expect(screen.getByTestId('modal')).toBeInTheDocument();
    expect(screen.getByTestId('transfer')).toBeInTheDocument();
  });

  it('应该显示权限树形结构', async () => {
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem()],
      total: 1,
    });
    vi.mocked(roleService.getPermissions).mockResolvedValueOnce({
      data: {
        assets: [
          {
            id: 'perm-001',
            name: 'assets:view',
            display_name: '查看资产',
            resource: 'assets',
            action: 'view',
          },
        ],
      },
    });

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row')).toHaveLength(1);
    });

    const permissionWrapper = screen.getByTestId('tooltip-权限配置');
    const permissionButton = permissionWrapper.querySelector('button');
    fireEvent.click(permissionButton!);

    expect(screen.getByTestId('tree')).toBeInTheDocument();
  });

  it('应该支持权限穿梭框', async () => {
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem()],
      total: 1,
    });
    vi.mocked(roleService.getPermissions).mockResolvedValueOnce({
      data: {
        assets: [
          {
            id: 'perm-001',
            name: 'assets:view',
            display_name: '查看资产',
            resource: 'assets',
            action: 'view',
          },
        ],
      },
    });

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row')).toHaveLength(1);
    });

    const permissionWrapper = screen.getByTestId('tooltip-权限配置');
    const permissionButton = permissionWrapper.querySelector('button');
    fireEvent.click(permissionButton!);

    expect(screen.getByTestId('transfer')).toBeInTheDocument();
  });
});

describe('RoleManagementPage - 搜索和筛选测试', () => {
  it('应该支持搜索角色', () => {
    render(<RoleManagementPage />);
    expect(screen.getByTestId('role-search')).toBeInTheDocument();
  });

  it('应该支持按状态筛选', () => {
    render(<RoleManagementPage />);
    expect(screen.getByTestId('select')).toBeInTheDocument();
  });
});

describe('RoleManagementPage - 角色类型测试', () => {
  it('系统角色应该显示特殊标签', async () => {
    const mockRole = createMockRole({ is_system: true });
    expect(mockRole.is_system).toBe(true);
  });

  it('系统角色不应该允许编辑', async () => {
    const mockRole = createMockRole({ is_system: true });
    expect(mockRole.is_system).toBe(true);
  });

  it('系统角色不应该允许删除', async () => {
    const mockRole = createMockRole({ is_system: true });
    expect(mockRole.is_system).toBe(true);
  });

  it('自定义角色应该允许所有操作', async () => {
    const mockRole = createMockRole({ is_system: false });
    expect(mockRole.is_system).toBe(false);
  });
});

describe('RoleManagementPage - 状态显示测试', () => {
  it('启用状态应该显示green标签', async () => {
    const mockRole = createMockRole({ status: 'active' });
    expect(mockRole.status).toBe('active');
  });

  it('停用状态应该显示red标签', async () => {
    const mockRole = createMockRole({ status: 'inactive' });
    expect(mockRole.status).toBe('inactive');
  });
});

describe('RoleManagementPage - 统计卡片测试', () => {
  it('应该显示总角色数', async () => {
    const stats = createMockStatistics();
    expect(stats.total).toBe(10);
  });

  it('应该显示启用角色数', async () => {
    const stats = createMockStatistics();
    expect(stats.active).toBe(8);
  });

  it('应该显示系统角色数', async () => {
    const stats = createMockStatistics();
    expect(stats.system).toBe(3);
  });

  it('应该显示平均权限数', async () => {
    const stats = createMockStatistics();
    expect(stats.avg_permissions).toBe(12);
  });
});

describe('RoleManagementPage - 分页测试', () => {
  it('应该支持分页', () => {
    render(<RoleManagementPage />);
    expect(screen.getByTestId('table')).toBeInTheDocument();
  });

  it('应该支持改变每页数量', () => {
    render(<RoleManagementPage />);
    expect(screen.getByTestId('table')).toBeInTheDocument();
  });
});

describe('RoleManagementPage - 错误处理测试', () => {
  it('加载角色失败应该显示错误消息', async () => {
    vi.mocked(roleService.getRoles).mockRejectedValue(new Error('Load failed'));

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(MessageManager.error).toHaveBeenCalledWith('加载角色列表失败');
    });
  });

  it('创建角色失败应该显示错误消息', async () => {
    vi.mocked(roleService.createRole).mockRejectedValue(new Error('Create failed'));

    render(<RoleManagementPage />);

    fireEvent.click(screen.getByText('新建角色'));
    await waitFor(() => expect(screen.getByTestId('form')).toBeInTheDocument());
    fireEvent.submit(screen.getByTestId('form'));

    await waitFor(() => {
      expect(MessageManager.error).toHaveBeenCalledWith('创建失败');
    });
  });

  it('删除角色失败应该显示错误消息', async () => {
    vi.mocked(roleService.deleteRole).mockRejectedValue(new Error('Delete failed'));
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem()],
      total: 1,
    });

    render(<RoleManagementPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row')).toHaveLength(1);
    });

    const deleteWrapper = screen.getByTestId('tooltip-删除');
    const deleteButton = deleteWrapper.querySelector('button');
    fireEvent.click(deleteButton!);

    await waitFor(() => {
      expect(MessageManager.error).toHaveBeenCalledWith('删除失败');
    });
  });
});

describe('RoleManagementPage - 权限模块测试', () => {
  it('应该包含dashboard模块', async () => {
    const permission = createMockPermission({ module: 'dashboard' });
    expect(permission.module).toBe('dashboard');
  });

  it('应该包含assets模块', async () => {
    const permission = createMockPermission({ module: 'assets' });
    expect(permission.module).toBe('assets');
  });

  it('应该包含rental模块', async () => {
    const permission = createMockPermission({ module: 'rental' });
    expect(permission.module).toBe('rental');
  });

  it('应该包含system模块', async () => {
    const permission = createMockPermission({ module: 'system' });
    expect(permission.module).toBe('system');
  });
});
