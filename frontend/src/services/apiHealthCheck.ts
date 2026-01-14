/**
 * API健康检查服务
 * 提供API可用性检查和健康监控功能
 */

import { enhancedApiClient } from '@/api/client'
import { createLogger } from '@/utils/logger'

const logger = createLogger('ApiHealthCheck');
const api = enhancedApiClient
import {
  AUTH_API,
  PDF_API,
  SYSTEM_API,
  ASSET_API,
  STATISTICS_API,
  TEST_COVERAGE_API,
  MONITORING_API,
  ERROR_REPORTING_API
} from '../constants/api'

// 健康检查结果接口
export interface HealthCheckResult {
  endpoint: string
  status: 'healthy' | 'unhealthy' | 'unknown'
  responseTime?: number
  error?: string
  lastChecked: Date
}

// 健康检查配置接口
export interface HealthCheckConfig {
  timeout: number // 毫秒
  retries: number
  retryDelay: number // 毫秒
  interval: number // 毫秒
  criticalEndpoints: string[]
}

export interface HealthReport {
  timestamp: Date
  critical: {
    total: number
    healthy: number
    unhealthy: number
    unknown: number
    healthPercentage: number
  }
  details: HealthCheckResult[]
}

// 默认配置
const DEFAULT_CONFIG: HealthCheckConfig = {
  timeout: 5000,
  retries: 2,
  retryDelay: 1000,
  interval: 30000, // 30秒
  criticalEndpoints: [
    AUTH_API.LOGIN,
    PDF_API.INFO,
    SYSTEM_API.USERS,
    ASSET_API.LIST,
    STATISTICS_API.OVERVIEW
  ]
}

/**
 * API健康检查服务类
 */
export class ApiHealthCheckService {
  private config: HealthCheckConfig
  private results: Map<string, HealthCheckResult> = new Map()
  private intervalId: NodeJS.Timeout | null = null
  private isRunning = false

  constructor(config: Partial<HealthCheckConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config }
  }

  /**
   * 检查单个API端点的健康状态
   */
  async checkEndpoint(endpoint: string, name: string = endpoint): Promise<HealthCheckResult> {
    const startTime = Date.now()
    let lastError: string | undefined

    try {
      // 使用HEAD请求检查端点可用性（如果支持的话）
      const response = await api.getAxiosInstance().head(endpoint)
      const responseTime = Date.now() - startTime

      const result: HealthCheckResult = {
        endpoint: name,
        status: ((response as any)?.status ?? 0) >= 200 && ((response as any)?.status ?? 0) < 300 ? 'healthy' : 'unhealthy',
        responseTime,
        lastChecked: new Date()
      }

      // 如果HEAD请求不支持，尝试GET请求
      if (((response as any)?.status ?? 0) === 405) {
        const getResponse = await api.get(endpoint)
        const getResponseTime = Date.now() - startTime

        result.status = ((getResponse as any)?.status ?? 0) >= 200 && ((getResponse as any)?.status ?? 0) < 300 ? 'healthy' : 'unhealthy'
        result.responseTime = getResponseTime
      }

      this.results.set(name, result)
      return result

    } catch (error: unknown) {
      const err = error instanceof Error ? error : new Error(String(error));
      const responseTime = Date.now() - startTime
      lastError = err.message || 'Unknown error'

      const result: HealthCheckResult = {
        endpoint: name,
        status: 'unhealthy',
        responseTime,
        error: lastError,
        lastChecked: new Date()
      }

      this.results.set(name, result)
      return result
    }
  }

  /**
   * 检查所有关键端点
   */
  async checkCriticalEndpoints(): Promise<HealthCheckResult[]> {
    const results: HealthCheckResult[] = []

    for (const endpoint of this.config.criticalEndpoints) {
      try {
        const result = await this.checkEndpoint(endpoint)
        results.push(result)
      } catch (error) {
        logger.error(`Health check failed for ${endpoint}`, error instanceof Error ? error : new Error(String(error)))
        results.push({
          endpoint,
          status: 'unknown',
          error: 'Health check failed',
          lastChecked: new Date()
        })
      }
    }

    return results
  }

  /**
   * 检查所有定义的API端点
   */
  async checkAllEndpoints(): Promise<{ total: number; healthy: number; unhealthy: number; unknown: number; results: HealthCheckResult[] }> {
    const endpoints = [
      // 认证API
      { path: AUTH_API.LOGIN, name: 'auth.login' },
      { path: AUTH_API.LOGOUT, name: 'auth.logout' },
      { path: AUTH_API.USERS, name: 'auth.users' },

      // PDF API
      { path: PDF_API.INFO, name: 'pdf.info' },
      { path: PDF_API.SESSIONS, name: 'pdf.sessions' },

      // 系统API
      { path: SYSTEM_API.USERS, name: 'system.users' },
      { path: SYSTEM_API.HEALTH, name: 'system.health' },

      // 资产API
      { path: ASSET_API.LIST, name: 'asset.list' },

      // 统计API
      { path: STATISTICS_API.OVERVIEW, name: 'stats.overview' },

      // 测试覆盖率API
      { path: TEST_COVERAGE_API.REPORT, name: 'test.coverage.report' },

      // 监控API
      { path: MONITORING_API.SYSTEM_HEALTH, name: 'monitoring.health' },

      // 错误报告API
      { path: ERROR_REPORTING_API.REPORT, name: 'error.report' }
    ]

    const results: HealthCheckResult[] = []
    let healthy = 0
    let unhealthy = 0
    let unknown = 0

    for (const { path, name } of endpoints) {
      try {
        const result = await this.checkEndpoint(path, name)
        results.push(result)

        if (result.status === 'healthy') healthy++
        else if (result.status === 'unhealthy') unhealthy++
        else unknown++

      } catch (error) {
        logger.error(`Health check failed for ${name}`, error instanceof Error ? error : new Error(String(error)))
        results.push({
          endpoint: name,
          status: 'unknown',
          error: 'Health check failed',
          lastChecked: new Date()
        })
        unknown++
      }
    }

    return {
      total: results.length,
      healthy,
      unhealthy,
      unknown,
      results
    }
  }

  /**
   * 启动定期健康检查
   */
  startPeriodicCheck(): void {
    if (this.isRunning) {
      logger.warn('Health check service is already running')
      return
    }

    this.isRunning = true
    logger.debug('Starting periodic API health checks...')

    // 立即执行一次检查
    this.checkCriticalEndpoints().catch(error => {
      logger.error('Initial health check failed', error instanceof Error ? error : new Error(String(error)))
    })

    // 设置定期检查
    this.intervalId = setInterval(() => {
      this.checkCriticalEndpoints().catch(error => {
        logger.error('Periodic health check failed', error instanceof Error ? error : new Error(String(error)))
      })
    }, this.config.interval)
  }

  /**
   * 停止定期健康检查
   */
  stopPeriodicCheck(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
    }

    this.isRunning = false
    logger.debug('Stopped periodic API health checks')
  }

  /**
   * 获取健康检查结果
   */
  getResults(): Map<string, HealthCheckResult> {
    return new Map(this.results)
  }

  /**
   * 获取端点健康状态
   */
  getEndpointHealth(endpoint: string): HealthCheckResult | undefined {
    return this.results.get(endpoint)
  }

  /**
   * 生成健康检查报告
   */
  generateReport(): HealthReport {
    const criticalResults = this.config.criticalEndpoints.map(endpoint =>
      this.results.get(endpoint) || {
        endpoint,
        status: 'unknown' as const,
        lastChecked: new Date()
      }
    )

    const healthy = criticalResults.filter(r => r.status === 'healthy').length
    const unhealthy = criticalResults.filter(r => r.status === 'unhealthy').length
    const unknown = criticalResults.filter(r => r.status === 'unknown').length

    return {
      timestamp: new Date(),
      critical: {
        total: criticalResults.length,
        healthy,
        unhealthy,
        unknown,
        healthPercentage: criticalResults.length > 0 ? (healthy / criticalResults.length) * 100 : 0
      },
      details: criticalResults as HealthCheckResult[]
    }
  }

  /**
   * 检查系统整体健康状态
   */
  async checkSystemHealth(): Promise<{
    isHealthy: boolean
    criticalIssues: string[]
    report: HealthReport
  }> {
    await this.checkAllEndpoints()
    const report = this.generateReport()
    const issues: string[] = []

    // 检查关键端点健康状况
    if (report.critical.healthPercentage < 80) {
      issues.push(`Critical API health is ${(report.critical.healthPercentage).toFixed(1)}%`)
    }

    // 检查响应时间
    const slowEndpoints = report.details.filter(r =>
      (r.responseTime ?? 0) > 3000
    )

    if (slowEndpoints.length > 0) {
      issues.push(`${slowEndpoints.length} endpoints have slow response times (>3s)`)
    }

    return {
      isHealthy: issues.length === 0 && report.critical.healthPercentage >= 80,
      criticalIssues: issues,
      report
    }
  }
}

// 创建全局实例
export const apiHealthCheck = new ApiHealthCheckService()

// 便捷的检查函数
export const checkApiHealth = async (): Promise<{
  isHealthy: boolean
  criticalIssues: string[]
  report: HealthReport
}> => {
  return apiHealthCheck.checkSystemHealth()
}

// 开发环境下自动启动健康检查
if (process.env.NODE_ENV === 'development') {
  // 等待应用启动后再开始健康检查
  setTimeout(() => {
    try {
      apiHealthCheck.startPeriodicCheck()
      logger.info('API Health Check Service started')
    } catch (error) {
      logger.error('Failed to start API Health Check Service', error instanceof Error ? error : new Error(String(error)))
    }
  }, 2000)
}

export default ApiHealthCheckService
