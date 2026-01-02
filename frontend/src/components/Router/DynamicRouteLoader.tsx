/**
 * 动态路由加载器
 * 支持运行时动态注册路由、模块化路由和权限路由
 */

import React, { createContext, useContext, useState, ReactNode, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { PermissionGuard } from '../System/PermissionGuard'

interface DynamicRoute {
  id: string
  path: string
  component: React.LazyExoticComponent<React.ComponentType<Record<string, unknown>>>
  permissions?: Array<{ resource: string; action: string }>
  exact?: boolean
  children?: DynamicRoute[]
  meta?: {
    title?: string
    description?: string
    icon?: string
    breadcrumb?: string[]
    cacheable?: boolean
    preload?: boolean
  }
}

interface DynamicRouteConfig {
  routes: DynamicRoute[]
  fallback?: React.ComponentType
  errorBoundary?: React.ComponentType
  loadingComponent?: React.ComponentType
}

interface RouteLoaderContextType {
  routes: Map<string, DynamicRoute>
  registerRoute: (route: DynamicRoute) => void
  unregisterRoute: (routeId: string) => void
  updateRoute: (routeId: string, updates: Partial<DynamicRoute>) => void
  loadRouteModule: (modulePath: string) => Promise<DynamicRoute[]>
  isRouteLoaded: (routeId: string) => boolean
  getRouteMetrics: () => RouteMetrics
  getRoutesByPermission: (resource: string, action: string) => DynamicRoute[]
}

interface RouteMetrics {
  totalRoutes: number
  loadedRoutes: number
  loadingRoutes: number
  errorRoutes: number
  cacheHits: number
  averageLoadTime: number
}

class DynamicRouteLoader {
  private routes: Map<string, DynamicRoute>
  private loadedModules: Map<string, Record<string, unknown>>
  private routeMetrics: Map<string, {
    loadTime: number
    loadCount: number
    lastLoaded: number
    errorCount: number
  }>
  private loadPromises: Map<string, Promise<DynamicRoute[]>>
  private defaultConfig: DynamicRouteConfig

  constructor(config?: Partial<DynamicRouteConfig>) {
    this.routes = new Map()
    this.loadedModules = new Map()
    this.routeMetrics = new Map()
    this.loadPromises = new Map()
    this.defaultConfig = {
      routes: [],
      fallback: () => <div>Route not found</div>,
      loadingComponent: () => <div>Loading...</div>,
      ...config
    }

    this.initializeDefaultRoutes()
  }

  private initializeDefaultRoutes() {
    // 初始化核心路由
    const coreRoutes: DynamicRoute[] = [
      {
        id: 'dashboard',
        path: '/dashboard',
        component: React.lazy(() => import('../../pages/Dashboard/DashboardPage')),
        meta: {
          title: '工作台',
          icon: 'dashboard',
          breadcrumb: ['工作台'],
          cacheable: true
        }
      }
    ]

    coreRoutes.forEach(route => {
      this.routes.set(route.id, route)
    })
  }

  public registerRoute(route: DynamicRoute) {
    // 检查路由是否已存在
    if (this.routes.has(route.id)) {
      console.warn(`Route ${route.id} already exists, updating instead`)
      this.updateRoute(route.id, route)
      return
    }

    // 验证路由配置
    this.validateRoute(route)

    // 注册路由
    this.routes.set(route.id, route)

    // 预加载路由（如果配置了）
    if (route.meta?.preload) {
      this.preloadRoute(route)
    }

    // Dynamic route registered
  }

  public unregisterRoute(routeId: string) {
    if (this.routes.has(routeId)) {
      this.routes.delete(routeId)
      this.routeMetrics.delete(routeId)
      // Dynamic route unregistered
    }
  }

  public updateRoute(routeId: string, updates: Partial<DynamicRoute>) {
    const existingRoute = this.routes.get(routeId)
    if (existingRoute) {
      const updatedRoute = { ...existingRoute, ...updates }
      this.routes.set(routeId, updatedRoute)
      // Dynamic route updated
    }
  }

  public async loadRouteModule(modulePath: string): Promise<DynamicRoute[]> {
    // 检查是否已在加载中
    if (this.loadPromises.has(modulePath)) {
      return this.loadPromises.get(modulePath)!
    }

    const startTime = performance.now()
    const loadPromise = this.performModuleLoad(modulePath, startTime)
    this.loadPromises.set(modulePath, loadPromise)

    try {
      const routes = await loadPromise
      return routes
    } finally {
      this.loadPromises.delete(modulePath)
    }
  }

  private async performModuleLoad(modulePath: string, startTime: number): Promise<DynamicRoute[]> {
    try {
      // 动态导入模块
      const module = await import(modulePath)
      this.loadedModules.set(modulePath, module)

      // 从模块中提取路由配置
      const routes = this.extractRoutesFromModule(module, modulePath)

      // 注册路由
      routes.forEach(route => {
        this.registerRoute(route)

        // 记录加载指标
        this.recordLoadMetrics(route.id, performance.now() - startTime)
      })

      return routes
    } catch (error) {
      console.error(`Failed to load route module: ${modulePath}`, error)
      throw error
    }
  }

  private extractRoutesFromModule(module: {
    routes?: DynamicRoute[];
    default?: React.LazyExoticComponent<React.ComponentType<Record<string, unknown>>>;
  }, modulePath: string): DynamicRoute[] {
    // 模块应该导出 routes 数组
    if (module.routes && Array.isArray(module.routes)) {
      return module.routes
    }

    // 如果模块是单个组件，创建包装路由
    if (module.default) {
      const componentName = modulePath.split('/').pop()?.replace(/\.(tsx?|jsx?)$/, '') || 'DynamicComponent'
      return [{
        id: componentName.toLowerCase(),
        path: `/dynamic/${componentName.toLowerCase()}`,
        component: module.default
      }]
    }

    return []
  }

  private validateRoute(route: DynamicRoute) {
    if (!route.id) {
      throw new Error('Route must have an id')
    }

    if (!route.path) {
      throw new Error('Route must have a path')
    }

    if (!route.component) {
      throw new Error('Route must have a component')
    }
  }

  private async preloadRoute(route: DynamicRoute) {
    try {
      // 预加载组件
      await route.component
      // Route preloaded
    } catch (error) {
      console.warn(`Failed to preload route: ${route.id}`, error)
    }
  }

  private recordLoadMetrics(routeId: string, loadTime: number) {
    const existing = this.routeMetrics.get(routeId) || {
      loadTime: 0,
      loadCount: 0,
      lastLoaded: 0,
      errorCount: 0
    }

    this.routeMetrics.set(routeId, {
      loadTime: (existing.loadTime * existing.loadCount + loadTime) / (existing.loadCount + 1),
      loadCount: existing.loadCount + 1,
      lastLoaded: Date.now(),
      errorCount: existing.errorCount
    })
  }

  public isRouteLoaded(routeId: string): boolean {
    return this.routes.has(routeId)
  }

  public getRoutes(): DynamicRoute[] {
    return Array.from(this.routes.values())
  }

  public getRouteMetrics(): RouteMetrics {
    const metrics = Array.from(this.routeMetrics.values())

    if (metrics.length === 0) {
      return {
        totalRoutes: this.routes.size,
        loadedRoutes: this.routes.size,
        loadingRoutes: 0,
        errorRoutes: 0,
        cacheHits: 0,
        averageLoadTime: 0
      }
    }

    const totalLoadTime = metrics.reduce((sum, m) => sum + m.loadTime, 0)
    const totalErrors = metrics.reduce((sum, m) => sum + m.errorCount, 0)

    return {
      totalRoutes: this.routes.size,
      loadedRoutes: this.routes.size,
      loadingRoutes: this.loadPromises.size,
      errorRoutes: totalErrors,
      cacheHits: 0, // 可以实现缓存命中统计
      averageLoadTime: totalLoadTime / metrics.length
    }
  }

  public async loadRouteById(routeId: string) {
    const route = this.routes.get(routeId)
    if (!route) {
      throw new Error(`Route not found: ${routeId}`)
    }

    // 如果组件还未加载，尝试加载
    try {
      await route.component
      return route
    } catch (error) {
      console.error(`Failed to load route component: ${routeId}`, error)
      throw error
    }
  }

  public searchRoutes(query: string): DynamicRoute[] {
    const lowerQuery = query.toLowerCase()
    return Array.from(this.routes.values()).filter(route =>
      route.id.toLowerCase().includes(lowerQuery) ||
      route.path.toLowerCase().includes(lowerQuery) ||
      route.meta?.title?.toLowerCase().includes(lowerQuery)
    )
  }

  public getRoutesByPermission(resource: string, action: string): DynamicRoute[] {
    return Array.from(this.routes.values()).filter(route =>
      route.permissions?.some(p => p.resource === resource && p.action === action)
    )
  }
}

// 动态路由上下文
const DynamicRouteContext = createContext<RouteLoaderContextType | null>(null)

// 动态路由提供者
interface DynamicRouteProviderProps {
  children: ReactNode
  config?: Partial<DynamicRouteConfig>
  onRouteLoad?: (route: DynamicRoute) => void
  onRouteError?: (error: Error, routeId: string) => void
}

export const DynamicRouteProvider: React.FC<DynamicRouteProviderProps> = ({
  children,
  config,
  onRouteLoad,
  onRouteError
}) => {
  const [loader] = useState(() => new DynamicRouteLoader(config))
  const [_loadingRoutes, _setLoadingRoutes] = useState<Set<string>>(new Set())

  const registerRoute = (route: DynamicRoute) => {
    loader.registerRoute(route)
    onRouteLoad?.(route)
  }

  const unregisterRoute = (routeId: string) => {
    loader.unregisterRoute(routeId)
  }

  const updateRoute = (routeId: string, updates: Partial<DynamicRoute>) => {
    loader.updateRoute(routeId, updates)
  }

  const loadRouteModule = async (modulePath: string) => {
    _setLoadingRoutes((prev: Set<string>) => new Set(prev).add(modulePath))

    try {
      const routes = await loader.loadRouteModule(modulePath)
      return routes
    } catch (error) {
      onRouteError?.(error as Error, modulePath)
      throw error
    } finally {
      _setLoadingRoutes((prev: Set<string>) => {
        const newSet = new Set(prev)
        newSet.delete(modulePath)
        return newSet
      })
    }
  }

  const isRouteLoaded = (routeId: string) => {
    return loader.isRouteLoaded(routeId)
  }

  const getRouteMetrics = () => {
    return loader.getRouteMetrics()
  }

  const getRoutesByPermission = (resource: string, action: string) => {
    return loader.getRoutesByPermission(resource, action)
  }

  const contextValue: RouteLoaderContextType = {
    routes: new Map(loader.getRoutes().map(route => [route.id, route])),
    registerRoute,
    unregisterRoute,
    updateRoute,
    loadRouteModule,
    isRouteLoaded,
    getRouteMetrics,
    getRoutesByPermission
  }

  return (
    <DynamicRouteContext.Provider value={contextValue}>
      {children}
    </DynamicRouteContext.Provider>
  )
}

// 动态路由Hook
export const useDynamicRoute = () => {
  const context = useContext(DynamicRouteContext)
  if (!context) {
    throw new Error('useDynamicRoute must be used within DynamicRouteProvider')
  }

  return context
}

// 动态路由渲染器
export const DynamicRouteRenderer: React.FC = () => {
  const { routes } = useDynamicRoute()
  const [error, setError] = useState<string | null>(null)

  // 将路由转换为React Router格式
  const renderRoutes = (routeList: DynamicRoute[], parentPath = ''): ReactNode[] => {
    return routeList.map(route => {
      const fullPath = parentPath + route.path

      const element = (
        <Suspense fallback={<div>Loading {route.meta?.title || route.id}...</div>}>
          <ErrorBoundary
            onError={(error) => {
              console.error(`Route ${route.id} error:`, error)
              setError(`Failed to load ${route.meta?.title || route.id}`)
            }}
            fallback={<div>Error loading {route.meta?.title || route.id}</div>}
          >
            {route.permissions && route.permissions.length > 0 ? (
              <PermissionGuard permissions={route.permissions}>
                <route.component />
              </PermissionGuard>
            ) : (
              <route.component />
            )}
          </ErrorBoundary>
        </Suspense>
      )

      if (route.children && route.children.length > 0) {
        return (
          <Route
            key={route.id}
            path={route.path}
            element={element}
          >
            {renderRoutes(route.children, fullPath)}
          </Route>
        )
      }

      return (
        <Route
          key={route.id}
          path={route.path}
          element={element}
        />
      )
    })
  }

  if (error) {
    return (
      <div style={{
        padding: '50px',
        textAlign: 'center',
        color: '#ff4d4f'
      }}>
        <h2>路由加载错误</h2>
        <p>{error}</p>
        <button onClick={() => setError(null)}>重试</button>
      </div>
    )
  }

  return (
    <Routes>
      {/* 默认重定向 */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* 动态路由 */}
      {renderRoutes(Array.from(routes.values()))}

      {/* 404页面 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

// 错误边界组件
interface ErrorBoundaryProps {
  children: ReactNode
  onError?: (error: Error) => void
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Route Error Boundary caught an error:', error, errorInfo)
    this.props.onError?.(error)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{
          padding: '20px',
          textAlign: 'center',
          color: '#ff4d4f',
          border: '1px solid #ff4d4f',
          borderRadius: '6px',
          margin: '20px'
        }}>
          <h3>路由加载失败</h3>
          <p>{this.state.error?.message}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            重试
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

// 权限路由加载器
export const usePermissionBasedRoutes = () => {
  const { getRoutesByPermission, routes } = useDynamicRoute()

  const loadRoutesByPermissions = async (permissions: Array<{ resource: string; action: string }>) => {
    const permissionRoutes: DynamicRoute[] = []

    for (const permission of permissions) {
      const routes = getRoutesByPermission(permission.resource, permission.action)
      permissionRoutes.push(...routes)
    }

    return permissionRoutes
  }

  return {
    loadRoutesByPermissions,
    availableRoutes: Array.from(routes.values())
  }
}

// 路由模块加载器
export const RouteModuleLoader = () => {
  const { loadRouteModule } = useDynamicRoute()
  const [loading, setLoading] = useState(false)
  const [loadedModules, setLoadedModules] = useState<string[]>([])

  const loadModule = async (modulePath: string) => {
    setLoading(true)
    try {
      const routes = await loadRouteModule(modulePath)
      setLoadedModules(prev => [...prev, modulePath])
      return routes
    } catch (error) {
      console.error('Failed to load route module:', error)
      throw error
    } finally {
      setLoading(false)
    }
  }

  return {
    loadModule,
    loading,
    loadedModules
  }
}

export default DynamicRouteLoader