import type { ComponentType, LazyExoticComponent } from 'react';

export interface DynamicRoutePermission {
  resource: string;
  action: string;
}

export interface DynamicRouteMeta {
  title?: string;
  description?: string;
  icon?: string;
  breadcrumb?: string[];
  cacheable?: boolean;
  preload?: boolean;
}

export interface DynamicRoute {
  id: string;
  path: string;
  component: LazyExoticComponent<ComponentType<Record<string, unknown>>>;
  permissions?: DynamicRoutePermission[];
  exact?: boolean;
  children?: DynamicRoute[];
  meta?: DynamicRouteMeta;
}

export interface DynamicRouteConfig {
  routes: DynamicRoute[];
  fallback?: ComponentType;
  errorBoundary?: ComponentType;
  loadingComponent?: ComponentType;
}

export interface RouteMetrics {
  totalRoutes: number;
  loadedRoutes: number;
  loadingRoutes: number;
  errorRoutes: number;
  cacheHits: number;
  averageLoadTime: number;
}

export interface RouteLoaderContextType {
  routes: Map<string, DynamicRoute>;
  registerRoute: (route: DynamicRoute) => void;
  unregisterRoute: (routeId: string) => void;
  updateRoute: (routeId: string, updates: Partial<DynamicRoute>) => void;
  loadRouteModule: (modulePath: string) => Promise<DynamicRoute[]>;
  isRouteLoaded: (routeId: string) => boolean;
  getRouteMetrics: () => RouteMetrics;
  getRoutesByPermission: (resource: string, action: string) => DynamicRoute[];
}
