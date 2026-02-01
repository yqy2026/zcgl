/**
 * MSW API Handlers 统一管理 - 更新版
 *
 * 修复内容：
 * - 添加 /statistics/* 端点支持（匹配后端实际路由）
 * - 保留 /analytics/* 端点（综合分析）
 * - 更新响应格式匹配后端结构
 */

import { http, HttpResponse } from 'msw';

// Base URL
const API_BASE_URL = '/api/v1';

// =============================================================================
// Statistics Handlers (新增 - 匹配后端统计模块)
// =============================================================================

export const statisticsHandlers = [
  // 基础统计
  http.get(`${API_BASE_URL}/statistics/basic`, () => {
    return HttpResponse.json({
      total_assets: 100,
      ownership_status: {
        confirmed: 70,
        unconfirmed: 20,
        partial: 10,
      },
      property_nature: {
        commercial: 60,
        non_commercial: 40,
      },
      usage_status: {
        rented: 55,
        self_used: 25,
        vacant: 20,
      },
      generated_at: new Date().toISOString(),
      filters_applied: {},
    });
  }),

  // 面积摘要
  http.get(`${API_BASE_URL}/statistics/area-summary`, () => {
    return HttpResponse.json({
      total_land_area: 50000.0,
      total_rentable_area: 45000.0,
      total_rented_area: 38475.0,
      total_unrented_area: 6525.0,
      overall_occupancy_rate: 85.5,
      calculation_method: 'aggregation',
    });
  }),

  // 面积统计（直接计算）
  http.get(`${API_BASE_URL}/statistics/area-statistics`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        total_area: 50000.0,
        rented_area: 35000.0,
        vacant_area: 15000.0,
        occupancy_rate: 70.0,
      },
    });
  }),

  // 财务摘要
  http.get(`${API_BASE_URL}/statistics/financial-summary`, () => {
    return HttpResponse.json({
      total_assets: 100,
      total_annual_income: 1000000.0,
      total_annual_expense: 200000.0,
      net_annual_income: 800000.0,
      income_per_sqm: 20.0,
      expense_per_sqm: 4.0,
    });
  }),

  // 出租率统计
  http.get(`${API_BASE_URL}/statistics/occupancy-rate`, () => {
    return HttpResponse.json({
      overall_rate: 85.5,
      total_rentable_area: 45000.0,
      total_rented_area: 38475.0,
      total_assets: 100,
      rentable_assets_count: 80,
      calculation_method: 'aggregation',
    });
  }),

  // 按类别获取出租率
  http.get(`${API_BASE_URL}/statistics/occupancy-rate/by-category`, () => {
    return HttpResponse.json({
      商业: {
        overall_rate: 90.0,
        total_rentable_area: 20000.0,
        total_rented_area: 18000.0,
        asset_count: 30,
      },
      住宅: {
        overall_rate: 80.0,
        total_rentable_area: 15000.0,
        total_rented_area: 12000.0,
        asset_count: 20,
      },
    });
  }),

  // 仪表板数据
  http.get(`${API_BASE_URL}/statistics/dashboard`, () => {
    return HttpResponse.json({
      basic_stats: {
        total_assets: 100,
        ownership_status: {
          confirmed: 70,
          unconfirmed: 20,
          partial: 10,
        },
        property_nature: {
          commercial: 60,
          non_commercial: 40,
        },
        usage_status: {
          rented: 55,
          self_used: 25,
          vacant: 20,
        },
      },
      area_summary: {
        total_area: 50000.0,
        rentable_area: 45000.0,
        rented_area: 38475.0,
        unrented_area: 6525.0,
        occupancy_rate: 85.5,
      },
      financial_summary: {
        total_assets: 100,
        total_annual_income: 1000000.0,
        total_annual_expense: 200000.0,
        net_annual_income: 800000.0,
        income_per_sqm: 20.0,
        expense_per_sqm: 4.0,
      },
      occupancy_stats: {
        overall_rate: 85.5,
        total_rentable_area: 45000.0,
        total_rented_area: 38475.0,
        total_assets: 100,
        rentable_assets_count: 80,
      },
      category_occupancy: [],
      generated_at: new Date().toISOString(),
      filters_applied: {},
    });
  }),
];

// =============================================================================
// Analytics Handlers (保留 - 综合分析端点)
// =============================================================================

export const analyticsHandlers = [
  // 获取综合分析数据
  http.get(`${API_BASE_URL}/analytics/comprehensive`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        total_assets: 100,
        total_area: 50000.0,
        occupancy_rate: 85.5,
        total_revenue: 1000000.0,
        total_contracts: 50,
        active_contracts: 35,
        expired_contracts: 10,
        expiring_soon_contracts: 5,
        average_rent_per_sqm: 20.0,
        revenue_by_type: {
          lease: 800000.0,
          service: 150000.0,
          management: 50000.0,
        },
        asset_distribution: {
          by_type: [
            { type: 'building', count: 50, area: 30000.0 },
            { type: 'land', count: 30, area: 15000.0 },
            { type: 'facility', count: 20, area: 5000.0 },
          ],
          by_status: [
            { status: 'active', count: 80, area: 40000.0 },
            { status: 'inactive', count: 15, area: 8000.0 },
            { status: 'maintenance', count: 5, area: 2000.0 },
          ],
        },
      },
    });
  }),

  // 获取资产分布统计
  http.get(`${API_BASE_URL}/analytics/asset-distribution`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        by_type: [
          { type: 'building', count: 50, area: 30000.0 },
          { type: 'land', count: 30, area: 15000.0 },
          { type: 'facility', count: 20, area: 5000.0 },
        ],
        by_status: [
          { status: 'active', count: 80, area: 40000.0 },
          { status: 'inactive', count: 15, area: 8000.0 },
          { status: 'maintenance', count: 5, area: 2000.0 },
        ],
      },
    });
  }),

  // 面积统计
  http.get(`${API_BASE_URL}/analytics/area-statistics`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        total_area: 50000.0,
        rented_area: 35000.0,
        vacant_area: 15000.0,
        occupancy_rate: 70.0,
        by_district: [
          { district: '朝阳区', area: 20000.0 },
          { district: '海淀区', area: 15000.0 },
          { district: '西城区', area: 10000.0 },
          { district: '东城区', area: 5000.0 },
        ],
      },
    });
  }),

  // 出租率统计
  http.get(`${API_BASE_URL}/analytics/occupancy-rate`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        overall: 85.5,
        by_type: {
          building: 90.0,
          land: 80.0,
          facility: 75.0,
        },
        trend: [
          { month: '2024-01', rate: 82.0 },
          { month: '2024-02', rate: 83.5 },
          { month: '2024-03', rate: 85.0 },
          { month: '2024-04', rate: 85.5 },
        ],
      },
    });
  }),

  // 趋势数据
  http.get(`${API_BASE_URL}/analytics/trend`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        period: 'monthly',
        data_points: [
          { month: '2024-01', revenue: 80000.0, occupancy_rate: 82.0 },
          { month: '2024-02', revenue: 85000.0, occupancy_rate: 83.5 },
          { month: '2024-03', revenue: 90000.0, occupancy_rate: 85.0 },
        ],
      },
    });
  }),

  // 分布数据
  http.get(`${API_BASE_URL}/analytics/distribution`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        total: 100,
        categories: [
          { name: 'building', value: 50, percentage: 50 },
          { name: 'land', value: 30, percentage: 30 },
          { name: 'facility', value: 20, percentage: 20 },
        ],
      },
    });
  }),

  // 缓存统计
  http.get(`${API_BASE_URL}/analytics/cache/stats`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        total_keys: 10,
        hit_rate: 0.85,
        miss_rate: 0.15,
        memory_usage: '1.2MB',
      },
    });
  }),

  // 清除缓存
  http.post(`${API_BASE_URL}/analytics/cache/clear`, () => {
    return HttpResponse.json({
      success: true,
      message: '缓存已清除',
    });
  }),

  // 导出数据
  http.post(`${API_BASE_URL}/analytics/export`, () => {
    const excelContent = 'fake excel content';
    return new HttpResponse(excelContent, {
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': 'attachment; filename="analytics.xlsx"',
      },
    });
  }),
];

// =============================================================================
// 合并所有 Handlers
// =============================================================================

export const allHandlers = [
  ...statisticsHandlers,
  ...analyticsHandlers,
  // ... 其他 handlers (auth, asset, contract 等)
];
