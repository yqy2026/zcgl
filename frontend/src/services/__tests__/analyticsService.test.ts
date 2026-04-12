/**
 * AnalyticsService 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AnalyticsService, analyticsService } from '../analyticsService';

// Mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
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

vi.mock('@/stores/dataScopeStore', () => ({
  useDataScopeStore: {
    getState: () => ({
      getEffectiveViewMode: () => 'owner',
    }),
  },
}));

import { apiClient } from '@/api/client';

describe('AnalyticsService', () => {
  let service: AnalyticsService;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
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
        params: {
          view_mode: 'owner',
        },
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
        params: {
          ...filters,
          view_mode: 'owner',
        },
      });
    });

    it('显式传入 view_mode 时附加到综合分析请求参数', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          area_summary: { total_assets: 50 },
        },
      });

      await service.getComprehensiveAnalytics({ project_id: 'proj_123' }, 'manager');

      expect(apiClient.get).toHaveBeenCalledWith('/analytics/comprehensive', {
        params: {
          project_id: 'proj_123',
          view_mode: 'manager',
        },
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

    it('保留客户统计拆分字段', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          area_summary: {
            total_assets: 10,
          },
          financial_summary: {},
          actual_receipts: '12345.67',
          collection_rate: null,
          customer_entity_breakdown: {
            upstream_lease: 1,
            downstream_sublease: 2,
            entrusted_operation: 3,
          },
          customer_contract_breakdown: {
            upstream_lease: 2,
            downstream_sublease: 4,
            entrusted_operation: 6,
          },
        },
      });

      const result = await service.getComprehensiveAnalytics();

      expect(result.data?.customer_entity_breakdown).toEqual({
        upstream_lease: 1,
        downstream_sublease: 2,
        entrusted_operation: 3,
      });
      expect(result.data?.actual_receipts).toBe(12345.67);
      expect(result.data?.collection_rate).toBeNull();
      expect(result.data?.customer_contract_breakdown).toEqual({
        upstream_lease: 2,
        downstream_sublease: 4,
        entrusted_operation: 6,
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

    it('默认使用当前 view_mode 请求基础统计', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          total_assets: 100,
          total_area: 50000,
        },
      });

      await service.getBasicStatistics({ project_id: 'proj_1' });

      expect(apiClient.get).toHaveBeenCalledWith(expect.any(String), {
        params: {
          project_id: 'proj_1',
          view_mode: 'owner',
        },
      });
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

  describe('exportAnalyticsReport', () => {
    it('passes date filters to backend export using date_from/date_to', async () => {
      const blob = new Blob(['csv']);
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: blob,
      });

      const result = await service.exportAnalyticsReport(
        'csv',
        {
          start_date: '2026-03-01',
          end_date: '2026-03-31',
          include_deleted: true,
        },
        'manager'
      );

      expect(apiClient.post).toHaveBeenCalledWith(
        '/analytics/export',
        undefined,
        expect.objectContaining({
          params: {
            export_format: 'csv',
            date_from: '2026-03-01',
            date_to: '2026-03-31',
            include_deleted: true,
            view_mode: 'manager',
          },
          responseType: 'blob',
          retry: false,
          smartExtract: false,
        })
      );
      expect(result).toBe(blob);
    });

    it('downloadAnalyticsReport downloads the blob using the shared filename rule', async () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2026-03-25T01:18:43.000Z'));

      const blob = new Blob(['xlsx']);
      vi.spyOn(service, 'exportAnalyticsReport').mockResolvedValue(blob);

      const anchor = document.createElement('a');
      const clickSpy = vi.fn();
      const removeSpy = vi.fn();
      anchor.click = clickSpy;
      anchor.remove = removeSpy;

      const originalCreateElement = document.createElement.bind(document);
      vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
        if (tagName === 'a') {
          return anchor;
        }
        return originalCreateElement(tagName);
      });

      global.URL.createObjectURL = vi.fn(() => 'blob:analytics');
      global.URL.revokeObjectURL = vi.fn();

      await service.downloadAnalyticsReport(
        'excel',
        {
          start_date: '2026-03-01',
          end_date: '2026-03-31',
        },
        'manager'
      );

      expect(service.exportAnalyticsReport).toHaveBeenCalledWith(
        'excel',
        {
          start_date: '2026-03-01',
          end_date: '2026-03-31',
        },
        'manager'
      );
      expect(global.URL.createObjectURL).toHaveBeenCalledWith(blob);
      expect(anchor.download).toBe('analytics_20260325T011843.xlsx');
      expect(clickSpy).toHaveBeenCalled();
      expect(removeSpy).toHaveBeenCalled();
      expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('blob:analytics');
    });

    it('does not create a blob URL when the backend export request fails', async () => {
      vi.spyOn(service, 'exportAnalyticsReport').mockRejectedValue(
        new Error('501 Not Implemented')
      );
      global.URL.createObjectURL = vi.fn(() => 'blob:analytics');
      global.URL.revokeObjectURL = vi.fn();

      await expect(
        service.downloadAnalyticsReport('excel', {
          start_date: '2026-03-01',
          end_date: '2026-03-31',
        })
      ).rejects.toThrow('501 Not Implemented');

      expect(global.URL.createObjectURL).not.toHaveBeenCalled();
      expect(global.URL.revokeObjectURL).not.toHaveBeenCalled();
    });
  });

  describe('全局实例', () => {
    it('导出的 analyticsService 实例存在', () => {
      expect(analyticsService).toBeDefined();
      expect(analyticsService).toBeInstanceOf(AnalyticsService);
    });
  });
});
