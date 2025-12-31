/**
 * MSW Mocks 模块入口
 * 统一导出所有MSW相关的配置和工具
 */

// 服务器配置
export { mswServer } from './server'

// Handlers
export { handlers } from './handlers'
export type { HttpHandler } from 'msw'

// Fixtures
export {
  mockAsset,
  mockAssetList,
  mockUser,
  mockContract,
  mockProject,
  mockOwnership,
  mockStatistics,
  successResponse,
  errorResponse,
  paginatedResponse,
  assetListResponse,
  assetDetailResponse,
  assetCreateResponse,
  assetUpdateResponse,
  assetDeleteResponse,
  loginResponse,
  contractListResponse,
  projectListResponse,
  ownershipListResponse,
  statisticsResponse,
  unauthorizedResponse,
  forbiddenResponse,
  notFoundResponse,
  serverErrorResponse,
  authErrorResponse,
  validationErrorResponse,
} from './fixtures'

// 默认导出服务器
export { mswServer as default } from './server'
