/**
 * SystemService 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  userService,
  roleService,
  logService,
  organizationService,
  systemService,
} from '../systemService';

// Mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock dayjs
vi.mock('dayjs', () => {
  const mockDayjs = (_date?: string) => ({
    format: () => '2026-01-30',
    isValid: () => true,
    isSame: () => true,
    diff: () => 30,
  });
  mockDayjs.default = mockDayjs;
  return { default: mockDayjs };
});

import { apiClient } from '@/api/client';

describe('userService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getUsers', () => {
    it('maps backend user records to the management view model', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [
            {
              id: 'user_1',
              username: 'admin',
              email: 'admin@test.com',
              full_name: 'Admin User',
              phone: '13800000000',
              roles: ['system_admin'],
              role_ids: ['role-admin'],
              is_active: true,
              is_locked: false,
              last_login_at: '2026-08-04T08:00:00Z',
              failed_login_attempts: 2,
              account_type: 'human',
              organization_id: 'org-1',
              created_at: '2026-08-01T08:00:00Z',
              updated_at: '2026-08-04T08:00:00Z',
            },
          ],
          pagination: {
            total: 1,
            page: 1,
            page_size: 20,
            total_pages: 1,
          },
        },
      });

      const result = await userService.getUsers({ page: 1, page_size: 20 });

      expect(result.items).toEqual([
        expect.objectContaining({
          id: 'user_1',
          status: 'active',
          organization_id: 'org-1',
          last_login: '2026-08-04T08:00:00Z',
          login_attempts: 2,
        }),
      ]);
      expect(result.total).toBe(1);
      expect(result.pages).toBe(1);
    });

    it('maps view filters to canonical backend query fields', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 20, pages: 0 },
      });

      await userService.getUsers({ organization_id: 'org-1', status: 'active' });

      expect(apiClient.get).toHaveBeenCalledWith('/auth/users', {
        params: { organization_id: 'org-1', is_active: true },
      });
    });

    it('uses an empty page when the backend returns no data', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: null,
      });

      const result = await userService.getUsers();

      expect(result.items).toEqual([]);
      expect(result.total).toBe(0);
    });
  });

  describe('getUser', () => {
    it('returns the requested user detail', async () => {
      const mockUser = {
        id: 'user_1',
        username: 'admin',
        email: 'admin@test.com',
        full_name: 'Admin User',
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockUser,
      });

      const result = await userService.getUser('user_1');

      expect(result.username).toBe('admin');
    });
  });

  describe('user Party bindings', () => {
    it('gets the current explicit bindings', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [
          {
            id: 'binding-1',
            user_id: 'user_1',
            party_id: 'party-1',
            relation_type: 'owner',
            valid_from: '2026-03-01T00:00:00Z',
            valid_to: null,
            created_at: '2026-03-01T00:00:00Z',
            updated_at: '2026-03-01T00:00:00Z',
          },
        ],
      });

      const result = await userService.getUserPartyBindings('user_1', { active_only: true });

      expect(result).toHaveLength(1);
      expect(apiClient.get).toHaveBeenCalledWith('/users/user_1/party-bindings', {
        params: { active_only: true },
      });
    });

    it('posts a user Party scope preview proposal', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { preview_token: 'preview-1', operation: 'create' },
      });

      const result = await userService.previewUserPartyScope('user_1', {
        operation: 'create',
        party_id: 'party-1',
        relation_type: 'owner',
      });

      expect(result?.preview_token).toBe('preview-1');
      expect(apiClient.post).toHaveBeenCalledWith('/users/user_1/party-bindings/preview', {
        operation: 'create',
        party_id: 'party-1',
        relation_type: 'owner',
      });
    });

    it('posts a confirmed user Party scope change', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: {
          binding: { id: 'binding-1' },
          operation: 'create',
          idempotent: false,
        },
      });

      const result = await userService.commitUserPartyScope('user_1', {
        preview_token: 'preview-1',
        reason: 'Assign the user to the approved owner Party.',
        idempotency_key: 'request-1',
      });

      expect(result?.binding.id).toBe('binding-1');
      expect(apiClient.post).toHaveBeenCalledWith('/users/user_1/party-bindings/commit', {
        preview_token: 'preview-1',
        reason: 'Assign the user to the approved owner Party.',
        idempotency_key: 'request-1',
      });
    });
  });

  describe('user organization transfer', () => {
    it('posts a user organization transfer preview proposal', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { preview_token: 'preview-organization-1' },
      });

      const result = await userService.previewUserOrganizationTransfer('user_1', {
        organization_id: 'organization-2',
      });

      expect(result?.preview_token).toBe('preview-organization-1');
      expect(apiClient.post).toHaveBeenCalledWith('/auth/users/user_1/organization/preview', {
        organization_id: 'organization-2',
      });
    });

    it('puts a confirmed user organization transfer', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: {
          user_id: 'user_1',
          organization_id: 'organization-2',
          idempotent: false,
        },
      });

      const result = await userService.commitUserOrganizationTransfer('user_1', {
        preview_token: 'preview-organization-1',
        reason: 'Move the user to the regional operations team.',
        idempotency_key: 'request-organization-1',
      });

      expect(result?.organization_id).toBe('organization-2');
      expect(apiClient.put).toHaveBeenCalledWith('/auth/users/user_1/organization', {
        preview_token: 'preview-organization-1',
        reason: 'Move the user to the regional operations team.',
        idempotency_key: 'request-organization-1',
      });
    });
  });
  describe('createUser', () => {
    it('创建用户时不发送由服务端控制的启用状态', async () => {
      const newUser = {
        username: 'newuser',
        email: 'newuser@test.com',
        full_name: '新用户',
        password: 'password123',
        status: 'active' as const,
        role_ids: ['role-user-id', 'role-reviewer-id'],
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: 'user_new', ...newUser },
      });

      const result = await userService.createUser(newUser);

      expect(apiClient.post).toHaveBeenCalledWith('/auth/users', {
        username: 'newuser',
        email: 'newuser@test.com',
        full_name: '新用户',
        password: 'password123',
        role_ids: ['role-user-id', 'role-reviewer-id'],
        role_id: 'role-user-id',
      });
      expect(result.id).toBe('user_new');
    });
  });

  describe('updateUser', () => {
    it('成功更新用户', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: 'user_1', full_name: '更新后的名称' },
      });

      const result = await userService.updateUser('user_1', {
        full_name: '更新后的名称',
        role_ids: ['role-user-id', 'role-reviewer-id'],
      });

      expect(apiClient.put).toHaveBeenCalledWith('/auth/users/user_1', {
        full_name: '更新后的名称',
        role_ids: ['role-user-id', 'role-reviewer-id'],
        role_id: 'role-user-id',
      });
      expect(result.full_name).toBe('更新后的名称');
    });

    it('将页面状态更新映射为后端 is_active 字段', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: 'user_1', is_active: false },
      });

      await userService.updateUser('user_1', { status: 'inactive' });

      expect(apiClient.put).toHaveBeenCalledWith('/auth/users/user_1', {
        is_active: false,
      });
    });
  });

  describe('deleteUser', () => {
    it('成功删除用户', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
        data: { deleted: true },
      });

      const result = await userService.deleteUser('user_1');

      expect(result.deleted).toBe(true);
    });
  });

  describe('lockUser / unlockUser', () => {
    it('成功锁定用户', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { locked: true },
      });

      const result = await userService.lockUser('user_1');

      expect(result.locked).toBe(true);
    });

    it('成功解锁用户', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { unlocked: true },
      });

      const result = await userService.unlockUser('user_1');

      expect(result.unlocked).toBe(true);
    });
  });
});

describe('roleService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getRoles', () => {
    it('成功获取角色列表', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [
            { id: 'role_1', name: 'admin', display_name: '管理员' },
            { id: 'role_2', name: 'user', display_name: '普通用户' },
          ],
          total: 2,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await roleService.getRoles();

      expect(result.items).toHaveLength(2);
    });
  });

  describe('createRole', () => {
    it('成功创建角色', async () => {
      const newRole = {
        name: 'editor',
        display_name: '编辑者',
        description: '可以编辑内容',
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: 'role_new', ...newRole },
      });

      const result = await roleService.createRole(newRole);

      expect(apiClient.post).toHaveBeenCalledWith('/roles', newRole, { retry: false });
      expect(result.id).toBe('role_new');
    });
  });

  describe('updateRolePermissions', () => {
    it('成功更新角色权限', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { updated: true },
      });

      const result = await roleService.updateRolePermissions('role_1', ['perm_1', 'perm_2']);

      expect(result.updated).toBe(true);
    });
  });

  describe('getPermissions', () => {
    it('成功获取权限列表', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [
          { id: 'perm_1', name: 'asset:read' },
          { id: 'perm_2', name: 'asset:write' },
        ],
      });

      const result = await roleService.getPermissions();

      expect(result).toHaveLength(2);
    });
  });
});

describe('logService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getLogs', () => {
    it('成功获取操作日志列表', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [
            { id: 'log_1', action: 'create', module: 'asset' },
            { id: 'log_2', action: 'update', module: 'contract' },
          ],
          total: 2,
          page: 1,
          page_size: 20,
          pages: 1,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await logService.getLogs({ page: 1 });

      expect(result.items).toHaveLength(2);
    });

    it('返回空数据时使用默认值', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        data: null,
      });

      const result = await logService.getLogs();

      expect(result.items).toEqual([]);
      expect(result.total).toBe(0);
    });
  });

  describe('getLogStatistics', () => {
    it('成功获取日志统计', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          total_logs: 1000,
          daily_statistics: {
            '2026-01-30': 50,
            '2026-01-29': 45,
          },
          error_statistics: {
            total_errors: 10,
          },
        },
      });

      const result = await logService.getLogStatistics({ days: 7 });

      expect(result.total).toBe(1000);
      expect(result.error_count).toBe(10);
    });

    it('返回空数据时使用默认值', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        data: null,
      });

      const result = await logService.getLogStatistics();

      expect(result.total).toBe(0);
      expect(result.error_count).toBe(0);
    });
  });
});

describe('organizationService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getOrganizationStatistics', () => {
    it('成功获取组织统计', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          total: 10,
          active: 8,
          inactive: 2,
        },
      });

      const result = await organizationService.getOrganizationStatistics();

      expect(result.total).toBe(10);
      expect(result.active).toBe(8);
    });

    it('返回空数据时使用默认值', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        data: null,
      });

      const result = await organizationService.getOrganizationStatistics();

      expect(result.total).toBe(0);
      expect(result.active).toBe(0);
    });
  });

  describe('getOrganizationMembers', () => {
    it('成功获取组织成员', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [
          { id: 'user_1', username: 'member1' },
          { id: 'user_2', username: 'member2' },
        ],
      });

      const result = await organizationService.getOrganizationMembers('org_1');

      expect(result).toHaveLength(2);
    });
  });
});

describe('systemService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getSettings', () => {
    it('成功获取系统设置', async () => {
      const mockSettings = {
        site_name: '资产管理系统',
        site_description: '企业资产管理平台',
        allow_registration: false,
        session_timeout: 3600,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockSettings,
      });

      const result = await systemService.getSettings();

      expect(result.site_name).toBe('资产管理系统');
    });

    it('获取失败时抛出错误', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '权限不足',
      });

      await expect(systemService.getSettings()).rejects.toThrow('权限不足');
    });
  });

  describe('getSystemInfo', () => {
    it('成功获取系统信息', async () => {
      const mockInfo = {
        version: '1.0.0',
        build_time: '2026-01-30T00:00:00Z',
        database_status: 'connected',
        api_version: 'v1',
        environment: 'production',
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockInfo,
      });

      const result = await systemService.getSystemInfo();

      expect(result.version).toBe('1.0.0');
      expect(result.environment).toBe('production');
    });
  });

  describe('updateSettings', () => {
    it('成功更新系统设置', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { updated: true },
      });

      const result = await systemService.updateSettings({
        site_name: '新系统名称',
      });

      expect(result.updated).toBe(true);
    });
  });

  describe('backupSystem', () => {
    it('成功创建系统备份', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { backup_id: 'backup_123' },
      });

      const result = await systemService.backupSystem();

      expect(result.backup_id).toBe('backup_123');
    });
  });
});
