/**
 * Asset Service 单元测试
 *
 * 测试资产服务的核心 CRUD 操作
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AssetCoreService } from '../asset/assetCoreService';

// Mock API client
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    invalidateCacheByPrefix: vi.fn(),
  },
}));

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnershipSelectOptions: vi.fn(),
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

import { apiClient } from '@/api/client';
import { ownershipService } from '@/services/ownershipService';

describe('AssetCoreService', () => {
  let service: AssetCoreService;

  beforeEach(() => {
    service = new AssetCoreService();
    vi.clearAllMocks();
  });

  // ==========================================================================
  // getAssets 测试
  // ==========================================================================

  describe('getAssets', () => {
    it('should return asset list on success', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [
            { id: '1', name: '资产1', asset_code: 'A001' },
            { id: '2', name: '资产2', asset_code: 'A002' },
          ],
          total: 2,
          page: 1,
          page_size: 20,
          pages: 1,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getAssets({ page: 1, page_size: 20 });

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(2);
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ page: 1, page_size: 20 }),
        })
      );
    });

    it('should convert decimal string fields in list items', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [
            {
              id: '1',
              name: '资产1',
              land_area: '123.45',
              monthly_rent: '8888.00',
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
          pages: 1,
        },
      });

      const result = await service.getAssets({ page: 1, page_size: 20 });
      const firstItem = result.items[0] as unknown as {
        land_area: number;
        monthly_rent: number;
      };

      expect(firstItem.land_area).toBe(123.45);
      expect(firstItem.monthly_rent).toBe(8888);
    });

    it('should use default pagination when not provided', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          pages: 0,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      await service.getAssets();

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ page: 1, page_size: 20 }),
        })
      );
    });

    it('should send both owner_party_id and ownership_id when owner filter uses owner_party_id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          pages: 0,
        },
      });

      await service.getAssets({ owner_party_id: 'party-1' });

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

    it('should send both owner_party_id and ownership_id when owner filter uses ownership_id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          pages: 0,
        },
      });

      await service.getAssets({ ownership_id: 'party-legacy' });

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({
            owner_party_id: 'party-legacy',
            ownership_id: 'party-legacy',
          }),
        })
      );
    });

    it('should return empty list when API returns success false', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getAssets()).rejects.toThrow('获取资产列表失败');
    });

    it('should handle API error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      await expect(service.getAssets()).rejects.toThrow();
    });
  });

  // ==========================================================================
  // getAsset 测试
  // ==========================================================================

  describe('getAsset', () => {
    it('should return asset detail on success', async () => {
      const mockAsset = {
        id: '1',
        name: '测试资产',
        asset_code: 'A001',
        building_area: 100.5,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockAsset,
      });

      const result = await service.getAsset('1');

      expect(result).toEqual(mockAsset);
      expect(result.id).toBe('1');
    });

    it('should convert decimal string fields in asset detail', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          id: '1',
          name: '测试资产',
          land_area: '1000.50',
          rentable_area: '800.25',
          total_deposit: '50000.00',
        },
      });

      const result = await service.getAsset('1');
      const convertedAsset = result as unknown as {
        land_area: number;
        rentable_area: number;
        total_deposit: number;
      };

      expect(convertedAsset.land_area).toBe(1000.5);
      expect(convertedAsset.rentable_area).toBe(800.25);
      expect(convertedAsset.total_deposit).toBe(50000);
    });

    it('should throw error when asset not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '资产不存在',
      });

      await expect(service.getAsset('999')).rejects.toThrow('获取资产详情失败');
    });
  });

  // ==========================================================================
  // getAssetLeaseSummary 测试
  // ==========================================================================

  describe('getAssetLeaseSummary', () => {
    it('should return lease summary on success', async () => {
      const mockSummary = {
        asset_id: 'asset-1',
        period_start: '2026-03-01',
        period_end: '2026-03-31',
        total_contracts: 2,
        total_rented_area: 1000,
        rentable_area: 1200,
        occupancy_rate: 83.33,
        by_type: [],
        customer_summary: [],
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockSummary,
      });

      const result = await service.getAssetLeaseSummary('asset-1', {
        period_start: '2026-03-01',
        period_end: '2026-03-31',
      });

      expect(result).toEqual(mockSummary);
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/assets/asset-1/lease-summary'),
        expect.objectContaining({
          params: {
            period_start: '2026-03-01',
            period_end: '2026-03-31',
          },
        })
      );
    });

    it('should throw error when lease summary request fails', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '资产租赁汇总不存在',
      });

      await expect(service.getAssetLeaseSummary('missing')).rejects.toThrow('获取资产租赁汇总失败');
    });
  });

  // ==========================================================================
  // createAsset 测试
  // ==========================================================================

  describe('createAsset', () => {
    it('should create asset successfully', async () => {
      const newAsset = {
        name: '新资产',
        asset_code: 'A003',
        building_area: 200,
      };

      const createdAsset = {
        id: '3',
        ...newAsset,
        created_at: '2026-01-30T00:00:00Z',
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: createdAsset,
      });

      const result = await service.createAsset(newAsset);

      expect(result.id).toBe('3');
      expect(result.name).toBe('新资产');
      expect(apiClient.post).toHaveBeenCalledWith(expect.any(String), newAsset, expect.any(Object));
    });

    it('should throw error on creation failure', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '资产编码重复',
      });

      await expect(service.createAsset({ name: '测试', asset_code: 'A001' })).rejects.toThrow(
        '创建资产失败'
      );
    });
  });

  // ==========================================================================
  // updateAsset 测试
  // ==========================================================================

  describe('updateAsset', () => {
    it('should update asset successfully', async () => {
      const updateData = { name: '更新后的名称' };
      const updatedAsset = {
        id: '1',
        name: '更新后的名称',
        asset_code: 'A001',
        updated_at: '2026-01-30T00:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: updatedAsset,
      });

      const result = await service.updateAsset('1', updateData);

      expect(result.name).toBe('更新后的名称');
      expect(apiClient.put).toHaveBeenCalledWith(
        expect.stringContaining('1'),
        updateData,
        expect.any(Object)
      );
    });

    it('should throw error when update fails', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: false,
        error: '更新失败',
      });

      await expect(service.updateAsset('1', { name: '测试' })).rejects.toThrow('更新资产失败');
    });
  });

  // ==========================================================================
  // deleteAsset 测试
  // ==========================================================================

  describe('deleteAsset', () => {
    it('should delete asset successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
      });

      await expect(service.deleteAsset('1')).resolves.toBeUndefined();
      expect(apiClient.delete).toHaveBeenCalled();
    });

    it('should throw error when delete fails', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: false,
        error: '资产正在使用中',
      });

      await expect(service.deleteAsset('1')).rejects.toThrow('删除资产失败');
    });
  });

  // ==========================================================================
  // deleteAssets (批量删除) 测试
  // ==========================================================================

  describe('deleteAssets', () => {
    it('should delete multiple assets successfully', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
      });

      await expect(service.deleteAssets(['1', '2', '3'])).resolves.toBeUndefined();
      expect(apiClient.post).toHaveBeenCalledWith(
        expect.stringContaining('/batch-delete'),
        { asset_ids: ['1', '2', '3'] },
        expect.any(Object)
      );
    });

    it('should throw error when batch delete fails', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '部分资产删除失败',
      });

      await expect(service.deleteAssets(['1', '2'])).rejects.toThrow('批量删除资产失败');
    });
  });

  // ==========================================================================
  // getAssetsByIds 测试
  // ==========================================================================

  describe('getAssetsByIds', () => {
    it('should return assets by ids', async () => {
      const mockAssets = [
        { id: '1', name: '资产1' },
        { id: '2', name: '资产2' },
      ];

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: mockAssets,
      });

      const result = await service.getAssetsByIds(['1', '2']);

      expect(result).toHaveLength(2);
      expect(apiClient.post).toHaveBeenCalledWith(
        expect.stringContaining('by-ids'),
        { ids: ['1', '2'] },
        expect.any(Object)
      );
    });

    it('should include relations when requested', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: [],
      });

      await service.getAssetsByIds(['1'], { includeRelations: true });

      expect(apiClient.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({
          params: { include_relations: true },
        })
      );
    });
  });

  // ==========================================================================
  // searchAssets 测试
  // ==========================================================================

  describe('searchAssets', () => {
    it('should search assets with query', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [{ id: '1', name: '办公楼A' }],
          total: 1,
          page: 1,
          page_size: 20,
          pages: 1,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.searchAssets('办公楼');

      expect(result.items).toHaveLength(1);
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ search: '办公楼' }),
        })
      );
    });

    it('should apply filters when searching', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 20, pages: 0 },
      });

      await service.searchAssets('测试', { ownership_id: 'own-1' });

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({
            search: '测试',
            ownership_id: 'own-1',
          }),
        })
      );
    });
  });

  // ==========================================================================
  // validateAsset 测试
  // ==========================================================================

  describe('validateAsset', () => {
    it('should return valid result', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: {
          is_valid: true,
          errors: [],
          warnings: [],
        },
      });

      const result = await service.validateAsset({ name: '测试资产' });

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should return validation errors', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: {
          is_valid: false,
          errors: [
            { field: 'name', message: '名称不能为空' },
            { field: 'asset_code', message: '编码格式错误' },
          ],
          warnings: [],
        },
      });

      const result = await service.validateAsset({ name: '' });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('名称不能为空');
      expect(result.errors).toContain('编码格式错误');
    });

    it('should handle API failure gracefully', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '验证服务不可用',
      });

      const result = await service.validateAsset({ name: '测试' });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('验证服务不可用');
    });
  });

  // ==========================================================================
  // getOwnershipEntities 测试
  // ==========================================================================

  describe('getOwnershipEntities', () => {
    it('should return ownership entities list', async () => {
      const mockEntities = [
        { value: 'own-1', label: '公司A' },
        { value: 'own-2', label: '公司B' },
        { value: 'own-3', label: '公司C' },
      ];
      vi.mocked(ownershipService.getOwnershipSelectOptions).mockResolvedValue(mockEntities);

      const result = await service.getOwnershipEntities();

      expect(result).toEqual(mockEntities);
      expect(result).toHaveLength(3);
    });

    it('should return empty array when no entities', async () => {
      vi.mocked(ownershipService.getOwnershipSelectOptions).mockResolvedValue([]);

      const result = await service.getOwnershipEntities();

      expect(result).toEqual([]);
    });
  });

  // ==========================================================================
  // getBusinessCategories 测试
  // ==========================================================================

  describe('getBusinessCategories', () => {
    it('should return business categories', async () => {
      const mockCategories = ['办公', '商业', '住宅'];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockCategories,
      });

      const result = await service.getBusinessCategories();

      expect(result).toEqual(mockCategories);
    });
  });

  // ==========================================================================
  // getManagementEntities 测试
  // ==========================================================================

  describe('getManagementEntities', () => {
    it('should return management entities', async () => {
      const mockEntities = ['物业公司A', '物业公司B'];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockEntities,
      });

      const result = await service.getManagementEntities();

      expect(result).toEqual(mockEntities);
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getManagementEntities()).rejects.toThrow('获取管理实体列表失败');
    });
  });

  // ==========================================================================
  // getAllAssets 测试
  // ==========================================================================

  describe('getAllAssets', () => {
    it('should return all assets without pagination', async () => {
      const mockAssets = Array.from({ length: 100 }, (_, i) => ({
        id: String(i + 1),
        name: `资产${i + 1}`,
      }));

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockAssets,
      });

      const result = await service.getAllAssets();

      expect(result).toHaveLength(100);
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/all'),
        expect.objectContaining({
          params: expect.objectContaining({ page_size: 10000 }),
        })
      );
    });

    it('should apply filters when getting all assets', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [],
      });

      await service.getAllAssets({ ownership_id: 'own-1' });

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ ownership_id: 'own-1' }),
        })
      );
    });

    it('should keep owner filter compatibility in all-assets endpoint', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [],
      });

      await service.getAllAssets({ owner_party_id: 'party-2' });

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({
            owner_party_id: 'party-2',
            ownership_id: 'party-2',
          }),
        })
      );
    });
  });
});
