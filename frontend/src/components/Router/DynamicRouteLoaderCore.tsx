import React from 'react';
import { createLogger } from '@/utils/logger';
import type { DynamicRoute, DynamicRouteConfig, RouteMetrics } from './dynamicRouteTypes';

export const componentLogger = createLogger('DynamicRouteLoader');

class DynamicRouteLoader {
  private routes: Map<string, DynamicRoute>;
  private loadedModules: Map<string, Record<string, unknown>>;
  private routeMetrics: Map<
    string,
    {
      loadTime: number;
      loadCount: number;
      lastLoaded: number;
      errorCount: number;
    }
  >;
  private loadPromises: Map<string, Promise<DynamicRoute[]>>;
  private defaultConfig: DynamicRouteConfig;

  constructor(config?: Partial<DynamicRouteConfig>) {
    this.routes = new Map();
    this.loadedModules = new Map();
    this.routeMetrics = new Map();
    this.loadPromises = new Map();
    this.defaultConfig = {
      routes: [],
      fallback: () => <div>Route not found</div>,
      loadingComponent: () => <div>Loading...</div>,
      ...config,
    };

    this.initializeDefaultRoutes();
  }

  private initializeDefaultRoutes() {
    // 初始化核心路由
    const coreRoutes: DynamicRoute[] = [
      {
        id: 'dashboard',
        path: '/dashboard',
        component: React.lazy(() => import('@/pages/Dashboard/DashboardPage')),
        meta: {
          title: '工作台',
          icon: 'dashboard',
          breadcrumb: ['工作台'],
          cacheable: true,
        },
      },
    ];

    coreRoutes.forEach(route => {
      this.routes.set(route.id, route);
    });
  }

  public registerRoute(route: DynamicRoute) {
    // 检查路由是否已存在
    if (this.routes.has(route.id)) {
      componentLogger.warn(`Route ${route.id} already exists, updating instead`);
      this.updateRoute(route.id, route);
      return;
    }

    // 验证路由配置
    this.validateRoute(route);

    // 注册路由
    this.routes.set(route.id, route);

    // 预加载路由（如果配置了）
    if (route.meta?.preload === true) {
      this.preloadRoute(route);
    }

    // Dynamic route registered
  }

  public unregisterRoute(routeId: string) {
    if (this.routes.has(routeId)) {
      this.routes.delete(routeId);
      this.routeMetrics.delete(routeId);
      // Dynamic route unregistered
    }
  }

  public updateRoute(routeId: string, updates: Partial<DynamicRoute>) {
    const existingRoute = this.routes.get(routeId);
    if (existingRoute !== undefined && existingRoute !== null) {
      const updatedRoute = { ...existingRoute, ...updates };
      this.routes.set(routeId, updatedRoute);
      // Dynamic route updated
    }
  }

  public async loadRouteModule(modulePath: string): Promise<DynamicRoute[]> {
    // 检查是否已在加载中
    if (this.loadPromises.has(modulePath)) {
      return this.loadPromises.get(modulePath)!;
    }

    const startTime = performance.now();
    const loadPromise = this.performModuleLoad(modulePath, startTime);
    this.loadPromises.set(modulePath, loadPromise);

    try {
      const routes = await loadPromise;
      return routes;
    } finally {
      this.loadPromises.delete(modulePath);
    }
  }

  private async performModuleLoad(modulePath: string, startTime: number): Promise<DynamicRoute[]> {
    try {
      // 动态导入模块
      const module = await import(modulePath);
      this.loadedModules.set(modulePath, module);

      // 从模块中提取路由配置
      const routes = this.extractRoutesFromModule(module, modulePath);

      // 注册路由
      routes.forEach(route => {
        this.registerRoute(route);

        // 记录加载指标
        this.recordLoadMetrics(route.id, performance.now() - startTime);
      });

      return routes;
    } catch (error) {
      componentLogger.error(`Failed to load route module: ${modulePath}`, error as Error);
      throw error;
    }
  }

  private extractRoutesFromModule(
    module: {
      routes?: DynamicRoute[];
      default?: React.LazyExoticComponent<React.ComponentType<Record<string, unknown>>>;
    },
    modulePath: string
  ): DynamicRoute[] {
    // 模块应该导出 routes 数组
    if (module.routes && Array.isArray(module.routes)) {
      return module.routes;
    }

    // 如果模块是单个组件，创建包装路由
    if (module.default != null) {
      const componentName =
        modulePath
          .split('/')
          .pop()
          ?.replace(/\.(tsx?|jsx?)$/, '') ?? 'DynamicComponent';
      return [
        {
          id: componentName.toLowerCase(),
          path: `/dynamic/${componentName.toLowerCase()}`,
          component: module.default,
        },
      ];
    }

    return [];
  }

  private validateRoute(route: DynamicRoute) {
    if (!route.id) {
      throw new Error('Route must have an id');
    }

    if (route.path == null) {
      throw new Error('Route must have a path');
    }

    if (route.component == null) {
      throw new Error('Route must have a component');
    }
  }

  private async preloadRoute(route: DynamicRoute) {
    try {
      // 预加载组件
      await route.component;
      // Route preloaded
    } catch (error) {
      componentLogger.warn(`Failed to preload route: ${route.id} - ${String(error)}`);
    }
  }

  private recordLoadMetrics(routeId: string, loadTime: number) {
    const existing = this.routeMetrics.get(routeId) || {
      loadTime: 0,
      loadCount: 0,
      lastLoaded: 0,
      errorCount: 0,
    };

    this.routeMetrics.set(routeId, {
      loadTime: (existing.loadTime * existing.loadCount + loadTime) / (existing.loadCount + 1),
      loadCount: existing.loadCount + 1,
      lastLoaded: Date.now(),
      errorCount: existing.errorCount,
    });
  }

  public isRouteLoaded(routeId: string): boolean {
    return this.routes.has(routeId);
  }

  public getRoutes(): DynamicRoute[] {
    return Array.from(this.routes.values());
  }

  public getRouteMetrics(): RouteMetrics {
    const metrics = Array.from(this.routeMetrics.values());

    if (metrics.length === 0) {
      return {
        totalRoutes: this.routes.size,
        loadedRoutes: this.routes.size,
        loadingRoutes: 0,
        errorRoutes: 0,
        cacheHits: 0,
        averageLoadTime: 0,
      };
    }

    const totalLoadTime = metrics.reduce((sum, m) => sum + m.loadTime, 0);
    const totalErrors = metrics.reduce((sum, m) => sum + m.errorCount, 0);

    return {
      totalRoutes: this.routes.size,
      loadedRoutes: this.routes.size,
      loadingRoutes: this.loadPromises.size,
      errorRoutes: totalErrors,
      cacheHits: 0, // 可以实现缓存命中统计
      averageLoadTime: totalLoadTime / metrics.length,
    };
  }

  public async loadRouteById(routeId: string) {
    const route = this.routes.get(routeId);
    if (!route) {
      throw new Error(`Route not found: ${routeId}`);
    }

    // 如果组件还未加载，尝试加载
    try {
      await route.component;
      return route;
    } catch (error) {
      componentLogger.error(`Failed to load route component: ${routeId}`, error as Error);
      throw error;
    }
  }

  public searchRoutes(query: string): DynamicRoute[] {
    const lowerQuery = query.toLowerCase();
    return Array.from(this.routes.values()).filter(
      route =>
        route.id.toLowerCase().includes(lowerQuery) ||
        route.path.toLowerCase().includes(lowerQuery) ||
        (route.meta?.title?.toLowerCase().includes(lowerQuery) ?? false)
    );
  }

  public getRoutesByPermission(resource: string, action: string): DynamicRoute[] {
    return Array.from(this.routes.values()).filter(
      route =>
        route.permissions?.some(
          permission => permission.resource === resource && permission.action === action
        ) ?? false
    );
  }
}

export default DynamicRouteLoader;
