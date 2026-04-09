import { beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import UserManagementPage from '../UserManagementPage';
import { userService } from '@/services/systemService';
import { partyService } from '@/services/partyService';
import { MessageManager } from '@/utils/messageManager';
import { useUserManagementData } from '../UserManagement/hooks/useUserManagementData';

vi.mock('../UserManagement/hooks/useUserManagementData', () => ({
  useUserManagementData: vi.fn(),
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  }),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

const mockUser = {
  id: 'user-1',
  username: 'zhangsan',
  email: 'zhangsan@example.com',
  full_name: '张三',
  phone: '13800000000',
  status: 'active' as const,
  role_id: 'role-1',
  role_name: '资产管理员',
  roles: ['role-1'],
  role_ids: ['role-1'],
  default_organization_id: 'org-1',
  organization_name: '总部',
  last_login: null,
  created_at: '2026-02-01T08:00:00Z',
  updated_at: '2026-02-01T08:00:00Z',
  is_locked: false,
  login_attempts: 0,
};

const buildHookResult = (overrides: Record<string, unknown> = {}) => {
  return {
    users: [mockUser],
    tablePagination: {
      current: 1,
      pageSize: 10,
      total: 1,
    },
    loading: false,
    isRefreshing: false,
    organizations: [{ id: 'org-1', name: '总部' }],
    roles: [{ id: 'role-1', name: '资产管理员' }],
    statistics: {
      total: 1,
      active: 1,
      inactive: 0,
      locked: 0,
      by_role: {},
      by_organization: {},
    },
    usersError: null,
    organizationsError: null,
    rolesError: null,
    statisticsError: null,
    refetchUsers: vi.fn().mockResolvedValue(undefined),
    refetchStatistics: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
};

describe('UserManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useUserManagementData).mockReturnValue(buildHookResult());
    vi.spyOn(userService, 'lockUser').mockResolvedValue(undefined);
    vi.spyOn(userService, 'updateUser').mockResolvedValue({ id: mockUser.id });
    vi.spyOn(userService, 'getUserPartyBindings').mockResolvedValue([]);
    vi.spyOn(partyService, 'getParties').mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 500,
      isTruncated: false,
    });
  });

  it('renders page with toolbar summary and actions', () => {
    renderWithProviders(<UserManagementPage />);

    expect(screen.getByText('用户管理')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新建系统用户' })).toBeInTheDocument();
    expect(screen.getByText('总记录：1')).toBeInTheDocument();
  }, 40_000);

  it('triggers refresh and user status actions', async () => {
    const refetchUsers = vi.fn().mockResolvedValue(undefined);
    const refetchStatistics = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useUserManagementData).mockReturnValue(
      buildHookResult({
        refetchUsers,
        refetchStatistics,
      })
    );

    renderWithProviders(<UserManagementPage />);

    fireEvent.click(screen.getByRole('button', { name: '刷新用户列表' }));
    await waitFor(() => {
      expect(refetchUsers).toHaveBeenCalled();
      expect(refetchStatistics).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByRole('button', { name: '锁定用户zhangsan' }));
    await waitFor(() => {
      expect(userService.lockUser).toHaveBeenCalledWith('user-1');
    });

    fireEvent.click(screen.getByRole('switch', { name: '停用用户zhangsan' }));
    await waitFor(() => {
      expect(userService.updateUser).toHaveBeenCalledWith('user-1', { status: 'inactive' });
      expect(MessageManager.success).toHaveBeenCalledWith('状态已更新');
    });
  }, 20_000);

  it('shows detail drawer and surfaces load errors', async () => {
    vi.mocked(useUserManagementData).mockReturnValue(
      buildHookResult({
        usersError: new Error('load users failed'),
      })
    );

    renderWithProviders(<UserManagementPage />);

    fireEvent.click(screen.getByRole('button', { name: '查看用户zhangsan详情' }));
    expect(await screen.findByText('用户详情')).toBeInTheDocument();

    await waitFor(() => {
      expect(MessageManager.error).toHaveBeenCalledWith('加载用户列表失败');
    });
  }, 20_000);

  it('renders multiple role tags for a multi-role user', async () => {
    vi.mocked(useUserManagementData).mockReturnValue(
      buildHookResult({
        users: [
          {
            ...mockUser,
            role_id: 'role-1',
            role_name: '资产管理员',
            role_ids: ['role-1', 'role-2'],
            roles: ['asset_manager', 'reviewer'],
          },
        ],
        roles: [
          { id: 'role-1', name: '资产管理员' },
          { id: 'role-2', name: '审核员' },
        ],
      })
    );

    renderWithProviders(<UserManagementPage />);

    expect(screen.getByText('资产管理员')).toBeInTheDocument();
    expect(screen.getByText('审核员')).toBeInTheDocument();
  }, 20_000);

  it('opens party binding modal from table action', async () => {
    renderWithProviders(<UserManagementPage />);

    fireEvent.click(screen.getByRole('button', { name: '主体绑定用户zhangsan' }));

    expect(await screen.findByText('主体标签绑定 - 张三')).toBeInTheDocument();
    await waitFor(() => {
      expect(userService.getUserPartyBindings).toHaveBeenCalledWith('user-1', {
        active_only: true,
      });
      expect(partyService.getParties).toHaveBeenCalledWith({ limit: 500 });
    });
  }, 20_000);

  it('does not emit an unconnected useForm warning during page interactions', async () => {
    const refetchUsers = vi.fn().mockResolvedValue(undefined);
    const refetchStatistics = vi.fn().mockResolvedValue(undefined);
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    vi.mocked(useUserManagementData).mockReturnValue(
      buildHookResult({
        refetchUsers,
        refetchStatistics,
      })
    );

    renderWithProviders(<UserManagementPage />);

    fireEvent.click(screen.getByRole('button', { name: '刷新用户列表' }));

    await waitFor(() => {
      expect(refetchUsers).toHaveBeenCalled();
      expect(refetchStatistics).toHaveBeenCalled();
    });

    expect(
      consoleErrorSpy.mock.calls.some(call =>
        call.some(arg =>
          String(arg).includes('Instance created by `useForm` is not connected to any Form element')
        )
      )
    ).toBe(false);

    consoleErrorSpy.mockRestore();
  }, 20_000);
});
