/**
 * AnalyticsService 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AnalyticsService, analyticsService } from '../analyticsService';

// Mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  }),
}));

import { apiClient } from '@/api/client';

describe('AnalyticsService', () => {
  let service: AnalyticsService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new AnalyticsService();
  });

  describe('getComprehensiveAnalytics', () => {
    it('成功获取综合分析数据', async () => {
      const mockResponse = {
        success: true,
        data: {
          area_summary: {
            total_assets: 100,
            total_area: 50000,
            total_rentable_area: 40000,
            total_rented_area: 35000,
            total_unrented_area: 5000,
            assets_with_area_data: 95,
            occupancy_rate: 87.5,
            total_non_commercial_area: 10000,
          },
          financial_summary: {
            estimated_annual_income: 1000000,
            total_annual_income: 900000,
            total_annual_expense: 100000,
            total_net_income: 800000,
            total_monthly_rent: 75000,
            total_deposit: 150000,
            assets_with_income_data: 80,
            assets_with_rent_data: 75,
            profit_margin: 80,
          },
          property_nature_distribution: [],
          ownership_status_distribution: [],
          usage_status_distribution: [],
          business_category_distribution: [],
          occupancy_trend: [],
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getComprehensiveAnalytics();

      expect(apiClient.get).toHaveBeenCalledWith('/analytics/comprehensive', {
        params: undefined,
      });
      expect(result).toBeDefined();
    });

    it('带筛选参数获取数据', async () => {
      const mockResponse = {
        success: true,
        data: {
          area_summary: { total_assets: 50 },
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const filters = { project_id: 'proj_123' };
      await service.getComprehensiveAnalytics(filters);

      expect(apiClient.get).toHaveBeenCalledWith('/analytics/comprehensive', {
        params: filters,
      });
    });

    it('API 返回失败时抛出错误', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '服务器错误',
      });

      await expect(service.getComprehensiveAnalytics()).rejects.toThrow('服务器错误');
    });

    it('API 返回空数据时抛出错误', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: null,
      });

      await expect(service.getComprehensiveAnalytics()).rejects.toThrow('综合分析接口返回为空');
    });

    it('适配原始 API 数据格式', async () => {
      const rawApiData = {
        success: true,
        data: {
          area_summary: {
            total_assets: 100,
            total_land_area: 50000,
            overall_occupancy_rate: 85,
          },
          financial_summary: {
            estimated_annual_income: 1000000,
          },
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(rawApiData);

      const result = await service.getComprehensiveAnalytics();

      expect(result.success).toBe(true);
      expect(result.data?.area_summary.total_assets).toBe(100);
    });

    it('将金额和面积字符串转换为数字', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          area_summary: {
            total_assets: 10,
            total_land_area: '50000.75',
            total_rentable_area: '42000.50',
            occupancy_rate: '84.25',
          },
          financial_summary: {
            total_monthly_rent: '75000.30',
            total_deposit: '150000.40',
          },
          business_category_distribution: [
            {
              category: '办公',
              count: '6',
              occupancy_rate: '80.5',
              avg_annual_income: '120000.75',
            },
          ],
        },
      });

      const result = await service.getComprehensiveAnalytics();
      const analyticsData = result.data;

      expect(analyticsData?.area_summary.total_area).toBe(50000.75);
      expect(analyticsData?.area_summary.total_rentable_area).toBe(42000.5);
      expect(analyticsData?.area_summary.occupancy_rate).toBe(84.25);
      expect(analyticsData?.financial_summary.total_monthly_rent).toBe(75000.3);
      expect(analyticsData?.financial_summary.total_deposit).toBe(150000.4);
      expect(analyticsData?.business_category_distribution[0]).toEqual({
        category: '办公',
        count: 6,
        occupancy_rate: 80.5,
        avg_annual_income: 120000.75,
      });
    });
  });

  describe('getBasicStatistics', () => {
    it('成功获取基础统计数据', async () => {
      const mockResponse = {
        success: true,
        data: {
          total_assets: 100,
          total_area: 50000,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getBasicStatistics();

      expect(result).toBeDefined();
    });

    it('API 失败时抛出错误', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getBasicStatistics()).rejects.toThrow();
    });
  });

  describe('getAreaSummary', () => {
    it('成功获取面积汇总', async () => {
      const mockResponse = {
        success: true,
        data: {
          total_area: 50000,
          total_rentable_area: 40000,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getAreaSummary();

      expect(result).toBeDefined();
    });

    it('API 失败时抛出错误', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getAreaSummary()).rejects.toThrow();
    });
  });

  describe('getFinancialSummary', () => {
    it('成功获取财务汇总', async () => {
      const mockResponse = {
        success: true,
        data: {
          total_annual_income: 1000000,
          total_net_income: 800000,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getFinancialSummary();

      expect(result).toBeDefined();
    });

    it('API 失败时抛出错误', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      await expect(service.getFinancialSummary()).rejects.toThrow();
    });
  });

  describe('全局实例', () => {
    it('导出的 analyticsService 实例存在', () => {
      expect(analyticsService).toBeDefined();
      expect(analyticsService).toBeInstanceOf(AnalyticsService);
    });
  });
});
