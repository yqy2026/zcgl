/**
 * MSW Fixtures - 测试数据固定装置
 * 提供模拟API响应的测试数据
 */

import { Asset } from '@/types/asset'

// =============================================================================
// 资产相关 Fixtures
// =============================================================================

export const mockAsset: Asset = {
  id: 'asset-001',
  ownershipEntity: '测试权属方',
  ownershipCategory: '企业',
  projectName: '测试项目',
  propertyName: '测试物业A',
  address: '北京市朝阳区测试路123号',
  ownershipStatus: '自有',
  propertyNature: '商业',
  usageStatus: '使用中',

  // 面积字段
  landArea: 5000,
  actualPropertyArea: 4500,
  rentableArea: 4000,
  rentedArea: 3200,
  unrentedArea: 800,
  occupancyRate: 80,

  // 财务字段
  annualIncome: 480000,
  annualExpense: 96000,
  netIncome: 384000,

  // 合同字段
  leaseContractNumber: 'CT-2024-001',
  contractStartDate: '2024-01-01',
  contractEndDate: '2026-12-31',

  // 自动计算字段
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-12-28T00:00:00Z',
}

export const mockAssetList: Asset[] = [
  mockAsset,
  {
    ...mockAsset,
    id: 'asset-002',
    propertyName: '测试物业B',
    address: '北京市海淀区测试路456号',
    occupancyRate: 60,
  },
  {
    ...mockAsset,
    id: 'asset-003',
    propertyName: '测试物业C',
    address: '北京市西城区测试路789号',
    occupancyRate: 90,
  },
]

// =============================================================================
// API响应 Fixtures
// =============================================================================

export const successResponse = <T>(data: T) => ({
  success: true,
  data,
  message: '操作成功',
})

export const errorResponse = (message: string, code: string = 'ERROR') => ({
  success: false,
  data: null,
  message,
  code,
})

export const paginatedResponse = <T>(
  items: T[],
  page: number = 1,
  pageSize: number = 20,
  total: number = items.length
) => ({
  success: true,
  data: items,
  pagination: {
    page,
    pageSize,
    total,
    totalPages: Math.ceil(total / pageSize),
  },
})

// =============================================================================
// 特定API响应 Fixtures
// =============================================================================

export const assetListResponse = paginatedResponse(mockAssetList, 1, 20, 3)

export const assetDetailResponse = successResponse(mockAsset)

export const assetCreateResponse = successResponse({
  ...mockAsset,
  id: 'asset-new-001',
})

export const assetUpdateResponse = successResponse({
  ...mockAsset,
  propertyName: '更新后的物业名称',
})

export const assetDeleteResponse = successResponse({ id: 'asset-001', deleted: true })

// =============================================================================
// 错误响应 Fixtures
// =============================================================================

export const unauthorizedResponse = errorResponse('未授权，请先登录', 'UNAUTHORIZED')

export const forbiddenResponse = errorResponse('权限不足', 'FORBIDDEN')

export const notFoundResponse = errorResponse('资源不存在', 'NOT_FOUND')

export const validationErrorResponse = errorResponse(
  '数据验证失败',
  'VALIDATION_ERROR'
)

export const serverErrorResponse = errorResponse(
  '服务器内部错误',
  'INTERNAL_SERVER_ERROR'
)

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
}

export const loginResponse = successResponse({
  user: mockUser,
  token: 'mock-jwt-token-123456',
  refreshToken: 'mock-refresh-token-789012',
})

export const authErrorResponse = errorResponse('认证失败', 'AUTH_ERROR')

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
}

export const contractListResponse = paginatedResponse([mockContract], 1, 20, 1)

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
}

export const projectListResponse = paginatedResponse([mockProject], 1, 20, 1)

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
}

export const ownershipListResponse = paginatedResponse([mockOwnership], 1, 20, 1)

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
}

export const statisticsResponse = successResponse(mockStatistics)
