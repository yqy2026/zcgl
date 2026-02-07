/**
 * Statistics Service 单元测试
 * 测试统计服务的核心功能
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { StatisticsService, statisticsService } from '../statisticsService';

// =============================================================================
// Mock dependencies
// =============================================================================

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../../utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn(error => ({
      message: error instanceof Error ? error.message : 'Unknown error',
      code: 'UNKNOWN',
    })),
  },
}));

vi.mock('../../utils/logger', () => ({
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

const mockDashboardData = {
  totalAssets: 100,
  totalArea: 50000,
  occupancyRate: 85.5,
  monthlyRent: 1000000,
  alerts: [],
};

const mockBasicStatistics = {
  totalAssets: 100,
  totalArea: 50000,
  totalRentableArea: 45000,
  totalRentedArea: 38000,
  averageOccupancyRate: 84.4,
  categoryCount: { office: 50, retail: 30, warehouse: 20 },
  regionCount: { east: 40, west: 30, north: 30 },
};

const mockAreaStatistics = {
  landArea: 100000,
  totalPropertyArea: 80000,
  totalRentableArea: 70000,
  totalRentedArea: 60000,
  vacantArea: 10000,
  averageUnitPrice: 50,
  regionStats: {
    east: { area: 30000, rentableArea: 25000, rentedArea: 22000 },
    west: { area: 25000, rentableArea: 22000, rentedArea: 19000 },
  },
};

const mockChartData = [
  { name: '类型A', value: 100 },
  { name: '类型B', value: 200 },
  { name: '类型C', value: 150 },
];

const mockTrendData = [
  { date: '2026-01', value: 100 },
  { date: '2026-02', value: 120 },
  { date: '2026-03', value: 115 },
];

// =============================================================================
// Tests
// =============================================================================

describe('StatisticsService', () => {
  let service: StatisticsService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new StatisticsService();
  });

  // =============================================================================
  // getDashboardData 测试
  // =============================================================================

  describe('getDashboardData', () => {
    it('should return dashboard data successfully', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockDashboardData,
      });

      const result = await service.getDashboardData();

      expect(result).toEqual(mockDashboardData);
      expect(apiClient.get).toHaveBeenCalledWith(
        '/statistics/dashboard',
        expect.objectContaining({ cache: true })
      );
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getDashboardData()).rejects.toThrow();
    });
  });

  // =============================================================================
  // getBasicStatistics 测试
  // =============================================================================

  describe('getBasicStatistics', () => {
    it('should return basic statistics', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockBasicStatistics,
      });

      const result = await service.getBasicStatistics();

      expect(result).toEqual(mockBasicStatistics);
      expect(result.totalAssets).toBe(100);
      expect(result.averageOccupancyRate).toBe(84.4);
    });

    it('should pass filters to API', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockBasicStatistics,
      });

      const filters = { region: 'east', year: 2026 };
      await service.getBasicStatistics(filters);

      expect(apiClient.get).toHaveBeenCalledWith(
        '/statistics/basic',
        expect.objectContaining({
          params: filters,
        })
      );
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getBasicStatistics()).rejects.toThrow();
    });
  });

  // =============================================================================
  // getAreaStatistics 测试
  // =============================================================================

  describe('getAreaStatistics', () => {
    it('should return area statistics', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockAreaStatistics,
      });

      const result = await service.getAreaStatistics();

      expect(result).toEqual(mockAreaStatistics);
      expect(result.landArea).toBe(100000);
      expect(result.vacantArea).toBe(10000);
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getAreaStatistics()).rejects.toThrow();
    });
  });

  // =============================================================================
  // 分布数据测试
  // =============================================================================

  describe('getOwnershipDistribution', () => {
    it('should return ownership distribution', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockChartData,
      });

      const result = await service.getOwnershipDistribution();

      expect(result).toEqual(mockChartData);
    });

    it('should return empty array on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      const result = await service.getOwnershipDistribution();

      expect(result).toEqual([]);
    });
  });

  describe('getPropertyNatureDistribution', () => {
    it('should return property nature distribution', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockChartData,
      });

      const result = await service.getPropertyNatureDistribution();

      expect(result).toEqual(mockChartData);
    });

    it('should return empty array on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      const result = await service.getPropertyNatureDistribution();

      expect(result).toEqual([]);
    });
  });

  describe('getUsageStatusDistribution', () => {
    it('should return usage status distribution', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockChartData,
      });

      const result = await service.getUsageStatusDistribution();

      expect(result).toEqual(mockChartData);
    });

    it('should return empty array on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      const result = await service.getUsageStatusDistribution();

      expect(result).toEqual([]);
    });
  });

  describe('getOccupancyRateDistribution', () => {
    it('should return occupancy rate distribution', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { categories: mockChartData },
      });

      const result = await service.getOccupancyRateDistribution();

      expect(result).toEqual(mockChartData);
    });

    it('should return empty array when categories is null', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { categories: null },
      });

      const result = await service.getOccupancyRateDistribution();

      expect(result).toEqual([]);
    });
  });

  // =============================================================================
  // 趋势数据测试
  // =============================================================================

  describe('getTrendData', () => {
    it('should return trend data', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockTrendData,
      });

      const result = await service.getTrendData('occupancy', 'monthly');

      expect(result).toEqual(mockTrendData);
      expect(apiClient.get).toHaveBeenCalledWith(
        '/statistics/trend/occupancy',
        expect.objectContaining({
          params: expect.objectContaining({ period: 'monthly' }),
        })
      );
    });

    it('should use default period', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockTrendData,
      });

      await service.getTrendData('revenue');

      expect(apiClient.get).toHaveBeenCalledWith(
        '/statistics/trend/revenue',
        expect.objectContaining({
          params: expect.objectContaining({ period: 'monthly' }),
        })
      );
    });

    it('should return empty array on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      const result = await service.getTrendData('occupancy');

      expect(result).toEqual([]);
    });
  });

  describe('getMultipleTrends', () => {
    it('should return multiple trends', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockTrendData,
      });

      const result = await service.getMultipleTrends(['occupancy', 'revenue']);

      expect(result.occupancy).toEqual(mockTrendData);
      expect(result.revenue).toEqual(mockTrendData);
    });

    it('should handle partial failures', async () => {
      vi.mocked(apiClient.get)
        .mockResolvedValueOnce({ success: true, data: mockTrendData })
        .mockResolvedValueOnce({ success: false, error: '失败' });

      const result = await service.getMultipleTrends(['occupancy', 'revenue']);

      expect(result.occupancy).toEqual(mockTrendData);
      expect(result.revenue).toEqual([]);
    });
  });

  // =============================================================================
  // 对比分析测试
  // =============================================================================

  describe('getComparisonData', () => {
    it('should return comparison data', async () => {
      const mockComparison = {
        categories: ['Q1', 'Q2', 'Q3'],
        series: [{ name: '2025', data: [100, 120, 130] }],
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockComparison,
      });

      const result = await service.getComparisonData('revenue', 'period');

      expect(result).toEqual(mockComparison);
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getComparisonData('revenue', 'period')).rejects.toThrow();
    });
  });

  describe('getPeriodComparison', () => {
    it('should calculate growth rate correctly', async () => {
      vi.mocked(apiClient.get)
        .mockResolvedValueOnce({
          success: true,
          data: [{ date: '2026-01', value: 120 }],
        })
        .mockResolvedValueOnce({
          success: true,
          data: [{ date: '2025-01', value: 100 }],
        });

      const result = await service.getPeriodComparison('revenue', '2026-Q1', '2025-Q1');

      expect(result.growth).toBe(20); // (120 - 100) / 100 * 100 = 20%
    });

    it('should handle zero previous value', async () => {
      vi.mocked(apiClient.get)
        .mockResolvedValueOnce({
          success: true,
          data: [{ date: '2026-01', value: 100 }],
        })
        .mockResolvedValueOnce({
          success: true,
          data: [],
        });

      const result = await service.getPeriodComparison('revenue', '2026-Q1', '2025-Q1');

      expect(result.growth).toBe(0);
    });
  });

  // =============================================================================
  // 报表生成测试
  // =============================================================================

  describe('generateReport', () => {
    it('should generate report successfully', async () => {
      const mockResponse = {
        reportId: 'report-123',
        status: 'queued' as const,
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: mockResponse,
      });

      const result = await service.generateReport('monthly', {}, 'excel');

      expect(result).toEqual(mockResponse);
      expect(apiClient.post).toHaveBeenCalledWith(
        '/statistics/report/monthly',
        { filters: {}, format: 'excel' },
        expect.any(Object)
      );
    });

    it('should use default format', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { reportId: '123', status: 'queued' },
      });

      await service.generateReport('monthly');

      expect(apiClient.post).toHaveBeenCalledWith(
        '/statistics/report/monthly',
        expect.objectContaining({ format: 'json' }),
        expect.any(Object)
      );
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '生成失败',
      });

      await expect(service.generateReport('monthly')).rejects.toThrow();
    });
  });

  describe('getReportStatus', () => {
    it('should return report status', async () => {
      const mockStatus = {
        reportId: 'report-123',
        status: 'completed' as const,
        downloadUrl: '/download/123',
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockStatus,
      });

      const result = await service.getReportStatus('report-123');

      expect(result).toEqual(mockStatus);
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getReportStatus('invalid')).rejects.toThrow();
    });
  });

  describe('downloadReport', () => {
    it('should return blob', async () => {
      const mockBlob = new Blob(['test'], { type: 'application/pdf' });

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockBlob,
      });

      const result = await service.downloadReport('report-123');

      expect(result).toBeInstanceOf(Blob);
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '下载失败',
      });

      await expect(service.downloadReport('invalid')).rejects.toThrow();
    });
  });

  // =============================================================================
  // 高级统计功能测试
  // =============================================================================

  describe('getAssetRankings', () => {
    it('should return asset rankings', async () => {
      const mockRankings = [
        { name: '资产A', value: 1000, rank: 1 },
        { name: '资产B', value: 800, rank: 2 },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockRankings,
      });

      const result = await service.getAssetRankings('area', 10);

      expect(result).toEqual(mockRankings);
    });

    it('should return empty array on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      const result = await service.getAssetRankings('area');

      expect(result).toEqual([]);
    });
  });

  describe('getRegionalComparison', () => {
    it('should return regional comparison', async () => {
      const mockData = {
        regions: ['东区', '西区'],
        metrics: { area: [1000, 800], rent: [50000, 40000] },
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockData,
      });

      const result = await service.getRegionalComparison();

      expect(result).toEqual(mockData);
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getRegionalComparison()).rejects.toThrow();
    });
  });

  describe('getPerformanceSummary', () => {
    it('should return performance summary', async () => {
      const mockSummary = {
        totalAssets: 100,
        totalArea: 50000,
        averageOccupancyRate: 85,
        averageRent: 50,
        revenueGrowth: 10,
        efficiency: 0.9,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockSummary,
      });

      const result = await service.getPerformanceSummary();

      expect(result).toEqual(mockSummary);
    });

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getPerformanceSummary()).rejects.toThrow();
    });
  });

  describe('batchGetStatistics', () => {
    it('should return all statistics', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockChartData,
      });

      const result = await service.batchGetStatistics();

      expect(result).toHaveProperty('distributions');
      expect(result.distributions).toHaveProperty('ownership');
      expect(result.distributions).toHaveProperty('propertyNature');
    });

    it('should handle partial failures gracefully', async () => {
      vi.mocked(apiClient.get)
        .mockResolvedValueOnce({ success: false }) // dashboard
        .mockResolvedValueOnce({ success: true, data: mockBasicStatistics })
        .mockResolvedValueOnce({ success: true, data: mockAreaStatistics })
        .mockResolvedValue({ success: true, data: mockChartData });

      const result = await service.batchGetStatistics();

      expect(result.basic).toEqual(mockBasicStatistics);
      expect(result.area).toEqual(mockAreaStatistics);
    });
  });

  // =============================================================================
  // 单例导出测试
  // =============================================================================

  describe('statisticsService singleton', () => {
    it('should export singleton instance', () => {
      expect(statisticsService).toBeInstanceOf(StatisticsService);
    });
  });
});
