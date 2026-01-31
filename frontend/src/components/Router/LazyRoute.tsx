import React, { Suspense } from 'react';
import { Route } from 'react-router-dom';
import { SkeletonLoader } from '@/components/Loading';
import { RouteConfig } from '@/constants/routes';
import { SystemErrorBoundary } from '@/components/ErrorHandling';
import { PermissionGuard } from '@/components/System/PermissionGuard';

interface LazyRouteProps extends Omit<RouteConfig, 'children'> {
  component: React.LazyExoticComponent<React.ComponentType<Record<string, unknown>>>;
  fallback?: React.ReactNode;
  preload?: () => void;
  exact?: boolean;
  errorBoundary?: boolean;
}

/**
 * 懒加载路由组件
 * 支持预加载、自定义加载状态
 */
const LazyRoute: React.FC<LazyRouteProps> = ({
  component: Component,
  fallback = <SkeletonLoader type="detail" rows={5} />,
  preload,
  permissions,
  errorBoundary = true,
  ...routeProps
}) => {
  // 如果提供了预加载函数，在组件加载时执行
  const _handleMouseEnter = () => {
    if (preload != null) {
      preload();
    }
  };

  const renderElement = () => {
    const WrappedComponent = (
      <Suspense fallback={fallback}>
        <Component />
      </Suspense>
    );

    // 如果没有权限要求，直接渲染懒加载组件
    if (permissions == null || permissions.length === 0) {
      return WrappedComponent;
    }

    // 有权限要求，使用权限守卫包装
    return (
      <PermissionGuard permissions={permissions} mode="any">
        {WrappedComponent}
      </PermissionGuard>
    );
  };

  const wrappedElement = errorBoundary ? (
    <SystemErrorBoundary>{renderElement()}</SystemErrorBoundary>
  ) : (
    renderElement()
  );

  return <Route {...routeProps} element={wrappedElement} />;
};

export default LazyRoute;
