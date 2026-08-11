import { beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { fireEvent, renderWithProviders, screen, waitFor, within } from '@/test/utils/test-helpers';
import UserManagementPage from '../UserManagement';
import {
  type UserPartyScopeCommitResponse,
  type UserOrganizationTransferCommitResponse,
  type UserOrganizationTransferPreview,
  type UserPartyScopePreview,
  userService,
} from '@/services/systemService';
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
  account_type: 'human' as const,
  organization_id: 'org-1',
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

  it('keeps account classification and organization assignment out of the ordinary user form', async () => {
    renderWithProviders(<UserManagementPage />);

    fireEvent.click(screen.getByRole('button', { name: '新建系统用户' }));

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.queryByLabelText('所属组织')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('账号类型')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('状态')).not.toBeInTheDocument();
  });

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

    fireEvent.click(screen.getByRole('button', { name: '用户数据范围zhangsan' }));

    expect(await screen.findByText('用户数据范围 - 张三')).toBeInTheDocument();
    await waitFor(() => {
      expect(userService.getUserPartyBindings).toHaveBeenCalledWith('user-1', {
        active_only: true,
      });
      expect(partyService.getParties).toHaveBeenCalledWith({
        limit: 500,
        status: 'active',
        review_status: 'approved',
      });
    });
  }, 20_000);

  it('requires a reason before committing a previewed Party scope change', async () => {
    const approvedParty = {
      id: 'party-approved',
      business_roles: ['owner'],
      party_type: 'legal_entity',
      name: 'Approved Party',
      code: 'LE-000001',
      status: 'active',
      review_status: 'approved',
      created_at: '2026-08-04T08:00:00Z',
      updated_at: '2026-08-04T08:00:00Z',
    } as const;
    const draftParty = {
      ...approvedParty,
      id: 'party-draft',
      name: 'Draft Party',
      code: 'LE-000002',
      review_status: 'draft',
    } as const;
    const beforeScope = {
      source: 'none',
      scope_mode: 'none',
      owner_party_ids: [],
      manager_party_ids: [],
      organization_id: 'org-1',
      source_organization_id: null,
      next_transition_at: null,
      error_code: null,
      issues: [],
    } satisfies UserPartyScopePreview['before_scope'];
    const afterScope = {
      ...beforeScope,
      source: 'explicit',
      scope_mode: 'owner',
      owner_party_ids: [approvedParty.id],
    } satisfies UserPartyScopePreview['after_scope'];
    const preview = {
      user_id: mockUser.id,
      operation: 'create',
      before_scope: beforeScope,
      after_scope: afterScope,
      impact: {
        before_current_binding_count: 0,
        after_current_binding_count: 1,
        scope_changed: true,
        uses_organization_default_after: false,
      },
      preview_token: 'preview-token-1',
      expires_at: '2026-08-04T08:10:00Z',
    } satisfies UserPartyScopePreview;
    const commitResponse = {
      binding: {
        id: 'binding-1',
        user_id: mockUser.id,
        party_id: approvedParty.id,
        relation_type: 'owner',
        valid_from: '2026-08-04T08:00:00Z',
        valid_to: null,
        created_at: '2026-08-04T08:00:00Z',
        updated_at: '2026-08-04T08:00:00Z',
      },
      operation: 'create',
      before_scope: beforeScope,
      after_scope: afterScope,
      impact: preview.impact,
      committed_at: '2026-08-04T08:01:00Z',
      idempotent: false,
    } satisfies UserPartyScopeCommitResponse;

    vi.mocked(partyService.getParties).mockResolvedValue({
      items: [approvedParty, draftParty],
      total: 2,
      skip: 0,
      limit: 500,
      isTruncated: false,
    });
    vi.spyOn(userService, 'previewUserPartyScope').mockResolvedValue(preview);
    vi.spyOn(userService, 'commitUserPartyScope').mockResolvedValue(commitResponse);

    renderWithProviders(<UserManagementPage />);

    fireEvent.click(screen.getByRole('button', { name: '用户数据范围zhangsan' }));
    expect(await screen.findByText('用户数据范围 - 张三')).toBeInTheDocument();

    const scopeDialog = screen.getByRole('dialog');
    const [partySelect] = within(scopeDialog).getAllByRole('combobox');
    fireEvent.mouseDown(partySelect);
    // 服务端负责过滤（#82）：请求携带 review_status=approved，客户端透传不再 .filter
    await waitFor(() => {
      expect(partyService.getParties).toHaveBeenCalledWith({
        limit: 500,
        status: 'active',
        review_status: 'approved',
      });
    });
    expect(await screen.findByText('Draft Party')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Approved Party'));

    fireEvent.click(screen.getByRole('button', { name: '新增绑定' }));
    await waitFor(() => {
      expect(userService.previewUserPartyScope).toHaveBeenCalledWith('user-1', {
        operation: 'create',
        party_id: 'party-approved',
        relation_type: 'owner',
      });
    });

    fireEvent.click(screen.getByRole('button', { name: '确认提交' }));
    expect(await screen.findByText('请填写变更原因')).toBeInTheDocument();
    expect(userService.commitUserPartyScope).not.toHaveBeenCalled();

    fireEvent.change(screen.getByPlaceholderText('请填写本次范围调整的原因'), {
      target: { value: 'Assign the user to the approved Party.' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认提交' }));

    await waitFor(() => {
      expect(userService.commitUserPartyScope).toHaveBeenCalledWith('user-1', {
        preview_token: 'preview-token-1',
        reason: 'Assign the user to the approved Party.',
        idempotency_key: expect.any(String),
      });
    });
  }, 30_000);
  it('previews and commits a human user organization transfer through the dedicated action', async () => {
    const beforeScope = {
      source: 'organization',
      scope_mode: 'owner',
      owner_party_ids: ['party-headquarters'],
      manager_party_ids: [],
      organization_id: 'org-1',
      source_organization_id: 'org-1',
      next_transition_at: null,
      error_code: null,
      issues: [],
    } satisfies UserOrganizationTransferPreview['before_scope'];
    const afterScope = {
      ...beforeScope,
      owner_party_ids: ['party-regional'],
      organization_id: 'org-2',
      source_organization_id: 'org-2',
    } satisfies UserOrganizationTransferPreview['after_scope'];
    const preview = {
      user_id: mockUser.id,
      before_scope: beforeScope,
      after_scope: afterScope,
      impact: {
        organization_changed: true,
        scope_changed: true,
        current_explicit_binding_count: 0,
        uses_explicit_party_scope_after: false,
        cache_invalidation_required: true,
      },
      preview_token: 'organization-preview-token-1',
      expires_at: '2026-08-06T08:10:00Z',
    } satisfies UserOrganizationTransferPreview;
    const commitResponse = {
      user_id: mockUser.id,
      organization_id: 'org-2',
      before_scope: beforeScope,
      after_scope: afterScope,
      impact: preview.impact,
      committed_at: '2026-08-06T08:01:00Z',
      idempotent: false,
    } satisfies UserOrganizationTransferCommitResponse;

    vi.mocked(useUserManagementData).mockReturnValue(
      buildHookResult({
        organizations: [
          { id: 'org-1', name: '总部' },
          { id: 'org-2', name: 'Regional Operations' },
        ],
      })
    );
    vi.spyOn(userService, 'previewUserOrganizationTransfer').mockResolvedValue(preview);
    vi.spyOn(userService, 'commitUserOrganizationTransfer').mockResolvedValue(commitResponse);

    renderWithProviders(<UserManagementPage />);

    fireEvent.click(screen.getByRole('button', { name: '调动用户组织zhangsan' }));
    const transferDialog = await screen.findByRole('dialog');
    const transferSelect = within(transferDialog).getByRole('combobox');
    fireEvent.mouseDown(transferSelect);
    fireEvent.click(await screen.findByText('Regional Operations'));

    fireEvent.click(within(transferDialog).getByRole('button', { name: '预览调动影响' }));
    await waitFor(() => {
      expect(userService.previewUserOrganizationTransfer).toHaveBeenCalledWith('user-1', {
        organization_id: 'org-2',
      });
    });

    fireEvent.click(within(transferDialog).getByRole('button', { name: '确认提交' }));
    expect(await screen.findByText('请填写变更原因')).toBeInTheDocument();
    expect(userService.commitUserOrganizationTransfer).not.toHaveBeenCalled();

    fireEvent.change(within(transferDialog).getByPlaceholderText('请填写本次组织调动的原因'), {
      target: { value: 'Move the user to the regional operations team.' },
    });
    fireEvent.click(within(transferDialog).getByRole('button', { name: '确认提交' }));

    await waitFor(() => {
      expect(userService.commitUserOrganizationTransfer).toHaveBeenCalledWith('user-1', {
        preview_token: 'organization-preview-token-1',
        reason: 'Move the user to the regional operations team.',
        idempotency_key: expect.any(String),
      });
    });
  }, 30_000);
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
