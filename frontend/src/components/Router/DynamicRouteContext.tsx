import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  ReactNode,
} from 'react';
import DynamicRouteLoader from './DynamicRouteLoaderCore';
import type {
  DynamicRoute,
  DynamicRouteConfig,
  RouteLoaderContextType,
} from './dynamicRouteTypes';

const DynamicRouteContext = createContext<RouteLoaderContextType | null>(null);

interface DynamicRouteProviderProps {
  children: ReactNode;
  config?: Partial<DynamicRouteConfig>;
  onRouteLoad?: (route: DynamicRoute) => void;
  onRouteError?: (error: Error, routeId: string) => void;
}

export const DynamicRouteProvider: React.FC<DynamicRouteProviderProps> = ({
  children,
  config,
  onRouteLoad,
  onRouteError,
}) => {
  const [loader] = useState(() => new DynamicRouteLoader(config));
  const [_loadingRoutes, _setLoadingRoutes] = useState<Set<string>>(new Set());

  const registerRoute = useCallback(
    (route: DynamicRoute) => {
      loader.registerRoute(route);
      onRouteLoad?.(route);
    },
    [loader, onRouteLoad]
  );

  const unregisterRoute = useCallback(
    (routeId: string) => {
      loader.unregisterRoute(routeId);
    },
    [loader]
  );

  const updateRoute = useCallback(
    (routeId: string, updates: Partial<DynamicRoute>) => {
      loader.updateRoute(routeId, updates);
    },
    [loader]
  );

  const loadRouteModule = useCallback(
    async (modulePath: string) => {
      _setLoadingRoutes((prev: Set<string>) => new Set(prev).add(modulePath));

      try {
        const routes = await loader.loadRouteModule(modulePath);
        return routes;
      } catch (error) {
        onRouteError?.(error as Error, modulePath);
        throw error;
      } finally {
        _setLoadingRoutes((prev: Set<string>) => {
          const newSet = new Set(prev);
          newSet.delete(modulePath);
          return newSet;
        });
      }
    },
    [loader, onRouteError]
  );

  const isRouteLoaded = useCallback(
    (routeId: string) => {
      return loader.isRouteLoaded(routeId);
    },
    [loader]
  );

  const getRouteMetrics = useCallback(() => {
    return loader.getRouteMetrics();
  }, [loader]);

  const getRoutesByPermission = useCallback(
    (resource: string, action: string) => {
      return loader.getRoutesByPermission(resource, action);
    },
    [loader]
  );

  const routesSnapshot = useMemo(
    () => new Map(loader.getRoutes().map(route => [route.id, route])),
    [loader, _loadingRoutes]
  );

  const contextValue = useMemo(
    () => ({
      routes: routesSnapshot,
      registerRoute,
      unregisterRoute,
      updateRoute,
      loadRouteModule,
      isRouteLoaded,
      getRouteMetrics,
      getRoutesByPermission,
    }),
    [
      getRouteMetrics,
      getRoutesByPermission,
      isRouteLoaded,
      loadRouteModule,
      registerRoute,
      routesSnapshot,
      unregisterRoute,
      updateRoute,
    ]
  );

  return (
    <DynamicRouteContext.Provider value={contextValue}>
      {children}
    </DynamicRouteContext.Provider>
  );
};

export const useDynamicRoute = () => {
  const context = useContext(DynamicRouteContext);
  if (!context) {
    throw new Error('useDynamicRoute must be used within DynamicRouteProvider');
  }

  return context;
};

export const usePermissionBasedRoutes = () => {
  const { getRoutesByPermission, routes } = useDynamicRoute();

  const loadRoutesByPermissions = useCallback(
    async (permissions: Array<{ resource: string; action: string }>) => {
      const permissionRoutes: DynamicRoute[] = [];

      for (const permission of permissions) {
        const matchedRoutes = getRoutesByPermission(
          permission.resource,
          permission.action
        );
        permissionRoutes.push(...matchedRoutes);
      }

      return permissionRoutes;
    },
    [getRoutesByPermission]
  );

  const availableRoutes = useMemo(() => Array.from(routes.values()), [routes]);

  return {
    loadRoutesByPermissions,
    availableRoutes,
  };
};
