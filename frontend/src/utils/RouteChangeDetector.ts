/**
 * 路由变更检测器
 * 检测路由配置变更、权限变更和API变更
 */

import { useCallback, useEffect } from 'react'
import { ROUTE_CONFIG } from '../constants/routes'

interface RouteChangeConfig {
  route: string
  permissions: Array<{ resource: string; action: string }>
  component: string
  params?: string[]
  query?: string[]
}

interface APIChangeConfig {
  endpoint: string
  method: string
  permissions: Array<{ resource: string; action: string }>
  version: string
  deprecated?: boolean
}

interface ChangeDetection {
  timestamp: number
  changes: {
    added: RouteChangeConfig[]
    removed: RouteChangeConfig[]
    modified: Array<{
      route: string
      old: RouteChangeConfig
      new: RouteChangeConfig
    }>
  }
  api_changes: {
    added: APIChangeConfig[]
    removed: APIChangeConfig[]
    modified: Array<{
      endpoint: string
      old: APIChangeConfig
      new: APIChangeConfig
    }>
  }
}

class RouteChangeDetector {
  private lastSnapshot: Map<string, RouteChangeConfig>
  private lastAPISnapshot: Map<string, APIChangeConfig>
  private changeHistory: ChangeDetection[]
  private maxHistorySize: number
  private checkInterval: NodeJS.Timeout | null = null

  constructor() {
    this.lastSnapshot = new Map()
    this.lastAPISnapshot = new Map()
    this.changeHistory = []
    this.maxHistorySize = 50

    this.initializeSnapshots()
    this.startPeriodicCheck()
  }

  private initializeSnapshots() {
    // 初始化路由快照
    this.takeRouteSnapshot()
    this.takeAPISnapshot()
  }

  private takeRouteSnapshot() {
    this.lastSnapshot.clear()

    // 从ROUTE_CONFIG提取路由信息
    const extractRoutes = (configs: any[], prefix = '') => {
      configs.forEach(config => {
        if (config.path) {
          const routeKey = prefix + config.path
          this.lastSnapshot.set(routeKey, {
            route: routeKey,
            permissions: config.permissions || [],
            component: config.component?.name || 'Unknown',
            params: this.extractParams(config.path),
            query: []
          })
        }

        if (config.children) {
          extractRoutes(config.children, prefix + (config.path || ''))
        }
      })
    }

    extractRoutes(ROUTE_CONFIG)
  }

  private takeAPISnapshot() {
    this.lastAPISnapshot.clear()

    // 从API配置提取端点信息
    const apiEndpoints = this.extractAPIEndpoints()
    apiEndpoints.forEach(endpoint => {
      this.lastAPISnapshot.set(`${endpoint.method}:${endpoint.endpoint}`, endpoint)
    })
  }

  private extractParams(path: string): string[] {
    const params: string[] = []
    const paramRegex = /:([^\/]+)/g
    let match

    while ((match = paramRegex.exec(path)) !== null) {
      params.push(match[1])
    }

    return params
  }

  private extractAPIEndpoints(): APIChangeConfig[] {
    // 这里应该从实际的API配置中提取
    // 简化版本，返回已知的API端点
    return [
      {
        endpoint: '/api/v1/assets',
        method: 'GET',
        permissions: [{ resource: 'asset', action: 'view' }],
        version: 'v1'
      },
      {
        endpoint: '/api/v1/assets',
        method: 'POST',
        permissions: [{ resource: 'asset', action: 'create' }],
        version: 'v1'
      },
      {
        endpoint: '/api/v1/assets/{asset_id}',
        method: 'PUT',
        permissions: [{ resource: 'asset', action: 'edit' }],
        version: 'v1'
      },
      {
        endpoint: '/api/v1/users',
        method: 'GET',
        permissions: [{ resource: 'user', action: 'view' }],
        version: 'v1'
      }
    ]
  }

  private startPeriodicCheck() {
    // 每30秒检查一次变更
    this.checkInterval = setInterval(() => {
      this.detectChanges()
    }, 30000)
  }

  public detectChanges(): ChangeDetection | null {
    const currentRoutes = new Map<string, RouteChangeConfig>()
    const currentAPIs = new Map<string, APIChangeConfig>()

    // 获取当前路由配置
    const extractCurrentRoutes = (configs: any[], prefix = '') => {
      configs.forEach(config => {
        if (config.path) {
          const routeKey = prefix + config.path
          currentRoutes.set(routeKey, {
            route: routeKey,
            permissions: config.permissions || [],
            component: config.component?.name || 'Unknown',
            params: this.extractParams(config.path),
            query: []
          })
        }

        if (config.children) {
          extractCurrentRoutes(config.children, prefix + (config.path || ''))
        }
      })
    }

    extractCurrentRoutes(ROUTE_CONFIG)

    // 获取当前API配置
    const currentAPIEndpoints = this.extractAPIEndpoints()
    currentAPIEndpoints.forEach(endpoint => {
      currentAPIs.set(`${endpoint.method}:${endpoint.endpoint}`, endpoint)
    })

    // 检测路由变更
    const routeChanges = {
      added: [] as RouteChangeConfig[],
      removed: [] as RouteChangeConfig[],
      modified: [] as Array<{
        route: string
        old: RouteChangeConfig
        new: RouteChangeConfig
      }>
    }

    // 检测新增的路由
    for (const [key, route] of currentRoutes) {
      if (!this.lastSnapshot.has(key)) {
        routeChanges.added.push(route)
      }
    }

    // 检测删除的路由
    for (const [key, route] of this.lastSnapshot) {
      if (!currentRoutes.has(key)) {
        routeChanges.removed.push(route)
      }
    }

    // 检测修改的路由
    for (const [key, currentRoute] of currentRoutes) {
      const lastRoute = this.lastSnapshot.get(key)
      if (lastRoute && this.routesDiffer(lastRoute, currentRoute)) {
        routeChanges.modified.push({
          route: key,
          old: lastRoute,
          new: currentRoute
        })
      }
    }

    // 检测API变更
    const apiChanges = {
      added: [] as APIChangeConfig[],
      removed: [] as APIChangeConfig[],
      modified: [] as Array<{
        endpoint: string
        old: APIChangeConfig
        new: APIChangeConfig
      }>
    }

    // 检测新增的API
    for (const [key, api] of currentAPIs) {
      if (!this.lastAPISnapshot.has(key)) {
        apiChanges.added.push(api)
      }
    }

    // 检测删除的API
    for (const [key, api] of this.lastAPISnapshot) {
      if (!currentAPIs.has(key)) {
        apiChanges.removed.push(api)
      }
    }

    // 检测修改的API
    for (const [key, currentAPI] of currentAPIs) {
      const lastAPI = this.lastAPISnapshot.get(key)
      if (lastAPI && this.apisDiffer(lastAPI, currentAPI)) {
        apiChanges.modified.push({
          endpoint: key,
          old: lastAPI,
          new: currentAPI
        })
      }
    }

    // 如果有变更，记录并更新快照
    const hasChanges = routeChanges.added.length > 0 ||
                     routeChanges.removed.length > 0 ||
                     routeChanges.modified.length > 0 ||
                     apiChanges.added.length > 0 ||
                     apiChanges.removed.length > 0 ||
                     apiChanges.modified.length > 0

    if (hasChanges) {
      const changeDetection: ChangeDetection = {
        timestamp: Date.now(),
        changes: routeChanges,
        api_changes: apiChanges
      }

      this.changeHistory.push(changeDetection)

      // 保持历史记录在限制范围内
      if (this.changeHistory.length > this.maxHistorySize) {
        this.changeHistory = this.changeHistory.slice(-this.maxHistorySize)
      }

      // 更新快照
      this.lastSnapshot = currentRoutes
      this.lastAPISnapshot = currentAPIs

      // 上报变更
      this.reportChanges(changeDetection)

      return changeDetection
    }

    return null
  }

  private routesDiffer(route1: RouteChangeConfig, route2: RouteChangeConfig): boolean {
    return JSON.stringify(route1.permissions) !== JSON.stringify(route2.permissions) ||
           route1.component !== route2.component
  }

  private apisDiffer(api1: APIChangeConfig, api2: APIChangeConfig): boolean {
    return JSON.stringify(api1.permissions) !== JSON.stringify(api2.permissions) ||
           api1.version !== api2.version ||
           api1.deprecated !== api2.deprecated
  }

  private async reportChanges(changes: ChangeDetection) {
    try {
      // 发送变更报告到监控服务
      await fetch('/api/v1/monitoring/route-changes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(changes)
      })

      console.log('路由变更已上报', changes)

      // 如果有重大变更，显示通知
      if (this.hasBreakingChanges(changes)) {
        this.showBreakingChangeNotification(changes)
      }

    } catch (error) {
      console.warn('路由变更上报失败:', error)
    }
  }

  private hasBreakingChanges(changes: ChangeDetection): boolean {
    // 检查是否有破坏性变更
    const { removed, modified } = changes.changes
    const { removed: apiRemoved, modified: apiModified } = changes.api_changes

    // 删除路由或API是破坏性变更
    if (removed.length > 0 || apiRemoved.length > 0) {
      return true
    }

    // 权限变更是破坏性变更
    const permissionChanges = modified.filter(change =>
      JSON.stringify(change.old.permissions) !== JSON.stringify(change.new.permissions)
    )

    const apiPermissionChanges = apiModified.filter(change =>
      JSON.stringify(change.old.permissions) !== JSON.stringify(change.new.permissions)
    )

    return permissionChanges.length > 0 || apiPermissionChanges.length > 0
  }

  private showBreakingChangeNotification(changes: ChangeDetection) {
    // 显示破坏性变更通知
    const notification = new Notification('路由配置已更新', {
      body: '检测到破坏性变更，请查看控制台了解详情',
      icon: '/favicon.ico'
    })

    if (notification) {
      notification.onclick = () => {
        window.focus()
        console.group('🚨 路由变更详情')
        console.log('变更时间:', new Date(changes.timestamp))
        console.log('路由变更:', changes.changes)
        console.log('API变更:', changes.api_changes)
        console.groupEnd()
      }
    }
  }

  public getChangeHistory(): ChangeDetection[] {
    return [...this.changeHistory]
  }

  public getLastChange(): ChangeDetection | null {
    return this.changeHistory.length > 0 ? this.changeHistory[this.changeHistory.length - 1] : null
  }

  public getBreakingChanges(): ChangeDetection[] {
    return this.changeHistory.filter(changes => this.hasBreakingChanges(changes))
  }

  public manualCheck(): ChangeDetection | null {
    return this.detectChanges()
  }

  public destroy() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
    }
  }
}

// 全局变更检测器实例
const globalChangeDetector = new RouteChangeDetector()

// Hook for using the change detector
export const useRouteChangeDetector = () => {
  const detector = globalChangeDetector

  const checkChanges = useCallback(() => {
    return detector.manualCheck()
  }, [detector])

  const getHistory = useCallback(() => {
    return detector.getChangeHistory()
  }, [detector])

  const getLastChange = useCallback(() => {
    return detector.getLastChange()
  }, [detector])

  const getBreakingChanges = useCallback(() => {
    return detector.getBreakingChanges()
  }, [detector])

  return {
    checkChanges,
    getHistory,
    getLastChange,
    getBreakingChanges,
    detector
  }
}

// 开发模式下的调试工具
export const useRouteChangeDebug = () => {
  const { getHistory, getLastChange, checkChanges } = useRouteChangeDetector()

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      // 暴露到全局对象用于调试
      (window as any).__ROUTE_CHANGE_DETECTOR__ = {
        getHistory,
        getLastChange,
        checkChanges,
        exportHistory: () => ({
          history: getHistory(),
          timestamp: Date.now()
        })
      }

      console.log('路由变更检测器已启用')
      console.log('使用 window.__ROUTE_CHANGE_DETECTOR__ 访问调试工具')
    }
  }, [getHistory, getLastChange, checkChanges])
}

export default RouteChangeDetector