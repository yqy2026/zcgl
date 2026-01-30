/**
 * OwnershipService 单元测试
 *
 * 测试权属方服务的核心功能
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { OwnershipService } from '../ownershipService';

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
    handleError: vi.fn((error) => ({
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

describe('OwnershipService', () => {
  let service: OwnershipService;

  beforeEach(() => {
    service = new OwnershipService();
    vi.clearAllMocks();
  });

  // ==========================================================================
  // 基础 CRUD 测试
  // ==========================================================================

  describe('getOwnerships', () => {
    it('should return ownership list on success', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [
            { id: '1', name: '权属方A', code: 'OWN-001' },
            { id: '2', name: '权属方B', code: 'OWN-002' },
          ],
          total: 2,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getOwnerships();

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it('should use default pagination', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 },
      });

      await service.getOwnerships();

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

      await service.getOwnerships({ keyword: '测试', is_active: true });

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ keyword: '测试', is_active: true }),
        })
      );
    });

    it('should throw error on API failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getOwnerships()).rejects.toThrow('获取权属方列表失败');
    });
  });

  describe('getOwnership', () => {
    it('should return ownership detail', async () => {
      const mockOwnership = {
        id: '1',
        name: '测试权属方',
        code: 'OWN-001',
        is_active: true,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockOwnership,
      });

      const result = await service.getOwnership('1');

      expect(result.name).toBe('测试权属方');
      expect(result.code).toBe('OWN-001');
    });

    it('should throw error when not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '权属方不存在',
      });

      await expect(service.getOwnership('999')).rejects.toThrow('获取权属方详情失败');
    });
  });

  describe('createOwnership', () => {
    it('should create ownership successfully', async () => {
      const newOwnership = {
        name: '新权属方',
        code: 'OWN-003',
        is_active: true,
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: '3', ...newOwnership },
      });

      const result = await service.createOwnership(newOwnership);

      expect(result.id).toBe('3');
      expect(result.name).toBe('新权属方');
    });

    it('should throw error on creation failure', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '编码重复',
      });

      await expect(
        service.createOwnership({ name: '测试', code: 'OWN-001' })
      ).rejects.toThrow('创建权属方失败');
    });
  });

  describe('updateOwnership', () => {
    it('should update ownership successfully', async () => {
      const updateData = { name: '更新后的名称' };

      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: '1', ...updateData },
      });

      const result = await service.updateOwnership('1', updateData);

      expect(result.name).toBe('更新后的名称');
    });
  });

  describe('deleteOwnership', () => {
    it('should delete ownership successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
        data: { message: '删除成功' },
      });

      const result = await service.deleteOwnership('1');

      expect(result.message).toBe('删除成功');
    });

    it('should throw error when delete fails', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: false,
        error: '存在关联资产',
      });

      await expect(service.deleteOwnership('1')).rejects.toThrow('删除权属方失败');
    });
  });

  // ==========================================================================
  // 搜索功能测试
  // ==========================================================================

  describe('searchOwnerships', () => {
    it('should search ownerships', async () => {
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

      const result = await service.searchOwnerships({ keyword: '测试' });

      expect(result.items).toHaveLength(1);
    });
  });

  describe('searchOwnershipsByKeyword', () => {
    it('should return ownerships matching keyword', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', name: '测试权属方' }],
          total: 1,
          page: 1,
          page_size: 100,
          pages: 1,
        },
      });

      const result = await service.searchOwnershipsByKeyword('测试');

      expect(result).toHaveLength(1);
    });

    it('should return empty array on error', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error('Network error'));

      const result = await service.searchOwnershipsByKeyword('测试');

      expect(result).toEqual([]);
    });
  });

  // ==========================================================================
  // 状态和统计测试
  // ==========================================================================

  describe('toggleOwnershipStatus', () => {
    it('should toggle status successfully', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: '1', is_active: false },
      });

      const result = await service.toggleOwnershipStatus('1');

      expect(result.is_active).toBe(false);
    });
  });

  describe('getOwnershipStatistics', () => {
    it('should return statistics', async () => {
      const mockStats = {
        total: 100,
        active: 80,
        inactive: 20,
        with_assets: 60,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockStats,
      });

      const result = await service.getOwnershipStatistics();

      expect(result.total).toBe(100);
      expect(result.active).toBe(80);
    });
  });

  // ==========================================================================
  // 选项列表测试
  // ==========================================================================

  describe('getOwnershipOptions', () => {
    it('should return dropdown options', async () => {
      const mockOptions = [
        { id: '1', name: '权属方A', code: 'OWN-001' },
        { id: '2', name: '权属方B', code: 'OWN-002' },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockOptions,
      });

      const result = await service.getOwnershipOptions();

      expect(result).toHaveLength(2);
    });

    it('should filter by active status', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [],
      });

      await service.getOwnershipOptions(false);

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('is_active=false'),
        expect.any(Object)
      );
    });
  });

  describe('getOwnershipSelectOptions', () => {
    it('should return formatted select options', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [{ id: '1', name: '权属方A', code: 'OWN-001' }],
      });

      const result = await service.getOwnershipSelectOptions();

      expect(result[0]).toEqual({
        value: '1',
        label: '权属方A (OWN-001)',
      });
    });

    it('should return empty array on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      const result = await service.getOwnershipSelectOptions();

      expect(result).toEqual([]);
    });
  });

  // ==========================================================================
  // 验证功能测试
  // ==========================================================================

  describe('validateOwnershipCode', () => {
    it('should return true when code is unique', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 },
      });

      const result = await service.validateOwnershipCode('NEW-001');

      expect(result).toBe(true);
    });

    it('should return false when code exists', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', code: 'OWN-001' }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.validateOwnershipCode('OWN-001');

      expect(result).toBe(false);
    });

    it('should exclude specific id when validating', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', code: 'OWN-001' }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.validateOwnershipCode('OWN-001', '1');

      expect(result).toBe(true);
    });
  });

  describe('validateOwnershipName', () => {
    it('should return true when name is unique', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 },
      });

      const result = await service.validateOwnershipName('新名称');

      expect(result).toBe(true);
    });
  });

  // ==========================================================================
  // 删除检查测试
  // ==========================================================================

  describe('canDeleteOwnership', () => {
    it('should return canDelete true when no assets', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { id: '1', name: '测试', asset_count: 0 },
      });

      const result = await service.canDeleteOwnership('1');

      expect(result.canDelete).toBe(true);
    });

    it('should return canDelete false when has assets', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { id: '1', name: '测试', asset_count: 5 },
      });

      const result = await service.canDeleteOwnership('1');

      expect(result.canDelete).toBe(false);
      expect(result.reason).toContain('5 个关联资产');
    });

    it('should handle not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '不存在',
      });

      const result = await service.canDeleteOwnership('999');

      expect(result.canDelete).toBe(false);
    });
  });

  // ==========================================================================
  // 活跃状态筛选测试
  // ==========================================================================

  describe('getActiveOwnerships', () => {
    it('should return only active ownerships', async () => {
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

      const result = await service.getActiveOwnerships();

      expect(result).toHaveLength(1);
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ is_active: true }),
        })
      );
    });
  });

  describe('getInactiveOwnerships', () => {
    it('should return only inactive ownerships', async () => {
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

      const result = await service.getInactiveOwnerships();

      expect(result).toHaveLength(1);
    });
  });

  // ==========================================================================
  // 计数测试
  // ==========================================================================

  describe('getOwnershipCount', () => {
    it('should return total count', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 50, page: 1, page_size: 1, pages: 50 },
      });

      const result = await service.getOwnershipCount();

      expect(result).toBe(50);
    });

    it('should return 0 on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      const result = await service.getOwnershipCount();

      expect(result).toBe(0);
    });
  });

  // ==========================================================================
  // 项目关联测试
  // ==========================================================================

  describe('updateOwnershipProjects', () => {
    it('should update associated projects', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: '1', project_ids: ['p1', 'p2'] },
      });

      await service.updateOwnershipProjects('1', ['p1', 'p2']);

      expect(apiClient.put).toHaveBeenCalledWith(
        expect.stringContaining('/projects'),
        ['p1', 'p2'],
        expect.any(Object)
      );
    });
  });

  // ==========================================================================
  // 导入导出测试
  // ==========================================================================

  describe('exportOwnerships', () => {
    it('should export to excel', async () => {
      const mockBlob = new Blob(['test'], { type: 'application/vnd.ms-excel' });

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockBlob,
      });

      const result = await service.exportOwnerships('excel');

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

      await service.exportOwnerships('csv');

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ format: 'csv' }),
        })
      );
    });
  });

  describe('importOwnerships', () => {
    it('should import from file', async () => {
      const mockFile = new File(['test'], 'test.xlsx', {
        type: 'application/vnd.ms-excel',
      });

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { success: true, message: '导入成功', imported: 10 },
      });

      const result = await service.importOwnerships(mockFile);

      expect(result.success).toBe(true);
      expect(result.imported).toBe(10);
    });

    it('should handle import errors', async () => {
      const mockFile = new File(['test'], 'test.xlsx');

      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '文件格式错误',
      });

      await expect(service.importOwnerships(mockFile)).rejects.toThrow(
        '导入权属方数据失败'
      );
    });
  });
});
