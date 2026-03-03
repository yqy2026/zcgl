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
    it('成功获取用户列表', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [
            { id: 'user_1', username: 'admin', email: 'admin@test.com' },
            { id: 'user_2', username: 'user', email: 'user@test.com' },
          ],
          total: 2,
          page: 1,
          page_size: 20,
          pages: 1,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await userService.getUsers({ page: 1, page_size: 20 });

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it('返回空数据时使用默认值', async () => {
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
    it('成功获取用户详情', async () => {
      const mockUser = {
        id: 'user_1',
        username: 'admin',
        email: 'admin@test.com',
        full_name: '管理员',
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockUser,
      });

      const result = await userService.getUser('user_1');

      expect(result.username).toBe('admin');
    });
  });

  describe('user party bindings', () => {
    it('成功获取用户主体绑定列表', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [
          {
            id: 'binding-1',
            user_id: 'user_1',
            party_id: 'party-1',
            relation_type: 'owner',
            is_primary: true,
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

    it('成功创建用户主体绑定', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: 'binding-1' },
      });

      const result = await userService.createUserPartyBinding('user_1', {
        party_id: 'party-1',
        relation_type: 'owner',
        is_primary: true,
      });

      expect(result?.id).toBe('binding-1');
      expect(apiClient.post).toHaveBeenCalledWith('/users/user_1/party-bindings', {
        party_id: 'party-1',
        relation_type: 'owner',
        is_primary: true,
      });
    });

    it('成功更新用户主体绑定', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: 'binding-1', is_primary: false },
      });

      const result = await userService.updateUserPartyBinding('user_1', 'binding-1', {
        is_primary: false,
      });

      expect(result?.is_primary).toBe(false);
      expect(apiClient.put).toHaveBeenCalledWith('/users/user_1/party-bindings/binding-1', {
        is_primary: false,
      });
    });

    it('成功关闭用户主体绑定', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
        data: { message: 'ok' },
      });

      const result = await userService.closeUserPartyBinding('user_1', 'binding-1');

      expect(result?.message).toBe('ok');
      expect(apiClient.delete).toHaveBeenCalledWith('/users/user_1/party-bindings/binding-1');
    });
  });

  describe('createUser', () => {
    it('成功创建用户', async () => {
      const newUser = {
        username: 'newuser',
        email: 'newuser@test.com',
        full_name: '新用户',
        password: 'password123',
        status: 'active' as const,
        role_id: 'role-user-id',
        default_organization_id: 'org_1',
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: 'user_new', ...newUser },
      });

      const result = await userService.createUser(newUser);

      expect(apiClient.post).toHaveBeenCalled();
      expect(result.id).toBe('user_new');
    });
  });

  describe('updateUser', () => {
    it('成功更新用户', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: 'user_1', full_name: '更新后的名称' },
      });

      const result = await userService.updateUser('user_1', { full_name: '更新后的名称' });

      expect(result.full_name).toBe('更新后的名称');
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
