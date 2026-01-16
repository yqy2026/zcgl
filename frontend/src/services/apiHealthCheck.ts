/**
 * API Health Check Service
 *
 * Monitors critical API endpoints and reports their health status.
 */

import { enhancedApiClient } from '@/api/client'

export interface HealthCheckResult {
  endpoint: string
  name: string
  status: 'healthy' | 'unhealthy' | 'unknown'
  responseTime?: number
  error?: string
  lastChecked: Date
}

interface HealthSummary {
  total: number
  healthy: number
  unhealthy: number
  unknown: number
  healthPercentage: number
}

// Critical endpoints to monitor
const CRITICAL_ENDPOINTS = [
  { path: '/health', name: 'Health Check' },
  { path: '/assets', name: 'Assets API' },
  { path: '/rent-contracts/contracts', name: 'Rent Contracts' },
  { path: '/auth/users/me', name: 'User Info' },
  { path: '/analytics/dashboard', name: 'Analytics Dashboard' },
]

class APIHealthCheckService {
  private results = new Map<string, HealthCheckResult>()

  /**
   * Check all critical endpoints
   */
  async checkCriticalEndpoints(): Promise<Map<string, HealthCheckResult>> {
    const checks = CRITICAL_ENDPOINTS.map(async (endpoint) => {
      const startTime = performance.now()

      try {
        const response = await enhancedApiClient.get(endpoint.path, {
          // Short timeout for health checks
          timeout: 5000,
        })

        const responseTime = performance.now() - startTime
        const result: HealthCheckResult = {
          endpoint: endpoint.name,
          name: endpoint.name,
          status: responseTime < 3000 ? 'healthy' : 'unhealthy',
          responseTime,
          lastChecked: new Date(),
        }

        this.results.set(endpoint.path, result)
        return result
      } catch (error: unknown) {
        const responseTime = performance.now() - startTime
        const result: HealthCheckResult = {
          endpoint: endpoint.name,
          name: endpoint.name,
          status: 'unhealthy',
          responseTime,
          error: this.getErrorMessage(error),
          lastChecked: new Date(),
        }

        this.results.set(endpoint.path, result)
        return result
      }
    })

    await Promise.all(checks)
    return this.results
  }

  /**
   * Get all health check results
   */
  getResults(): Map<string, HealthCheckResult> {
    return this.results
  }

  /**
   * Get health summary statistics
   */
  getHealthSummary(): HealthSummary {
    const results = Array.from(this.results.values())

    const summary: HealthSummary = {
      total: results.length,
      healthy: results.filter((r) => r.status === 'healthy').length,
      unhealthy: results.filter((r) => r.status === 'unhealthy').length,
      unknown: results.filter((r) => r.status === 'unknown').length,
      healthPercentage:
        results.length > 0
          ? (results.filter((r) => r.status === 'healthy').length / results.length) * 100
          : 0,
    }

    return summary
  }

  /**
   * Get a specific endpoint's health status
   */
  getEndpointStatus(path: string): HealthCheckResult | undefined {
    return this.results.get(path)
  }

  /**
   * Check a single endpoint
   */
  async checkSingleEndpoint(path: string, name?: string): Promise<HealthCheckResult> {
    const startTime = performance.now()

    try {
      await enhancedApiClient.get(path, {
        timeout: 5000,
      })

      const responseTime = performance.now() - startTime
      const result: HealthCheckResult = {
        endpoint: name ?? path,
        name: name ?? path,
        status: responseTime < 3000 ? 'healthy' : 'unhealthy',
        responseTime,
        lastChecked: new Date(),
      }

      this.results.set(path, result)
      return result
    } catch (error: unknown) {
      const responseTime = performance.now() - startTime
      const result: HealthCheckResult = {
        endpoint: name ?? path,
        name: name ?? path,
        status: 'unhealthy',
        responseTime,
        error: this.getErrorMessage(error),
        lastChecked: new Date(),
      }

      this.results.set(path, result)
      return result
    }
  }

  /**
   * Clear all results
   */
  clearResults(): void {
    this.results.clear()
  }

  /**
   * Extract error message from error object
   */
  private getErrorMessage(error: unknown): string {
    if (error instanceof Error) {
      return error.message
    }

    if (typeof error === 'string') {
      return error
    }

    if (error && typeof error === 'object' && 'response' in error) {
      const err = error as { response: { data?: { detail?: string }; status?: number } }
      if (err.response?.data?.detail) {
        return err.response.data.detail
      }
      if (err.response?.status) {
        return `HTTP ${err.response.status}`
      }
    }

    return 'Unknown error'
  }
}

// Export singleton instance
export const apiHealthCheck = new APIHealthCheckService()

export default apiHealthCheck
