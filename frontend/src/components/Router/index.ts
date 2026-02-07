// 路由组件统一导出

export { default as ProtectedRoute } from './ProtectedRoute';
export { default as LazyRoute } from './LazyRoute';
export { default as RouteBuilder } from './RouteBuilder';
export { default as RouteTransitions } from './RouteTransitions';
export { default as RouteABTesting } from './RouteABTesting';
export { default as DynamicRouteLoader } from './DynamicRouteLoader';
export { default as DynamicRouteLoaderCore } from './DynamicRouteLoaderCore';
export {
  DynamicRouteProvider,
  useDynamicRoute,
  usePermissionBasedRoutes,
} from './DynamicRouteContext';
export { DynamicRouteRenderer } from './DynamicRouteRenderer';
export { RouteModuleLoader } from './RouteModuleLoader';
export type {
  DynamicRoute,
  DynamicRouteConfig,
  RouteLoaderContextType,
  RouteMetrics,
  DynamicRouteMeta,
  DynamicRoutePermission,
} from './dynamicRouteTypes';
