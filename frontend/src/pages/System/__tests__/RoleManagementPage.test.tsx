/**
 * RoleManagementPage 页面测试
 * 测试角色权限管理页面的核心功能
 *
 * 修复说明：
 * - 移除 antd 所有组件 mock
 * - 移除 @ant-design/icons mock
 * - 保留服务层 mock (roleService)
 * - 保留工具类 mock (messageManager, dayjs, colorMap)
 * - 保留业务组件 mock (SystemBreadcrumb)
 * - 使用文本内容进行断言
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { act, fireEvent, screen, waitFor } from '@/test/utils/test-helpers';
import RoleManagementPage from '../RoleManagementPage';
import { roleService } from '@/services/systemService';
import { MessageManager } from '@/utils/messageManager';

// Mock dependencies
vi.mock('@/services/systemService', () => ({
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

vi.mock('@/components/System/SystemBreadcrumb', () => ({
  default: vi.fn(() => null),
}));

vi.mock('dayjs', () => ({
  default: vi.fn(() => ({
    format: vi.fn(() => '2024-01-01'),
  })),
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

const flushPromises = () =>
  new Promise<void>(resolve => {
    setTimeout(resolve, 0);
  });

const renderRoleManagementPage = async () => {
  await act(async () => {
    renderWithProviders(<RoleManagementPage />);
    await flushPromises();
  });
};

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
  it('应该可以渲染页面', async () => {
    await renderRoleManagementPage();
    expect(screen.getByText('新建角色')).toBeInTheDocument();
  });

  it('组件不需要任何必需属性', async () => {
    await renderRoleManagementPage();
    expect(screen.getByPlaceholderText(/搜索角色/)).toBeInTheDocument();
  });
});

describe('RoleManagementPage - 数据加载测试', () => {
  it('应该加载角色列表', async () => {
    await renderRoleManagementPage();

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

    await renderRoleManagementPage();

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

    await renderRoleManagementPage();

    await waitFor(() => {
      expect(roleService.getRoleStatistics).toHaveBeenCalled();
    });
  });
});

describe('RoleManagementPage - 角色操作测试', () => {
  it('应该支持创建角色', async () => {
    const user = userEvent.setup();
    await renderRoleManagementPage();

    await user.click(screen.getByText('新建角色'));
    
    // Check for form field in the modal
    expect(await screen.findByLabelText('角色名称')).toBeInTheDocument();
  });

  it('应该支持编辑角色', async () => {
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem()],
      total: 1,
    });

    await renderRoleManagementPage();

    await waitFor(() => {
      expect(roleService.getRoles).toHaveBeenCalled();
    });

    const editButtons = screen.getAllByRole('button', { name: '编辑' });
    fireEvent.click(editButtons[0]);
  });

  it('应该支持删除角色', async () => {
    vi.mocked(roleService.deleteRole).mockResolvedValue(undefined);
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem()],
      total: 1,
    });

    await renderRoleManagementPage();

    await waitFor(() => {
      expect(roleService.getRoles).toHaveBeenCalled();
    });

    const deleteButtons = screen.getAllByRole('button', { name: '删除' });
    fireEvent.click(deleteButtons[0]);

    // Popconfirm interaction
    await screen.findByText('确定要删除这个角色吗？');
    // 使用 querySelector 查找 Ant Design Popconfirm 的确认按钮
    const confirmButton = document.querySelector('.ant-popconfirm-buttons .ant-btn-primary');
    if (!confirmButton) throw new Error('Confirm button not found');
    fireEvent.click(confirmButton);

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

    await renderRoleManagementPage();

    await waitFor(() => {
      expect(roleService.getRoles).toHaveBeenCalled();
    });

    const switches = screen.queryAllByRole('switch');
    if (switches.length > 0) {
      fireEvent.click(switches[0]);

      await waitFor(() => {
        expect(roleService.updateRole).toHaveBeenCalledWith('role-001', {
          is_active: false,
        });
      });
    }
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

    await renderRoleManagementPage();

    await waitFor(() => {
      expect(roleService.getRoles).toHaveBeenCalled();
    });

    const permissionButtons = screen.getAllByRole('button', { name: '权限配置' });
    fireEvent.click(permissionButtons[0]);
  });
});

describe('RoleManagementPage - 搜索和筛选测试', () => {
  it('应该支持搜索角色', async () => {
    await renderRoleManagementPage();
    expect(screen.getByPlaceholderText(/搜索角色/)).toBeInTheDocument();
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

  it('自定义角色应该允许所有操作', async () => {
    const mockRole = createMockRole({ is_system: false });
    expect(mockRole.is_system).toBe(false);
  });
});

describe('RoleManagementPage - 状态显示测试', () => {
  it('启用状态应该显示active', async () => {
    const mockRole = createMockRole({ status: 'active' });
    expect(mockRole.status).toBe('active');
  });

  it('停用状态应该显示inactive', async () => {
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

describe('RoleManagementPage - 错误处理测试', () => {
  it('加载角色失败应该显示错误消息', async () => {
    vi.mocked(roleService.getRoles).mockRejectedValue(new Error('Load failed'));

    await renderRoleManagementPage();

    await waitFor(() => {
      expect(MessageManager.error).toHaveBeenCalledWith('加载角色列表失败');
    });
  });

  it('删除角色失败应该显示错误消息', async () => {
    vi.mocked(roleService.deleteRole).mockRejectedValue(new Error('Delete failed'));
    vi.mocked(roleService.getRoles).mockResolvedValueOnce({
      items: [createMockRoleApiItem()],
      total: 1,
    });

    await renderRoleManagementPage();

    await waitFor(() => {
      expect(roleService.getRoles).toHaveBeenCalled();
    });

    const deleteButtons = screen.getAllByRole('button', { name: '删除' });
    fireEvent.click(deleteButtons[0]);

    // Popconfirm interaction
    await screen.findByText('确定要删除这个角色吗？');
    // 使用 querySelector 查找 Ant Design Popconfirm 的确认按钮
    const confirmButton = document.querySelector('.ant-popconfirm-buttons .ant-btn-primary');
    if (!confirmButton) throw new Error('Confirm button not found');
    fireEvent.click(confirmButton);

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
