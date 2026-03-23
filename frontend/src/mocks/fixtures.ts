/**
 * MSW Fixtures - 测试数据固定装置
 * 提供模拟API响应的测试数据
 */

import {
  Asset,
  AssetLeaseSummaryResponse,
  OwnershipStatus,
  PropertyNature,
  UsageStatus,
} from '@/types/asset';

// =============================================================================
// 资产相关 Fixtures
// =============================================================================

export const mockAsset: Asset = {
  id: 'asset-001',
  owner_party_name: '测试权属方',
  ownership_category: '企业',
  project_name: '测试项目',
  asset_name: '测试物业A',
  address: '北京市朝阳区测试路123号',
  ownership_status: OwnershipStatus.CONFIRMED,
  property_nature: PropertyNature.COMMERCIAL,
  usage_status: UsageStatus.RENTED,

  // 面积字段
  land_area: 5000,
  actual_property_area: 4500,
  rentable_area: 4000,
  rented_area: 3200,
  unrented_area: 800,
  occupancy_rate: 80,
  include_in_occupancy_rate: true,

  // 合同字段
  lease_contract_number: 'CT-2024-001',
  contract_start_date: '2024-01-01',
  contract_end_date: '2026-12-31',

  // 其他必需字段
  is_sublease: false,
  is_litigated: false,

  // 自动计算字段
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-12-28T00:00:00Z',
};

export const mockAssetList: Asset[] = [
  mockAsset,
  {
    ...mockAsset,
    id: 'asset-002',
    asset_name: '测试物业B',
    address: '北京市海淀区测试路456号',
    occupancy_rate: 60,
  },
  {
    ...mockAsset,
    id: 'asset-003',
    asset_name: '测试物业C',
    address: '北京市西城区测试路789号',
    occupancy_rate: 90,
  },
];

// =============================================================================
// API响应 Fixtures
// =============================================================================

export const successResponse = <T>(data: T) => ({
  success: true,
  data,
  message: '操作成功',
});

export const errorResponse = (message: string, code: string = 'ERROR') => ({
  success: false,
  data: null,
  message,
  code,
});

export const paginatedResponse = <T>(
  items: T[],
  page: number = 1,
  pageSize: number = 20,
  total: number = items.length
) => ({
  success: true,
  data: {
    items,
    pagination: {
      page,
      page_size: pageSize,
      total,
      total_pages: Math.ceil(total / pageSize),
    },
  },
});

// =============================================================================
// 特定API响应 Fixtures
// =============================================================================

export const assetListResponse = paginatedResponse(mockAssetList, 1, 20, 3);

export const assetDetailResponse = successResponse(mockAsset);

export const assetLeaseSummaryResponse = successResponse<AssetLeaseSummaryResponse>({
  asset_id: mockAsset.id,
  period_start: '2026-03-01',
  period_end: '2026-03-31',
  total_contracts: 3,
  total_rented_area: 3200,
  rentable_area: 4000,
  occupancy_rate: 80,
  by_type: [
    {
      group_relation_type: '上游',
      label: '上游承租',
      contract_count: 1,
      total_area: 0,
      monthly_amount: 22000,
    },
    {
      group_relation_type: '下游',
      label: '下游转租',
      contract_count: 2,
      total_area: 0,
      monthly_amount: 46000,
    },
    {
      group_relation_type: '委托',
      label: '委托协议',
      contract_count: 0,
      total_area: 0,
      monthly_amount: 0,
    },
    {
      group_relation_type: '直租',
      label: '直租合同',
      contract_count: 0,
      total_area: 0,
      monthly_amount: 0,
    },
  ],
  customer_summary: [
    {
      party_id: 'party-001',
      party_name: '测试租户A',
      group_relation_type: '下游',
      contract_count: 2,
    },
  ],
});

export const assetCreateResponse = successResponse({
  ...mockAsset,
  id: 'asset-new-001',
});

export const assetUpdateResponse = successResponse({
  ...mockAsset,
  propertyName: '更新后的物业名称',
});

export const assetDeleteResponse = successResponse({ id: 'asset-001', deleted: true });

// =============================================================================
// 错误响应 Fixtures
// =============================================================================

export const unauthorizedResponse = errorResponse('未授权，请先登录', 'UNAUTHORIZED');

export const forbiddenResponse = errorResponse('权限不足', 'FORBIDDEN');

export const notFoundResponse = errorResponse('资源不存在', 'NOT_FOUND');

export const validationErrorResponse = errorResponse('数据验证失败', 'VALIDATION_ERROR');

export const serverErrorResponse = errorResponse('服务器内部错误', 'INTERNAL_SERVER_ERROR');

// =============================================================================
// 用户和认证相关 Fixtures
// =============================================================================

export const mockUser = {
  id: 'user-001',
  username: 'testuser',
  email: 'test@example.com',
  fullName: '测试用户',
  roles: ['admin'],
  permissions: ['asset:read', 'asset:write', 'asset:delete'],
};

export const loginResponse = successResponse({
  user: mockUser,
  token: 'mock-jwt-token-123456',
  refreshToken: 'mock-refresh-token-789012',
});

export const authErrorResponse = errorResponse('认证失败', 'AUTH_ERROR');

// =============================================================================
// 合同相关 Fixtures
// =============================================================================

export const mockContract = {
  id: 'contract-001',
  contractNumber: 'CT-2024-001',
  assetId: 'asset-001',
  propertyName: '测试物业A',
  tenantName: '测试租户',
  leaseStartDate: '2024-01-01',
  leaseEndDate: '2026-12-31',
  monthlyRent: 40000,
  status: 'active',
};

export const contractListResponse = paginatedResponse([mockContract], 1, 20, 1);

// =============================================================================
// 项目相关 Fixtures
// =============================================================================

export const mockProject = {
  id: 'project-001',
  projectName: '测试项目',
  projectCode: 'PRJ-001',
  totalAssets: 10,
  totalArea: 50000,
  rentedArea: 40000,
  occupancyRate: 80,
};

export const projectListResponse = paginatedResponse([mockProject], 1, 20, 1);

// =============================================================================
// 权属方相关 Fixtures
// =============================================================================

export const mockOwnership = {
  id: 'ownership-001',
  ownershipName: '测试权属方',
  ownershipType: '企业',
  contactPerson: '张三',
  contactPhone: '13800138000',
  assetCount: 5,
};

export const ownershipListResponse = paginatedResponse([mockOwnership], 1, 20, 1);

// =============================================================================
// 统计数据 Fixtures
// =============================================================================

export const mockStatistics = {
  totalAssets: 150,
  totalArea: 750000,
  rentedArea: 600000,
  occupancyRate: 80,
  annualIncome: 9000000,
  annualExpense: 1800000,
  netIncome: 7200000,
  activeContracts: 120,
  expiringContracts: 8,
};

export const statisticsResponse = successResponse(mockStatistics);
