import React from 'react';
import { Route } from 'react-router-dom';
import { SystemErrorBoundary } from '@/components/ErrorHandling';
import { PermissionGuard } from '@/components/System/PermissionGuard';
import { RouteConfig } from '@/constants/routes';

interface ProtectedRouteProps extends Omit<RouteConfig, 'children'> {
  component: React.ComponentType<Record<string, unknown>>;
  errorBoundary?: boolean;
  fallback?: React.ReactNode;
  exact?: boolean;
}

/**
 * 高阶受保护路由组件
 * 统一处理权限验证、错误边界和加载状态
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  component: Component,
  permissions,
  errorBoundary = true,
  fallback,
  ...routeProps
}) => {
  const renderElement = () => {
    // 如果没有权限要求，直接渲染组件
    if (permissions == null || permissions.length === 0) {
      return <Component />;
    }

    // 有权限要求，使用权限守卫包装
    return (
      <PermissionGuard permissions={permissions} fallback={fallback} mode="any">
        <Component />
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

export default ProtectedRoute;
