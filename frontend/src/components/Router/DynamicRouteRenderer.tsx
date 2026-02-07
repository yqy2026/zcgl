import React, { useCallback, useMemo, useState, ReactNode, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { PermissionGuard } from '@/components/System/PermissionGuard';
import { componentLogger } from './DynamicRouteLoaderCore';
import { useDynamicRoute } from './DynamicRouteContext';
import type { DynamicRoute } from './dynamicRouteTypes';

export const DynamicRouteRenderer: React.FC = () => {
  const { routes } = useDynamicRoute();
  const [error, setError] = useState<string | null>(null);

  const routeList = useMemo(() => Array.from(routes.values()), [routes]);

  // 将路由转换为React Router格式
  const renderRoutes = useCallback((routeList: DynamicRoute[], parentPath = ''): ReactNode[] => {
    return routeList.map(route => {
      const fullPath = parentPath + route.path;

      const element = (
        <Suspense fallback={<div>Loading {route.meta?.title ?? route.id}...</div>}>
          <ErrorBoundary
            onError={error => {
              componentLogger.error(`Route ${route.id} error:`, error);
              setError(`Failed to load ${route.meta?.title ?? route.id}`);
            }}
            fallback={<div>Error loading {route.meta?.title ?? route.id}</div>}
          >
            {route.permissions != null && route.permissions.length > 0 ? (
              <PermissionGuard permissions={route.permissions}>
                <route.component />
              </PermissionGuard>
            ) : (
              <route.component />
            )}
          </ErrorBoundary>
        </Suspense>
      );

      if (route.children && route.children.length > 0) {
        return (
          <Route key={route.id} path={route.path} element={element}>
            {renderRoutes(route.children, fullPath)}
          </Route>
        );
      }

      return <Route key={route.id} path={route.path} element={element} />;
    });
  }, []);

  const renderedRoutes = useMemo(() => renderRoutes(routeList), [renderRoutes, routeList]);

  if (error != null) {
    return (
      <div
        style={{
          padding: '50px',
          textAlign: 'center',
          color: '#ff4d4f',
        }}
      >
        <h2>路由加载错误</h2>
        <p>{error}</p>
        <button onClick={() => setError(null)}>重试</button>
      </div>
    );
  }

  return (
    <Routes>
      {/* 默认重定向 */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* 动态路由 */}
      {renderedRoutes}

      {/* 404页面 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

interface ErrorBoundaryProps {
  children: ReactNode;
  onError?: (error: Error) => void;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, _errorInfo: React.ErrorInfo) {
    componentLogger.error('Route Error Boundary caught an error:', error);
    this.props.onError?.(error);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div
            style={{
              padding: '20px',
              textAlign: 'center',
              color: '#ff4d4f',
              border: '1px solid #ff4d4f',
              borderRadius: '6px',
              margin: '20px',
            }}
          >
            <h3>路由加载失败</h3>
            <p>{this.state.error?.message}</p>
            <button onClick={() => this.setState({ hasError: false, error: null })}>重试</button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
