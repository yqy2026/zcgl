/**
 * 路由审查器
 * 定期审查路由结构的健康度和最佳实践合规性
 */

import { useCallback } from 'react'
import { ROUTE_CONFIG } from '../constants/routes'
import { useRoutePerformanceMonitor } from '../monitoring/RoutePerformanceMonitor'

interface RouteAuditIssue {
  severity: 'error' | 'warning' | 'info'
  type: string
  route: string
  message: string
  suggestion?: string
  autoFixable?: boolean
}

interface RouteAuditResult {
  timestamp: number
  totalRoutes: number
  issues: RouteAuditIssue[]
  score: number  // 0-100
  categories: {
    structure: RouteAuditIssue[]
    performance: RouteAuditIssue[]
    security: RouteAuditIssue[]
    maintainability: RouteAuditIssue[]
  }
  recommendations: string[]
  summary: {
    errors: number
    warnings: number
    info: number
  }
}

interface RouteMetrics {
  route: string
  loadTime: number
  errorRate: number
  usage: number
  lastAccessed: number
}

class RouteAuditor {
  private auditRules: Map<string, (route: any) => RouteAuditIssue[]> = new Map()
  private performanceThresholds = {
    maxLoadTime: 3000,      // 3秒
    maxErrorRate: 0.05,      // 5%
    minUsage: 10,            // 最少使用次数
    maxDepth: 4              // 最大嵌套深度
  }

  constructor() {
    this.initializeAuditRules()
  }

  private initializeAuditRules() {
    this.auditRules = new Map()

    // 结构审查规则
    this.auditRules.set('structure', (route) => {
      const issues: RouteAuditIssue[] = []

      // 检查路由深度
      const depth = this.calculateRouteDepth(route)
      if (depth > this.performanceThresholds.maxDepth) {
        issues.push({
          severity: 'warning',
          type: 'deep_nesting',
          route: route.path || '',
          message: `路由嵌套过深 (${depth}层)`,
          suggestion: '考虑扁平化路由结构或使用布局组件',
          autoFixable: false
        })
      }

      // 检查路由命名规范
      if (route.path && !this.isValidRoutePath(route.path)) {
        issues.push({
          severity: 'error',
          type: 'invalid_naming',
          route: route.path,
          message: '路由命名不符合规范',
          suggestion: '使用 kebab-case 命名规范，避免驼峰和下划线',
          autoFixable: true
        })
      }

      // 检查参数一致性
      if (route.path && this.hasInconsistentParams(route.path)) {
        issues.push({
          severity: 'warning',
          type: 'inconsistent_params',
          route: route.path,
          message: '路由参数不一致',
          suggestion: '确保相同类型资源的参数命名一致',
          autoFixable: false
        })
      }

      return issues
    })

    // 性能审查规则
    this.auditRules.set('performance', (route) => {
      const issues: RouteAuditIssue[] = []

      // 检查懒加载
      if (!route.lazy && route.component) {
        issues.push({
          severity: 'warning',
          type: 'missing_lazy_load',
          route: route.path || '',
          message: '路由未使用懒加载',
          suggestion: '对非首页路由使用懒加载以提高首屏性能',
          autoFixable: true
        })
      }

      // 检查权限守卫
      if (route.permissions && route.permissions.length > 0 && !route.errorBoundary) {
        issues.push({
          severity: 'info',
          type: 'missing_error_boundary',
          route: route.path || '',
          message: '权限路由缺少错误边界',
          suggestion: '为需要权限验证的路由添加错误边界保护',
          autoFixable: true
        })
      }

      return issues
    })

    // 安全审查规则
    this.auditRules.set('security', (route) => {
      const issues: RouteAuditIssue[] = []

      // 检查权限配置
      if (this.isSecureRoute(route.path) && (!route.permissions || route.permissions.length === 0)) {
        issues.push({
          severity: 'error',
          type: 'missing_permissions',
          route: route.path || '',
          message: '安全路由缺少权限配置',
          suggestion: '为敏感路由添加适当的权限验证',
          autoFixable: false
        })
      }

      // 检查权限粒度
      if (route.permissions && route.permissions.length > 3) {
        issues.push({
          severity: 'warning',
          type: 'over_granular_permissions',
          route: route.path || '',
          message: '权限配置过于细粒度',
          suggestion: '考虑合并相关权限或使用角色权限',
          autoFixable: false
        })
      }

      return issues
    })

    // 可维护性审查规则
    this.auditRules.set('maintainability', (route) => {
      const issues: RouteAuditIssue[] = []

      // 检查路由文档
      if (!route.title || route.title.trim() === '') {
        issues.push({
          severity: 'warning',
          type: 'missing_title',
          route: route.path || '',
          message: '路由缺少标题',
          suggestion: '为路由添加描述性标题以提高可维护性',
          autoFixable: false
        })
      }

      // 检查面包屑配置
      if (route.path && route.path.split('/').length > 2 && !route.breadcrumb) {
        issues.push({
          severity: 'info',
          type: 'missing_breadcrumb',
          route: route.path,
          message: '深层路由缺少面包屑配置',
          suggestion: '为深层路由添加面包屑导航',
          autoFixable: true
        })
      }

      return issues
    })
  }

  private calculateRouteDepth(route: any): number {
    if (!route.children || route.children.length === 0) {
      return 1
    }

    return 1 + Math.max(...route.children.map((child: any) => this.calculateRouteDepth(child)))
  }

  private isValidRoutePath(path: string): boolean {
    // 检查是否符合 kebab-case 规范
    const kebabCaseRegex = /^\/([a-z0-9]+(-[a-z0-9]+)*)*(\/:[a-z0-9]+)*\/?$/
    return kebabCaseRegex.test(path)
  }

  private hasInconsistentParams(path: string): boolean {
    // 检查参数命名一致性
    const params = path.match(/:([^\/]+)/g)
    if (!params) return false

    const paramNames = params.map(p => p.substring(1))

    // 检查是否使用了不一致的命名风格
    const hasCamelCase = paramNames.some(name => /[A-Z]/.test(name))
    const hasSnakeCase = paramNames.some(name => /_/.test(name))
    const hasKebabCase = paramNames.some(name => /-/.test(name))

    return (Number(hasCamelCase) + Number(hasSnakeCase) + Number(hasKebabCase)) > 1
  }

  private isSecureRoute(path: string): boolean {
    const securePatterns = [
      /^\/system\//,
      /^\/admin\//,
      /\/users\/.*\/edit/,
      /\/assets\/.*\/delete/
    ]

    return securePatterns.some(pattern => pattern.test(path))
  }

  public async auditRoutes(metrics?: RouteMetrics[]): Promise<RouteAuditResult> {
    const issues: RouteAuditIssue[] = []
    const categories = {
      structure: [] as RouteAuditIssue[],
      performance: [] as RouteAuditIssue[],
      security: [] as RouteAuditIssue[],
      maintainability: [] as RouteAuditIssue[]
    }

    // 递归审查路由
    const auditRoute = (route: any, depth = 0) => {
      // 执行所有审查规则
      for (const [category, rule] of this.auditRules) {
        const ruleIssues = rule(route)
        categories[category as keyof typeof categories].push(...ruleIssues)
        issues.push(...ruleIssues)
      }

      // 审查子路由
      if (route.children) {
        route.children.forEach((child: any) => auditRoute(child, depth + 1))
      }
    }

    // 审查所有路由配置
    ROUTE_CONFIG.forEach(route => auditRoute(route))

    // 如果有性能指标，进行性能相关审查
    if (metrics) {
      const performanceIssues = this.auditRoutePerformance(metrics)
      categories.performance.push(...performanceIssues)
      issues.push(...performanceIssues)
    }

    // 计算审查得分
    const score = this.calculateAuditScore(issues)

    // 生成建议
    const recommendations = this.generateRecommendations(categories)

    // 统计摘要
    const summary = {
      errors: issues.filter(i => i.severity === 'error').length,
      warnings: issues.filter(i => i.severity === 'warning').length,
      info: issues.filter(i => i.severity === 'info').length
    }

    const result: RouteAuditResult = {
      timestamp: Date.now(),
      totalRoutes: this.countRoutes(ROUTE_CONFIG),
      issues,
      score,
      categories,
      recommendations,
      summary
    }

    // 上报审查结果
    await this.reportAuditResult(result)

    return result
  }

  private countRoutes(routes: any[]): number {
    let count = 0
    for (const route of routes) {
      count += 1
      if (route.children) {
        count += this.countRoutes(route.children)
      }
    }
    return count
  }

  private auditRoutePerformance(metrics: RouteMetrics[]): RouteAuditIssue[] {
    const issues: RouteAuditIssue[] = []

    for (const metric of metrics) {
      // 检查加载时间
      if (metric.loadTime > this.performanceThresholds.maxLoadTime) {
        issues.push({
          severity: 'warning',
          type: 'slow_route',
          route: metric.route,
          message: `路由加载时间过长 (${metric.loadTime}ms)`,
          suggestion: '优化组件代码分割或使用预加载',
          autoFixable: false
        })
      }

      // 检查错误率
      if (metric.errorRate > this.performanceThresholds.maxErrorRate) {
        issues.push({
          severity: 'error',
          type: 'high_error_rate',
          route: metric.route,
          message: `路由错误率过高 (${(metric.errorRate * 100).toFixed(1)}%)`,
          suggestion: '检查路由组件的错误处理逻辑',
          autoFixable: false
        })
      }

      // 检查使用率
      if (metric.usage < this.performanceThresholds.minUsage) {
        issues.push({
          severity: 'info',
          type: 'low_usage',
          route: metric.route,
          message: `路由使用率较低 (${metric.usage}次)`,
          suggestion: '考虑是否需要保留该路由或改进其可发现性',
          autoFixable: false
        })
      }
    }

    return issues
  }

  private calculateAuditScore(issues: RouteAuditIssue[]): number {
    const weights = {
      error: 10,
      warning: 5,
      info: 1
    }

    const totalDeduction = issues.reduce((sum, issue) => {
      return sum + weights[issue.severity]
    }, 0)

    const maxScore = 100
    const score = Math.max(0, maxScore - totalDeduction)

    return score
  }

  private generateRecommendations(categories: any): string[] {
    const recommendations: string[] = []

    // 基于问题类型生成建议
    const issueTypes = new Set(
      Object.values(categories)
        .flat()
        .map((issue) => (issue as RouteAuditIssue).type)
    )

    if (issueTypes.has('missing_lazy_load')) {
      recommendations.push('建议对所有非首页路由启用懒加载以提高首屏性能')
    }

    if (issueTypes.has('missing_permissions')) {
      recommendations.push('建议审查所有安全路由的权限配置，确保符合最小权限原则')
    }

    if (issueTypes.has('deep_nesting')) {
      recommendations.push('建议重构深层嵌套的路由结构，提高代码可维护性')
    }

    if (issueTypes.has('slow_route')) {
      recommendations.push('建议优化慢路由的性能，考虑代码分割和预加载策略')
    }

    // 通用建议
    if (recommendations.length === 0) {
      recommendations.push('路由结构良好，继续保持当前的代码质量')
    }

    return recommendations
  }

  private async reportAuditResult(result: RouteAuditResult) {
    try {
      // 发送审查结果到监控服务
      await fetch('/api/v1/monitoring/route-audit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(result)
      })

      console.log(`路由审计完成，得分: ${result.score}/100`)

      if (result.summary.errors > 0) {
        console.warn(`发现 ${result.summary.errors} 个错误，需要立即处理`)
      }

      if (result.summary.warnings > 0) {
        console.info(`发现 ${result.summary.warnings} 个警告，建议优化`)
      }

    } catch (error) {
      console.warn('路由审计结果上报失败:', error)
    }
  }

  public async fixAutoFixableIssues(): Promise<string[]> {
    const fixedIssues: string[] = []

    // 这里可以实现自动修复逻辑
    // 例如：自动添加懒加载、自动修复路由命名等

    console.log('自动修复完成，修复了', fixedIssues.length, '个问题')
    return fixedIssues
  }
}

// Hook for using the route auditor
export const useRouteAuditor = () => {
  const auditor = new RouteAuditor()
  const audit = useCallback(async () => {
    // 执行审计
    return await auditor.auditRoutes()
  }, [auditor])

  const autoFix = useCallback(async () => {
    return await auditor.fixAutoFixableIssues()
  }, [auditor])

  return {
    audit,
    autoFix,
    auditor
  }
}

// 定期审计调度器
export class RouteAuditScheduler {
  private auditor: RouteAuditor
  private interval: NodeJS.Timeout | null = null
  private auditInterval: number // 毫秒

  constructor(auditInterval: number = 24 * 60 * 60 * 1000) { // 默认24小时
    this.auditor = new RouteAuditor()
    this.auditInterval = auditInterval
  }

  start() {
    if (this.interval) {
      this.stop()
    }

    // 立即执行一次审计
    this.performAudit()

    // 设置定期审计
    this.interval = setInterval(() => {
      this.performAudit()
    }, this.auditInterval)

    console.log(`路由定期审计已启动，间隔: ${this.auditInterval / 1000 / 60 / 60} 小时`)
  }

  stop() {
    if (this.interval) {
      clearInterval(this.interval)
      this.interval = null
      console.log('路由定期审计已停止')
    }
  }

  private async performAudit() {
    try {
      console.log('开始执行定期路由审计...')
      const result = await this.auditor.auditRoutes()

      console.log(`路由审计完成，得分: ${result.score}/100`)

      if (result.score < 80) {
        console.warn('路由健康度较低，建议关注并修复发现的问题')
      }

    } catch (error) {
      console.error('定期路由审计失败:', error)
    }
  }
}

export default RouteAuditor