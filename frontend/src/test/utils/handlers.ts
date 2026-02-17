/**
 * MSW API Handlers 统一管理
 * 集中管理所有 API Mock 处理器
 */

import { http, HttpResponse } from 'msw';

// Base URL
const API_BASE_URL = '/api/v1';

// =============================================================================
// Auth Handlers
// =============================================================================

export const authHandlers = [
  // 登录
  http.post(`${API_BASE_URL}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { identifier: string; password: string };

    if (body.identifier === 'testuser' && body.password === 'password123') {
      return HttpResponse.json({
        data: {
          user: {
            id: 'test-user-001',
            username: 'testuser',
            email: 'test@example.com',
            role_id: 'role-admin-id',
            role_name: 'admin',
            roles: ['admin'],
            role_ids: ['role-admin-id'],
            is_admin: true,
            full_name: 'Test User',
            default_organization_id: 'org-001',
          },
          token: 'fake-jwt-token',
        },
        message: '登录成功',
        success: true,
      });
    }

    return HttpResponse.json({ message: '用户名或密码错误', success: false }, { status: 401 });
  }),

  // 获取当前用户信息
  http.get(`${API_BASE_URL}/auth/me`, () => {
    return HttpResponse.json({
      data: {
        id: 'test-user-001',
        username: 'testuser',
        email: 'test@example.com',
        role_id: 'role-admin-id',
        role_name: 'admin',
        roles: ['admin'],
        role_ids: ['role-admin-id'],
        is_admin: true,
        full_name: 'Test User',
        is_active: true,
        default_organization_id: 'org-001',
      },
      success: true,
    });
  }),

  // 登出
  http.post(`${API_BASE_URL}/auth/logout`, () => {
    return HttpResponse.json({
      message: '登出成功',
      success: true,
    });
  }),
];

// =============================================================================
// Asset Handlers
// =============================================================================

export const assetHandlers = [
  // 获取资产列表
  http.get(`${API_BASE_URL}/assets`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const pageSize = parseInt(url.searchParams.get('page_size') || '10');
    const status = url.searchParams.get('status');

    // 生成模拟数据
    const assets = Array.from({ length: pageSize }, (_, i) => {
      const id = (page - 1) * pageSize + i + 1;
      return {
        id,
        name: `测试资产 ${id}`,
        code: `ASSET-${String(id).padStart(4, '0')}`,
        area: Math.round(Math.random() * 5000 + 500),
        location: `测试地址 ${i + 1}`,
        status: status || ['active', 'inactive', 'maintenance'][i % 3],
        asset_type: ['building', 'land', 'facility'][i % 3],
        created_at: new Date().toISOString(),
      };
    });

    return HttpResponse.json({
      data: {
        items: assets,
        total: 100,
        page,
        page_size: pageSize,
        total_pages: Math.ceil(100 / pageSize),
      },
      message: '获取成功',
      success: true,
    });
  }),

  // 获取资产详情
  http.get(`${API_BASE_URL}/assets/:id`, ({ params }) => {
    const { id } = params;
    const assetId = parseInt(id as string);

    return HttpResponse.json({
      data: {
        id: assetId,
        name: `测试资产 ${assetId}`,
        code: `ASSET-${String(assetId).padStart(4, '0')}`,
        area: 1000.0,
        location: '测试地址',
        status: 'active',
        asset_type: 'building',
        building_area: 800.0,
        floor_area: 1000.0,
        ownerships: [],
        contracts: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      success: true,
    });
  }),

  // 创建资产
  http.post(`${API_BASE_URL}/assets`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;

    return HttpResponse.json({
      data: {
        id: Math.floor(Math.random() * 10000),
        ...body,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      message: '创建成功',
      success: true,
    });
  }),

  // 更新资产
  http.put(`${API_BASE_URL}/assets/:id`, async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;

    return HttpResponse.json({
      data: {
        id: parseInt(params.id as string),
        ...body,
        updated_at: new Date().toISOString(),
      },
      message: '更新成功',
      success: true,
    });
  }),

  // 删除资产
  http.delete(`${API_BASE_URL}/assets/:id`, () => {
    return HttpResponse.json({
      message: '删除成功',
      success: true,
    });
  }),
];

// =============================================================================
// RentContract Handlers
// =============================================================================

export const rentContractHandlers = [
  // 获取合同列表
  http.get(`${API_BASE_URL}/rental-contracts/contracts`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const pageSize = parseInt(url.searchParams.get('page_size') || '10');
    const status = url.searchParams.get('status');

    const contracts = Array.from({ length: pageSize }, (_, i) => {
      const id = (page - 1) * pageSize + i + 1;
      return {
        id,
        contract_no: `HT-2024-${String(id).padStart(3, '0')}`,
        contract_name: `测试合同 ${id}`,
        contract_type: 'lease',
        status: status || ['active', 'expired', 'draft'][i % 3],
        start_date: '2024-01-01',
        end_date: '2024-12-31',
        total_rent: 10000 + i * 1000,
        paid_amount: 5000 + i * 500,
        overdue_amount: 1000 + i * 100,
        tenant_name: `测试租户 ${id}`,
        tenant_phone: `1380013800${i % 10}`,
        created_at: new Date().toISOString(),
      };
    });

    return HttpResponse.json({
      data: {
        items: contracts,
        total: 100,
        page,
        page_size: pageSize,
        total_pages: Math.ceil(100 / pageSize),
      },
      message: '获取成功',
      success: true,
    });
  }),

  // 获取合同详情
  http.get(`${API_BASE_URL}/rental-contracts/contracts/:id`, ({ params }) => {
    const id = parseInt(params.id as string);

    return HttpResponse.json({
      data: {
        id,
        contract_no: `HT-2024-${String(id).padStart(3, '0')}`,
        contract_name: `测试合同 ${id}`,
        contract_type: 'lease',
        status: 'active',
        start_date: '2024-01-01',
        end_date: '2024-12-31',
        total_rent: 10000,
        paid_amount: 5000,
        overdue_amount: 1000,
        tenant_name: `测试租户 ${id}`,
        tenant_phone: '13800138000',
        payment_cycle: 'monthly',
        payment_method: 'bank_transfer',
        rent_terms: [],
        asset: {
          id: 1,
          name: '测试资产',
          code: 'ASSET-0001',
          area: 1000,
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      success: true,
    });
  }),

  // 创建合同
  http.post(`${API_BASE_URL}/rental-contracts/contracts`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;

    return HttpResponse.json({
      data: {
        id: Math.floor(Math.random() * 10000),
        contract_no: `HT-2024-${String(Math.floor(Math.random() * 999)).padStart(3, '0')}`,
        ...body,
        status: 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      message: '合同创建成功',
      success: true,
    });
  }),

  // 更新合同
  http.put(`${API_BASE_URL}/rental-contracts/contracts/:id`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;

    return HttpResponse.json({
      data: {
        ...body,
        updated_at: new Date().toISOString(),
      },
      message: '更新成功',
      success: true,
    });
  }),

  // 删除合同
  http.delete(`${API_BASE_URL}/rental-contracts/contracts/:id`, () => {
    return HttpResponse.json({
      message: '删除成功',
      success: true,
    });
  }),

  // 续签合同
  http.post(`${API_BASE_URL}/rental-contracts/contracts/:id/renew`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;

    return HttpResponse.json({
      data: {
        id: Math.floor(Math.random() * 10000),
        contract_no: `HT-2025-${String(Math.floor(Math.random() * 999)).padStart(3, '0')}`,
        ...body,
        status: 'active',
      },
      message: '续签成功',
      success: true,
    });
  }),

  // 终止合同
  http.post(`${API_BASE_URL}/rental-contracts/contracts/:id/terminate`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const terminationReason =
      typeof body.termination_reason === 'string' ? body.termination_reason : '';

    return HttpResponse.json({
      data: {
        status: 'terminated',
        termination_reason: terminationReason,
        termination_date: new Date().toISOString().split('T')[0],
      },
      message: '终止成功',
      success: true,
    });
  }),
];

// =============================================================================
// Ownership Handlers
// =============================================================================

export const ownershipHandlers = [
  // 获取权属列表
  http.get(`${API_BASE_URL}/ownerships`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const pageSize = parseInt(url.searchParams.get('page_size') || '10');

    const ownerships = Array.from({ length: pageSize }, (_, i) => {
      const id = (page - 1) * pageSize + i + 1;
      return {
        id,
        asset_id: Math.floor(Math.random() * 100) + 1,
        organization_id: Math.floor(Math.random() * 50) + 1,
        organization_name: `测试单位 ${id}`,
        ownership_ratio: 100 / pageSize,
        start_date: '2024-01-01',
        is_active: true,
      };
    });

    return HttpResponse.json({
      data: {
        items: ownerships,
        total: 100,
        page,
        page_size: pageSize,
      },
      success: true,
    });
  }),

  // 获取权属详情
  http.get(`${API_BASE_URL}/ownerships/:id`, ({ params }) => {
    const id = parseInt(params.id as string);

    return HttpResponse.json({
      data: {
        id,
        asset_id: 1,
        organization_id: 1,
        organization_name: '测试单位',
        ownership_ratio: 100,
        start_date: '2024-01-01',
        end_date: null,
        is_active: true,
        ownership_type: 'full',
      },
      success: true,
    });
  }),
];

// =============================================================================
// Organization Handlers
// =============================================================================

export const organizationHandlers = [
  // 获取组织机构列表
  http.get(`${API_BASE_URL}/organizations`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const pageSize = parseInt(url.searchParams.get('page_size') || '10');

    const organizations = Array.from({ length: pageSize }, (_, i) => {
      const id = (page - 1) * pageSize + i + 1;
      return {
        id,
        name: `测试单位 ${id}`,
        code: `ORG-${String(id).padStart(4, '0')}`,
        type: ['company', 'government', 'institution'][i % 3],
        is_active: true,
      };
    });

    return HttpResponse.json({
      data: {
        items: organizations,
        total: 100,
        page,
        page_size: pageSize,
      },
      success: true,
    });
  }),
];

// =============================================================================
// Analytics Handlers
// =============================================================================

export const analyticsHandlers = [
  // 获取综合分析数据
  http.get(`${API_BASE_URL}/analytics/comprehensive`, () => {
    return HttpResponse.json({
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
      },
      success: true,
    });
  }),

  // 获取资产分布统计
  http.get(`${API_BASE_URL}/analytics/asset-distribution`, () => {
    return HttpResponse.json({
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
      success: true,
    });
  }),

  // 获取面积统计
  http.get(`${API_BASE_URL}/analytics/area-statistics`, () => {
    return HttpResponse.json({
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
      success: true,
    });
  }),

  // 获取出租率统计
  http.get(`${API_BASE_URL}/analytics/occupancy-rate`, () => {
    return HttpResponse.json({
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
      success: true,
    });
  }),

  // 导出 Excel
  http.get(`${API_BASE_URL}/analytics/export`, () => {
    // 返回模拟的 Excel 文件
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
// Reporting Handlers
// =============================================================================

export const reportingHandlers = [
  // 前端错误上报
  http.post(`${API_BASE_URL}/errors/report`, async () => {
    return HttpResponse.json({
      data: { accepted: true },
      message: '错误上报成功',
      success: true,
    });
  }),

  // A/B 测试事件上报
  http.post(`${API_BASE_URL}/analytics/abtest-events`, async () => {
    return HttpResponse.json({
      data: { accepted: true },
      message: '事件上报成功',
      success: true,
    });
  }),

  // A/B 测试转化上报
  http.post(`${API_BASE_URL}/analytics/abtest-conversions`, async () => {
    return HttpResponse.json({
      data: { accepted: true },
      message: '转化上报成功',
      success: true,
    });
  }),
];

// =============================================================================
// Export All Handlers
// =============================================================================

export const handlers = [
  ...authHandlers,
  ...assetHandlers,
  ...rentContractHandlers,
  ...ownershipHandlers,
  ...organizationHandlers,
  ...analyticsHandlers,
  ...reportingHandlers,
];
