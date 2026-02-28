import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DataPolicyService } from '../dataPolicyService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn(error => ({
      message: error instanceof Error ? error.message : String(error),
    })),
  },
}));

import { apiClient } from '@/api/client';

describe('DataPolicyService', () => {
  let service: DataPolicyService;

  beforeEach(() => {
    service = new DataPolicyService();
    vi.clearAllMocks();
  });

  it('gets role data policies by role id', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        role_id: 'role-1',
        policy_packages: ['dual_party_viewer'],
      },
    });

    const result = await service.getRoleDataPolicies('role-1');

    expect(result).toEqual({
      role_id: 'role-1',
      policy_packages: ['dual_party_viewer'],
    });
    expect(apiClient.get).toHaveBeenCalledWith(
      '/auth/roles/role-1/data-policies',
      expect.objectContaining({
        cache: false,
        smartExtract: true,
      })
    );
  });

  it('updates role data policies', async () => {
    vi.mocked(apiClient.put).mockResolvedValue({
      success: true,
      data: {
        role_id: 'role-1',
        policy_packages: ['platform_admin'],
      },
    });

    const result = await service.updateRoleDataPolicies('role-1', {
      policy_packages: ['platform_admin'],
    });

    expect(result.policy_packages).toEqual(['platform_admin']);
    expect(apiClient.put).toHaveBeenCalledWith(
      '/auth/roles/role-1/data-policies',
      { policy_packages: ['platform_admin'] },
      expect.objectContaining({
        smartExtract: true,
      })
    );
  });

  it('maps data policy templates record to list items', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        dual_party_viewer: {
          name: '双主体查看',
          description: '只读查看',
        },
        platform_admin: {
          name: '平台管理员',
          description: '全权限',
        },
      },
    });

    const result = await service.getDataPolicyTemplates();

    expect(result).toEqual([
      {
        code: 'dual_party_viewer',
        name: '双主体查看',
        description: '只读查看',
      },
      {
        code: 'platform_admin',
        name: '平台管理员',
        description: '全权限',
      },
    ]);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/auth/data-policies/templates',
      expect.objectContaining({
        cache: true,
        smartExtract: true,
      })
    );
  });

  it('throws normalized error when backend returns unsuccessful result', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: false,
      error: 'forbidden',
    });

    await expect(service.getRoleDataPolicies('role-2')).rejects.toThrow(
      '获取角色数据策略失败: forbidden'
    );
  });
});
