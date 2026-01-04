/**
 * MSW Handlers - API请求拦截器
 * 模拟后端API响应，支持测试环境
 */

import { http, HttpResponse } from 'msw'
import type { HttpHandler } from 'msw'

import {
  assetListResponse,
  assetDetailResponse,
  assetCreateResponse,
  assetUpdateResponse,
  assetDeleteResponse,
  unauthorizedResponse,
  forbiddenResponse,
  notFoundResponse,
  serverErrorResponse,
  loginResponse,
  authErrorResponse,
  contractListResponse,
  projectListResponse,
  ownershipListResponse,
  statisticsResponse,
} from './fixtures'

// =============================================================================
// 基础URL配置
// =============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// =============================================================================
// 辅助函数
// =============================================================================

/**
 * 延迟响应，模拟网络延迟
 */
const delay = (ms: number = 100) => new Promise(resolve => setTimeout(resolve, ms))

/**
 * 解析URL参数
 */
const getSearchParams = (request: Request) => {
  const url = new URL(request.url)
  return Object.fromEntries(url.searchParams)
}

// =============================================================================
// 资产管理 API Handlers
// =============================================================================

/**
 * GET /api/v1/assets - 获取资产列表
 */
export const getAssetsHandler = http.get(
  `${API_BASE_URL}/assets`,
  async ({ request }) => {
    await delay(50)

    const params = getSearchParams(request)
    const _page = parseInt(params.page || '1')
    const _limit = parseInt(params.limit || '20')

    // 模拟搜索过滤
    if (params.search) {
      return HttpResponse.json({
        ...assetListResponse,
        data: assetListResponse.data.filter((asset: { property_name: string }) =>
          (asset.property_name !== null && asset.property_name !== undefined && asset.property_name !== '') && asset.property_name.includes(params.search)
        ),
      })
    }

    return HttpResponse.json(assetListResponse)
  }
)

/**
 * GET /api/v1/assets/:id - 获取资产详情
 */
export const getAssetByIdHandler = http.get(
  `${API_BASE_URL}/assets/:id`,
  async ({ params }) => {
    await delay(50)

    if (params.id === '404') {
      return HttpResponse.json(notFoundResponse, { status: 404 })
    }

    return HttpResponse.json({
      ...assetDetailResponse,
      data: { ...assetDetailResponse.data, id: params.id },
    })
  }
)

/**
 * POST /api/v1/assets - 创建资产
 */
export const createAssetHandler = http.post(
  `${API_BASE_URL}/assets`,
  async ({ request }) => {
    await delay(100)

    const body = await request.json()

    // 模拟验证错误
    if ((body === null || body === undefined) || !((body as { propertyName?: string }).propertyName !== null && (body as { propertyName?: string }).propertyName !== undefined && (body as { propertyName?: string }).propertyName !== '')) {
      return HttpResponse.json({
        success: false,
        message: '物业名称不能为空',
        code: 'VALIDATION_ERROR',
      }, { status: 422 })
    }

    return HttpResponse.json(assetCreateResponse)
  }
)

/**
 * PUT /api/v1/assets/:id - 更新资产
 */
export const updateAssetHandler = http.put(
  `${API_BASE_URL}/assets/:id`,
  async ({ params, request }) => {
    await delay(100)

    const body = await request.json()

    if (params.id === '404') {
      return HttpResponse.json(notFoundResponse, { status: 404 })
    }

    return HttpResponse.json({
      ...assetUpdateResponse,
      data: {
        ...assetUpdateResponse.data,
        id: params.id,
        ...(body as object),
      },
    })
  }
)

/**
 * DELETE /api/v1/assets/:id - 删除资产
 */
export const deleteAssetHandler = http.delete(
  `${API_BASE_URL}/assets/:id`,
  async ({ params }) => {
    await delay(50)

    if (params.id === '404') {
      return HttpResponse.json(notFoundResponse, { status: 404 })
    }

    return HttpResponse.json({
      ...assetDeleteResponse,
      data: { id: params.id, deleted: true },
    })
  }
)

// =============================================================================
// 认证 API Handlers
// =============================================================================

/**
 * POST /api/v1/auth/login - 用户登录
 */
export const loginHandler = http.post(
  `${API_BASE_URL}/auth/login`,
  async ({ request }) => {
    await delay(100)

    const body = await request.json() as { username: string; password: string }

    // 模拟认证失败
    if (!body.username || !body.password) {
      return HttpResponse.json(authErrorResponse, { status: 401 })
    }

    if (body.username === 'error') {
      return HttpResponse.json(serverErrorResponse, { status: 500 })
    }

    return HttpResponse.json(loginResponse)
  }
)

/**
 * POST /api/v1/auth/logout - 用户登出
 */
export const logoutHandler = http.post(
  `${API_BASE_URL}/auth/logout`,
  async () => {
    await delay(50)
    return HttpResponse.json({ success: true, message: '登出成功' })
  }
)

/**
 * POST /api/v1/auth/refresh - 刷新Token
 */
export const refreshTokenHandler = http.post(
  `${API_BASE_URL}/auth/refresh`,
  async () => {
    await delay(50)
    return HttpResponse.json({
      success: true,
      data: {
        token: 'new-mock-jwt-token',
        refreshToken: 'new-mock-refresh-token',
      },
    })
  }
)

// =============================================================================
// 合同管理 API Handlers
// =============================================================================

/**
 * GET /api/v1/contracts - 获取合同列表
 */
export const getContractsHandler = http.get(
  `${API_BASE_URL}/contracts`,
  async () => {
    await delay(50)
    return HttpResponse.json(contractListResponse)
  }
)

// =============================================================================
// 项目管理 API Handlers
// =============================================================================

/**
 * GET /api/v1/projects - 获取项目列表
 */
export const getProjectsHandler = http.get(
  `${API_BASE_URL}/projects`,
  async () => {
    await delay(50)
    return HttpResponse.json(projectListResponse)
  }
)

// =============================================================================
// 权属方管理 API Handlers
// =============================================================================

/**
 * GET /api/v1/ownerships - 获取权属方列表
 */
export const getOwnershipsHandler = http.get(
  `${API_BASE_URL}/ownerships`,
  async () => {
    await delay(50)
    return HttpResponse.json(ownershipListResponse)
  }
)

// =============================================================================
// 统计数据 API Handlers
// =============================================================================

/**
 * GET /api/v1/statistics/dashboard - 获取工作台统计数据
 */
export const getStatisticsHandler = http.get(
  `${API_BASE_URL}/statistics/dashboard`,
  async () => {
    await delay(50)
    return HttpResponse.json(statisticsResponse)
  }
)

/**
 * GET /api/v1/test - 测试端点
 */
export const testHandler = http.get(
  `${API_BASE_URL}/test`,
  async () => {
    await delay(50)
    return HttpResponse.json({
      success: true,
      data: { id: 1, name: 'test' },
      message: 'Test endpoint works'
    })
  }
)

// =============================================================================
// 错误处理 Handlers
// =============================================================================

/**
 * 401 未授权错误
 */
export const unauthorizedHandler = http.get(
  `${API_BASE_URL}/error/unauthorized`,
  async () => {
    return HttpResponse.json(unauthorizedResponse, { status: 401 })
  }
)

/**
 * 403 权限不足错误
 */
export const forbiddenHandler = http.get(
  `${API_BASE_URL}/error/forbidden`,
  async () => {
    return HttpResponse.json(forbiddenResponse, { status: 403 })
  }
)

/**
 * 404 资源不存在错误
 */
export const notFoundHandler = http.get(
  `${API_BASE_URL}/error/notfound`,
  async () => {
    return HttpResponse.json(notFoundResponse, { status: 404 })
  }
)

/**
 * 500 服务器错误
 */
export const serverErrorHandler = http.get(
  `${API_BASE_URL}/error/server`,
  async () => {
    return HttpResponse.json(serverErrorResponse, { status: 500 })
  }
)

// =============================================================================
// 导出所有 Handlers
// =============================================================================

export const handlers: HttpHandler[] = [
  // 资产管理
  getAssetsHandler,
  getAssetByIdHandler,
  createAssetHandler,
  updateAssetHandler,
  deleteAssetHandler,

  // 认证
  loginHandler,
  logoutHandler,
  refreshTokenHandler,

  // 合同管理
  getContractsHandler,

  // 项目管理
  getProjectsHandler,

  // 权属方管理
  getOwnershipsHandler,

  // 统计数据
  getStatisticsHandler,

  // 测试
  testHandler,

  // 错误处理
  unauthorizedHandler,
  forbiddenHandler,
  notFoundHandler,
  serverErrorHandler,
]

// 默认导出
export default handlers
