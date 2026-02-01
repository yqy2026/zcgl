import { useState, useCallback } from 'react';
import { componentLogger } from './DynamicRouteLoaderCore';
import { useDynamicRoute } from './DynamicRouteContext';

export const RouteModuleLoader = () => {
  const { loadRouteModule } = useDynamicRoute();
  const [loading, setLoading] = useState(false);
  const [loadedModules, setLoadedModules] = useState<string[]>([]);

  const loadModule = useCallback(
    async (modulePath: string) => {
      setLoading(true);
      try {
        const routes = await loadRouteModule(modulePath);
        setLoadedModules(prev => [...prev, modulePath]);
        return routes;
      } catch (error) {
        componentLogger.error('Failed to load route module:', error as Error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [loadRouteModule]
  );

  return {
    loadModule,
    loading,
    loadedModules,
  };
};
