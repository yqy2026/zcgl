/**
 * Organization Service 单元测试
 * 测试组织架构管理服务的核心功能
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { organizationService } from '../organizationService';

const formatStderrWrites = (calls: unknown[][]) => calls.map(call => String(call[0] ?? '')).join(' ');

// =============================================================================
// Mock API client
// =============================================================================

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// =============================================================================
// Mock error handler
// =============================================================================

vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn(error => ({
      message: error instanceof Error ? error.message : 'Unknown error',
      code: 'UNKNOWN',
    })),
  },
}));

// =============================================================================
// Mock logger
// =============================================================================

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

import { apiClient } from '@/api/client';

// =============================================================================
// Test data
// =============================================================================

const mockOrganization = {
  id: 'org-1',
  name: '总公司',
  code: 'HQ',
  parent_id: null,
  level: 1,
  sort_order: 1,
  is_active: true,
  created_at: '2026-01-30T00:00:00Z',
  updated_at: '2026-01-30T00:00:00Z',
};

const mockChildOrganization = {
  id: 'org-2',
  name: '分公司A',
  code: 'BRANCH_A',
  parent_id: 'org-1',
  level: 2,
  sort_order: 1,
  is_active: true,
  created_at: '2026-01-30T00:00:00Z',
  updated_at: '2026-01-30T00:00:00Z',
};

// =============================================================================
// 基础CRUD测试
// =============================================================================

describe('OrganizationService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv('VITE_ENABLE_ORGANIZATION_WRITE', 'true');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe('getOrganizations', () => {
    it('should return organization list', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [mockOrganization, mockChildOrganization],
      });

      const result = await organizationService.getOrganizations();

      expect(result).toHaveLength(2);
      expect(apiClient.get).toHaveBeenCalledWith(
        '/organizations',
        expect.objectContaining({
          params: expect.objectContaining({ page: 1, page_size: 100 }),
        })
      );
    });

    it('should return empty array on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

      try {
        const result = await organizationService.getOrganizations();

        expect(result).toEqual([]);
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          '获取组织列表失败:',
          '获取组织列表失败: 获取失败'
        );
        expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain('获取组织列表失败');
      } finally {
        consoleErrorSpy.mockRestore();
        stderrWriteSpy.mockRestore();
      }
    });

    it('should support pagination', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [],
      });

      await organizationService.getOrganizations({ page: 2, page_size: 50 });

      expect(apiClient.get).toHaveBeenCalledWith(
        '/organizations',
        expect.objectContaining({
          params: expect.objectContaining({ page: 2, page_size: 50 }),
        })
      );
    });
  });

  describe('getOrganization', () => {
    it('should return organization by id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockOrganization,
      });

      const result = await organizationService.getOrganization('org-1');

      expect(result).toEqual(mockOrganization);
      expect(apiClient.get).toHaveBeenCalledWith('/organizations/org-1', expect.any(Object));
    });

    it('should throw error when not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '组织不存在',
      });

      await expect(organizationService.getOrganization('invalid')).rejects.toThrow();
    });
  });

  describe('createOrganization', () => {
    it('should create organization successfully', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: mockOrganization,
      });

      const result = await organizationService.createOrganization({
        name: '总公司',
        code: 'HQ',
      });

      expect(result).toEqual(mockOrganization);
      expect(apiClient.post).toHaveBeenCalledWith(
        '/organizations',
        { name: '总公司', code: 'HQ' },
        expect.any(Object)
      );
    });

    it('should throw error on creation failure', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '编码已存在',
      });

      await expect(
        organizationService.createOrganization({ name: '测试', code: 'TEST' })
      ).rejects.toThrow();
    });
  });

  describe('updateOrganization', () => {
    it('should update organization successfully', async () => {
      const updated = { ...mockOrganization, name: '新总公司' };
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: updated,
      });

      const result = await organizationService.updateOrganization('org-1', {
        name: '新总公司',
      });

      expect(result.name).toBe('新总公司');
    });

    it('should throw error on update failure', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: false,
        error: '更新失败',
      });

      await expect(
        organizationService.updateOrganization('org-1', { name: '测试' })
      ).rejects.toThrow();
    });
  });

  describe('deleteOrganization', () => {
    it('should delete organization successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
      });

      await expect(organizationService.deleteOrganization('org-1')).resolves.toBeUndefined();
    });

    it('should pass deletedBy parameter', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
      });

      await organizationService.deleteOrganization('org-1', 'admin');

      expect(apiClient.delete).toHaveBeenCalledWith(
        '/organizations/org-1',
        expect.objectContaining({
          params: { deleted_by: 'admin' },
        })
      );
    });

    it('should throw error on delete failure', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: false,
        error: '组织下存在子组织',
      });

      await expect(organizationService.deleteOrganization('org-1')).rejects.toThrow();
    });
  });

  describe('read-only guard', () => {
    it('should reject write operations when organization write is disabled', async () => {
      vi.stubEnv('VITE_ENABLE_ORGANIZATION_WRITE', 'false');

      await expect(
        organizationService.createOrganization({
          name: '只读组织',
          code: 'READ_ONLY',
          type: 'division',
          status: 'active',
        })
      ).rejects.toThrow(/只读模式/);
      await expect(
        organizationService.updateOrganization('org-1', {
          name: '只读更新',
        })
      ).rejects.toThrow(/只读模式/);
      await expect(organizationService.deleteOrganization('org-1')).rejects.toThrow(/只读模式/);
      await expect(
        organizationService.moveOrganization('org-1', {
          target_parent_id: 'org-root',
        })
      ).rejects.toThrow(/只读模式/);
      await expect(
        organizationService.importOrganizations(new File(['content'], 'organization.csv'))
      ).rejects.toThrow(/只读模式/);

      expect(apiClient.post).not.toHaveBeenCalled();
      expect(apiClient.put).not.toHaveBeenCalled();
      expect(apiClient.delete).not.toHaveBeenCalled();
    });
  });

  // =============================================================================
  // 组织树形结构测试
  // =============================================================================

  describe('getOrganizationTree', () => {
    it('should return organization tree', async () => {
      const mockTree = [
        {
          ...mockOrganization,
          children: [mockChildOrganization],
        },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockTree,
      });

      const result = await organizationService.getOrganizationTree();

      expect(result).toEqual(mockTree);
    });

    it('should return empty array on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

      try {
        const result = await organizationService.getOrganizationTree();

        expect(result).toEqual([]);
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          expect.stringContaining('获取组织树'),
          expect.stringContaining('获取失败')
        );
        expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain('获取组织树');
      } finally {
        consoleErrorSpy.mockRestore();
        stderrWriteSpy.mockRestore();
      }
    });

    it('should support parent_id filter', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [],
      });

      await organizationService.getOrganizationTree('org-1');

      expect(apiClient.get).toHaveBeenCalledWith(
        '/organizations/tree',
        expect.objectContaining({
          params: { parent_id: 'org-1' },
        })
      );
    });
  });

  describe('getOrganizationChildren', () => {
    it('should return child organizations', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [mockChildOrganization],
      });

      const result = await organizationService.getOrganizationChildren('org-1');

      expect(result).toHaveLength(1);
      expect(result[0].parent_id).toBe('org-1');
    });

    it('should support recursive option', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [],
      });

      await organizationService.getOrganizationChildren('org-1', true);

      expect(apiClient.get).toHaveBeenCalledWith(
        '/organizations/org-1/children',
        expect.objectContaining({
          params: { recursive: true },
        })
      );
    });
  });

  describe('getOrganizationPath', () => {
    it('should return organization path', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [mockOrganization, mockChildOrganization],
      });

      const result = await organizationService.getOrganizationPath('org-2');

      expect(result.organizations).toHaveLength(2);
      expect(result.path_string).toBe('总公司 > 分公司A');
    });
  });

  // =============================================================================
  // 搜索功能测试
  // =============================================================================

  describe('searchOrganizations', () => {
    it('should search organizations by keyword', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [mockOrganization],
      });

      const result = await organizationService.searchOrganizations('总公司');

      expect(result).toHaveLength(1);
      expect(apiClient.get).toHaveBeenCalledWith(
        '/organizations/search',
        expect.objectContaining({
          params: expect.objectContaining({ keyword: '总公司' }),
        })
      );
    });
  });

  describe('detailedSearchOrganizations', () => {
    it('should perform advanced search', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: [mockOrganization],
      });

      const searchCriteria = {
        name: '总公司',
        is_active: true,
      };

      const result = await organizationService.detailedSearchOrganizations(searchCriteria);

      expect(result).toHaveLength(1);
      expect(apiClient.post).toHaveBeenCalledWith(
        '/organizations/advanced-search',
        searchCriteria,
        expect.any(Object)
      );
    });
  });

  // =============================================================================
  // 统计功能测试
  // =============================================================================

  describe('getStatistics', () => {
    it('should return organization statistics', async () => {
      const mockStats = {
        total_count: 10,
        active_count: 8,
        inactive_count: 2,
        max_depth: 3,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockStats,
      });

      const result = await organizationService.getStatistics();

      expect(result).toEqual(mockStats);
    });
  });

  describe('getOrganizationHistory', () => {
    it('should return organization history', async () => {
      const mockHistory = [
        { id: 'h1', action: 'create', created_at: '2026-01-30T00:00:00Z' },
        { id: 'h2', action: 'update', created_at: '2026-01-30T01:00:00Z' },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockHistory,
      });

      const result = await organizationService.getOrganizationHistory('org-1');

      expect(result).toHaveLength(2);
    });
  });

  // =============================================================================
  // 组织操作测试
  // =============================================================================

  describe('moveOrganization', () => {
    it('should move organization successfully', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { success: true, message: '移动成功' },
      });

      const result = await organizationService.moveOrganization('org-2', {
        new_parent_id: 'org-3',
      });

      expect(result.success).toBe(true);
    });
  });

  describe('batchDeleteOrganizations', () => {
    it('should delete multiple organizations', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { success_count: 2, failed_count: 0 },
      });

      const result = await organizationService.batchDeleteOrganizations(['org-1', 'org-2']);

      expect(result.success_count).toBe(2);
    });
  });

  // =============================================================================
  // 工具方法测试
  // =============================================================================

  describe('buildOrganizationTreeData', () => {
    it('should build tree data from flat list', () => {
      const organizations = [mockOrganization, mockChildOrganization];

      const result = organizationService.buildOrganizationTreeData(organizations);

      expect(result).toHaveLength(1);
      expect(result[0].key).toBe('org-1');
      expect(result[0].title).toBe('总公司');
    });

    it('should handle empty list', () => {
      const result = organizationService.buildOrganizationTreeData([]);

      expect(result).toEqual([]);
    });
  });

  describe('getOrganizationLevelPath', () => {
    it('should return path array', () => {
      const organizations = [mockOrganization, mockChildOrganization];

      const result = organizationService.getOrganizationLevelPath(
        mockChildOrganization,
        organizations
      );

      expect(result).toEqual(['总公司', '分公司A']);
    });
  });

  describe('canMoveOrganization', () => {
    it('should return false when moving to itself', () => {
      const result = organizationService.canMoveOrganization('org-1', 'org-1', []);

      expect(result).toBe(false);
    });

    it('should return false when moving to descendant', () => {
      const organizations = [mockOrganization, mockChildOrganization];

      const result = organizationService.canMoveOrganization('org-1', 'org-2', organizations);

      expect(result).toBe(false);
    });

    it('should return true for valid move', () => {
      const thirdOrg = { ...mockOrganization, id: 'org-3', parent_id: null };
      const organizations = [mockOrganization, mockChildOrganization, thirdOrg];

      const result = organizationService.canMoveOrganization('org-2', 'org-3', organizations);

      expect(result).toBe(true);
    });
  });

  describe('getOrganizationDepth', () => {
    it('should return correct depth', () => {
      const organizations = [mockOrganization, mockChildOrganization];

      const depth1 = organizationService.getOrganizationDepth(mockOrganization, organizations);
      const depth2 = organizationService.getOrganizationDepth(mockChildOrganization, organizations);

      expect(depth1).toBe(1);
      expect(depth2).toBe(2);
    });
  });

  describe('getAllChildOrganizationIds', () => {
    it('should return all child ids recursively', () => {
      const grandChild = {
        ...mockChildOrganization,
        id: 'org-3',
        parent_id: 'org-2',
      };
      const organizations = [mockOrganization, mockChildOrganization, grandChild];

      const result = organizationService.getAllChildOrganizationIds('org-1', organizations);

      expect(result).toContain('org-2');
      expect(result).toContain('org-3');
    });
  });

  describe('validateOrganizationCode', () => {
    it('should return exists true when code is taken', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [mockOrganization],
      });

      const result = await organizationService.validateOrganizationCode('HQ');

      expect(result.exists).toBe(true);
    });

    it('should exclude specified id from check', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [mockOrganization],
      });

      const result = await organizationService.validateOrganizationCode('HQ', 'org-1');

      expect(result.exists).toBe(false);
    });
  });

  describe('getRootOrganizations', () => {
    it('should return only root organizations', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [mockOrganization, mockChildOrganization],
      });

      const result = await organizationService.getRootOrganizations();

      expect(result).toHaveLength(1);
      expect(result[0].parent_id).toBeNull();
    });
  });

  describe('findOrganizationByName', () => {
    it('should find organization by name', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [mockOrganization],
      });

      const result = await organizationService.findOrganizationByName('总公司');

      expect(result).toEqual(mockOrganization);
    });

    it('should return null when not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [],
      });

      const result = await organizationService.findOrganizationByName('不存在');

      expect(result).toBeNull();
    });
  });
});
