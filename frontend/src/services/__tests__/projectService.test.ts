/**
 * ProjectService 单元测试
 *
 * 测试项目服务的核心功能
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ProjectService } from '../projectService';

// Mock API client
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock error handler
vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn(error => ({
      message: error instanceof Error ? error.message : 'Unknown error',
      code: 'UNKNOWN',
    })),
  },
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

import { apiClient } from '@/api/client';

describe('ProjectService', () => {
  let service: ProjectService;

  beforeEach(() => {
    service = new ProjectService();
    vi.clearAllMocks();
  });

  // ==========================================================================
  // 基础 CRUD 测试
  // ==========================================================================

  describe('getProjects', () => {
    it('should return project list on success', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [
            { id: '1', name: '项目A', code: 'PRJ-001' },
            { id: '2', name: '项目B', code: 'PRJ-002' },
          ],
          total: 2,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getProjects();

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it('should use default pagination', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 },
      });

      await service.getProjects();

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ page: 1, page_size: 10 }),
        })
      );
    });

    it('should apply filters', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 },
      });

      await service.getProjects({ keyword: '测试', is_active: true, ownership_id: 'own-1' });

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({
            keyword: '测试',
            is_active: true,
            ownership_id: 'own-1',
          }),
        })
      );
    });

    it('should apply owner_party_id filter and keep legacy compatibility param', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 },
      });

      await service.getProjects({ owner_party_id: 'party-1' });

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({
            owner_party_id: 'party-1',
            ownership_id: 'party-1',
          }),
        })
      );
    });

    it('should throw error on API failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getProjects()).rejects.toThrow('获取项目列表失败');
    });
  });

  describe('getProject', () => {
    it('should return project detail', async () => {
      const mockProject = {
        id: '1',
        name: '测试项目',
        code: 'PRJ-001',
        is_active: true,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockProject,
      });

      const result = await service.getProject('1');

      expect(result.name).toBe('测试项目');
      expect(result.code).toBe('PRJ-001');
    });

    it('should throw error when not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '项目不存在',
      });

      await expect(service.getProject('999')).rejects.toThrow('获取项目详情失败');
    });
  });

  describe('createProject', () => {
    it('should create project successfully', async () => {
      const newProject = {
        name: '新项目',
        code: 'PRJ-003',
        is_active: true,
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: '3', ...newProject },
      });

      const result = await service.createProject(newProject);

      expect(result.id).toBe('3');
      expect(result.name).toBe('新项目');
    });

    it('should throw error on creation failure', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '编码重复',
      });

      await expect(service.createProject({ name: '测试', code: 'PRJ-001' })).rejects.toThrow(
        '创建项目失败'
      );
    });
  });

  describe('updateProject', () => {
    it('should update project successfully', async () => {
      const updateData = { name: '更新后的名称' };

      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: '1', ...updateData },
      });

      const result = await service.updateProject('1', updateData);

      expect(result.name).toBe('更新后的名称');
    });
  });

  describe('deleteProject', () => {
    it('should delete project successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
        data: { message: '删除成功' },
      });

      const result = await service.deleteProject('1');

      expect(result.message).toBe('删除成功');
    });

    it('should throw error when delete fails', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: false,
        error: '存在关联资产',
      });

      await expect(service.deleteProject('1')).rejects.toThrow('删除项目失败');
    });
  });

  // ==========================================================================
  // 搜索功能测试
  // ==========================================================================

  describe('searchProjects', () => {
    it('should search projects', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', name: '搜索结果' }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.searchProjects({ keyword: '测试' });

      expect(result.items).toHaveLength(1);
    });
  });

  describe('searchProjectsByKeyword', () => {
    it('should return projects matching keyword', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', name: '测试项目' }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.searchProjectsByKeyword('测试');

      expect(result).toHaveLength(1);
    });

    it('should return empty array on error', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error('Network error'));

      const result = await service.searchProjectsByKeyword('测试');

      expect(result).toEqual([]);
    });
  });

  // ==========================================================================
  // 状态和统计测试
  // ==========================================================================

  describe('toggleProjectStatus', () => {
    it('should toggle status successfully', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: '1', is_active: false },
      });

      const result = await service.toggleProjectStatus('1');

      expect(result.is_active).toBe(false);
    });
  });

  describe('getProjectStatistics', () => {
    it('should return statistics', async () => {
      const mockStats = {
        total: 50,
        active: 40,
        inactive: 10,
        total_assets: 200,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockStats,
      });

      const result = await service.getProjectStatistics();

      expect(result.total).toBe(50);
      expect(result.active).toBe(40);
    });
  });

  // ==========================================================================
  // 选项列表测试
  // ==========================================================================

  describe('getProjectOptions', () => {
    it('should return dropdown options', async () => {
      const mockOptions = [
        { id: '1', name: '项目A', code: 'PRJ-001' },
        { id: '2', name: '项目B', code: 'PRJ-002' },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockOptions,
      });

      const result = await service.getProjectOptions();

      expect(result).toHaveLength(2);
    });

    it('should filter by active status', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [],
      });

      await service.getProjectOptions(false);

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('is_active=false'),
        expect.any(Object)
      );
    });
  });

  describe('getProjectSelectOptions', () => {
    it('should return formatted select options', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [{ id: '1', name: '项目A', code: 'PRJ-001' }],
      });

      const result = await service.getProjectSelectOptions();

      expect(result[0]).toEqual({
        value: '1',
        label: '项目A (PRJ-001)',
      });
    });

    it('should return empty array on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      const result = await service.getProjectSelectOptions();

      expect(result).toEqual([]);
    });
  });

  // ==========================================================================
  // 验证功能测试
  // ==========================================================================

  describe('validateProjectCode', () => {
    it('should return true when code is unique', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 },
      });

      const result = await service.validateProjectCode('NEW-001');

      expect(result).toBe(true);
    });

    it('should return false when code exists', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', code: 'PRJ-001' }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.validateProjectCode('PRJ-001');

      expect(result).toBe(false);
    });

    it('should exclude specific id when validating', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', code: 'PRJ-001' }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.validateProjectCode('PRJ-001', '1');

      expect(result).toBe(true);
    });
  });

  describe('validateProjectName', () => {
    it('should return true when name is unique', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 },
      });

      const result = await service.validateProjectName('新名称');

      expect(result).toBe(true);
    });
  });

  // ==========================================================================
  // 删除检查测试
  // ==========================================================================

  describe('canDeleteProject', () => {
    it('should return canDelete true when no assets', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { id: '1', name: '测试', asset_count: 0 },
      });

      const result = await service.canDeleteProject('1');

      expect(result.canDelete).toBe(true);
    });

    it('should return canDelete false when has assets', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { id: '1', name: '测试', asset_count: 5 },
      });

      const result = await service.canDeleteProject('1');

      expect(result.canDelete).toBe(false);
      expect(result.reason).toContain('5 个关联资产');
    });

    it('should handle not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '不存在',
      });

      const result = await service.canDeleteProject('999');

      expect(result.canDelete).toBe(false);
    });
  });

  // ==========================================================================
  // 权属方筛选测试
  // ==========================================================================

  describe('getProjectsByOwnership', () => {
    it('should return projects for ownership', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', ownership_id: 'own-1' }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.getProjectsByOwnership('own-1');

      expect(result).toHaveLength(1);
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ ownership_id: 'own-1' }),
        })
      );
    });

    it('should return empty array on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      const result = await service.getProjectsByOwnership('own-1');

      expect(result).toEqual([]);
    });
  });

  describe('getProjectsByOwnerParty', () => {
    it('should return projects for owner party', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1' }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.getProjectsByOwnerParty('party-1');

      expect(result).toHaveLength(1);
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({
            owner_party_id: 'party-1',
            ownership_id: 'party-1',
          }),
        })
      );
    });
  });

  // ==========================================================================
  // 活跃状态筛选测试
  // ==========================================================================

  describe('getActiveProjects', () => {
    it('should return only active projects', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', is_active: true }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.getActiveProjects();

      expect(result).toHaveLength(1);
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ is_active: true }),
        })
      );
    });
  });

  describe('getInactiveProjects', () => {
    it('should return only inactive projects', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '2', is_active: false }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.getInactiveProjects();

      expect(result).toHaveLength(1);
    });
  });

  // ==========================================================================
  // 批量操作测试
  // ==========================================================================

  describe('getProjectsByIds', () => {
    it('should return multiple projects', async () => {
      vi.mocked(apiClient.get)
        .mockResolvedValueOnce({ success: true, data: { id: '1', is_active: true } })
        .mockResolvedValueOnce({ success: true, data: { id: '2', is_active: true } });

      const result = await service.getProjectsByIds(['1', '2']);

      expect(result).toHaveLength(2);
    });

    it('should filter out inactive projects', async () => {
      vi.mocked(apiClient.get)
        .mockResolvedValueOnce({ success: true, data: { id: '1', is_active: true } })
        .mockResolvedValueOnce({ success: true, data: { id: '2', is_active: false } });

      const result = await service.getProjectsByIds(['1', '2']);

      expect(result).toHaveLength(1);
    });
  });

  describe('batchDeleteProjects', () => {
    it('should delete multiple projects', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
        data: { message: '删除成功' },
      });

      const result = await service.batchDeleteProjects(['1', '2', '3']);

      expect(result.deleted).toBe(3);
      expect(result.errors).toHaveLength(0);
    });

    it('should handle partial failures', async () => {
      vi.mocked(apiClient.delete)
        .mockResolvedValueOnce({ success: true, data: { message: '成功' } })
        .mockResolvedValueOnce({ success: false, error: '删除失败' })
        .mockResolvedValueOnce({ success: true, data: { message: '成功' } });

      const result = await service.batchDeleteProjects(['1', '2', '3']);

      expect(result.deleted).toBe(2);
      expect(result.errors).toHaveLength(1);
    });
  });

  // ==========================================================================
  // 计数测试
  // ==========================================================================

  describe('getProjectCount', () => {
    it('should return total count', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 100, page: 1, page_size: 1, pages: 100 },
      });

      const result = await service.getProjectCount();

      expect(result).toBe(100);
    });

    it('should return 0 on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      const result = await service.getProjectCount();

      expect(result).toBe(0);
    });
  });

  // ==========================================================================
  // 导入导出测试
  // ==========================================================================

  describe('exportProjects', () => {
    it('should export to excel', async () => {
      const mockBlob = new Blob(['test'], { type: 'application/vnd.ms-excel' });

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockBlob,
      });

      const result = await service.exportProjects('excel');

      expect(result).toBeInstanceOf(Blob);
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/export'),
        expect.objectContaining({
          params: expect.objectContaining({ format: 'excel' }),
        })
      );
    });

    it('should export to csv', async () => {
      const mockBlob = new Blob(['test'], { type: 'text/csv' });

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockBlob,
      });

      await service.exportProjects('csv');

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ format: 'csv' }),
        })
      );
    });
  });

  describe('importProjects', () => {
    it('should import from file', async () => {
      const mockFile = new File(['test'], 'test.xlsx', {
        type: 'application/vnd.ms-excel',
      });

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { success: true, message: '导入成功', imported: 15 },
      });

      const result = await service.importProjects(mockFile);

      expect(result.success).toBe(true);
      expect(result.imported).toBe(15);
    });

    it('should handle import errors', async () => {
      const mockFile = new File(['test'], 'test.xlsx');

      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '文件格式错误',
      });

      await expect(service.importProjects(mockFile)).rejects.toThrow('导入项目数据失败');
    });
  });

  // ==========================================================================
  // 完整详情测试
  // ==========================================================================

  describe('getProjectFullDetails', () => {
    it('should return full project details', async () => {
      vi.mocked(apiClient.get)
        .mockResolvedValueOnce({
          success: true,
          data: { id: '1', name: '项目A', updated_at: '2026-01-30' },
        })
        .mockResolvedValueOnce({
          success: true,
          data: {
            projects: [{ id: '1', asset_count: 10, total_area: 5000 }],
          },
        });

      const result = await service.getProjectFullDetails('1');

      expect(result.project.name).toBe('项目A');
      expect(result.assetCount).toBe(10);
      expect(result.totalArea).toBe(5000);
    });

    it('should handle missing statistics', async () => {
      vi.mocked(apiClient.get)
        .mockResolvedValueOnce({
          success: true,
          data: { id: '1', name: '项目A', asset_count: 5, updated_at: '2026-01-30' },
        })
        .mockResolvedValueOnce({
          success: true,
          data: { projects: [] },
        });

      const result = await service.getProjectFullDetails('1');

      expect(result.assetCount).toBe(5);
      expect(result.totalArea).toBe(0);
    });
  });
});
