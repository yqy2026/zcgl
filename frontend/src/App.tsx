import React, { Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Button, Result, Spin, App as AntdApp } from 'antd';
import { protectedRoutes, type ProtectedRouteItem } from './routes/AppRoutes';
import AppLayout from './components/Layout/AppLayout';
import LoginPage from './pages/LoginPage';
import ErrorBoundary from './components/ErrorHandling/ErrorBoundary';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ErrorHandlingProvider } from './contexts/ErrorHandlingContext';
import { CapabilityGuard } from './components/System/CapabilityGuard';
import { MessageManager } from './utils/messageManager';
import { ThemeProvider } from './components/Common/ThemeProvider';
import { useCapabilities } from './hooks/useCapabilities';
import styles from './App.module.css';
// App.css removed - classes were unused default React template styles

/**
 * 路由状态接口
 */
interface LocationState {
  from?: {
    pathname: string;
  };
}

/**
 * 受保护的路由组件 - 需要认证才能访问
 */

import { AnimatePresence } from 'framer-motion';
import PageTransition from './components/Layout/PageTransition';

const InlineForbidden: React.FC = () => {
  return (
    <Result
      status="403"
      title="访问被拒绝"
      subTitle="当前账号无权访问该页面。"
      extra={
        <Button type="primary" onClick={() => void window.history.back()}>
          返回上一页
        </Button>
      }
    />
  );
};

const ProtectedRoutes: React.FC = () => {
  const { isAuthenticated, isAdmin, loading: authLoading } = useAuth();
  const { canPerform, loading: capabilitiesLoading } = useCapabilities();
  const location = useLocation();
  const capabilityGuardEnabled = import.meta.env.VITE_ENABLE_CAPABILITY_GUARD === 'true';

  const renderRouteElement = (route: ProtectedRouteItem): React.ReactNode => {
    const RouteComponent = route.element;
    return (
      <PageTransition>
        <Suspense fallback={<Spin size="large" className={styles.suspenseFallbackSpin} />}>
          <RouteComponent />
        </Suspense>
      </PageTransition>
    );
  };

  const renderProtectedElement = (route: ProtectedRouteItem): React.ReactNode => {
    if (authLoading || capabilitiesLoading) {
      return <Spin size="large" className={styles.suspenseFallbackSpin} />;
    }

    const bypassCapabilityGuard = route.capabilityGuardBypass === true;
    const hasRoutePermissions = (route.permissions?.length ?? 0) > 0;
    const shouldEnforceCapabilityGuard = capabilityGuardEnabled && bypassCapabilityGuard === false;
    const hasMixedGuardConfig = route.adminOnly === true && hasRoutePermissions;

    if (hasMixedGuardConfig) {
      // D10: adminOnly 与 permissions 互斥，运行时保守按 adminOnly 处理。
      console.error(
        '[authz] route config invalid: adminOnly and permissions are mutually exclusive',
        route.path
      );
    }

    if (route.adminOnly === true) {
      return isAdmin ? renderRouteElement(route) : (route.fallback ?? <InlineForbidden />);
    }

    if (!shouldEnforceCapabilityGuard) {
      return renderRouteElement(route);
    }

    if (!hasRoutePermissions) {
      return renderRouteElement(route);
    }

    const permissions = route.permissions ?? [];
    if (permissions.length === 1 && (route.permissionMode ?? 'any') === 'any') {
      const [permission] = permissions;
      return (
        <CapabilityGuard
          action={permission.action}
          resource={permission.resource}
          fallback={route.fallback}
        >
          {renderRouteElement(route)}
        </CapabilityGuard>
      );
    }

    const mode = route.permissionMode ?? 'any';
    const canAccess =
      mode === 'all'
        ? permissions.every(permission => canPerform(permission.action, permission.resource))
        : permissions.some(permission => canPerform(permission.action, permission.resource));

    return canAccess ? renderRouteElement(route) : (route.fallback ?? <InlineForbidden />);
  };

  // 未认证用户重定向到登录页面
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 已认证用户,渲染带布局的应用路由
  return (
    <AppLayout>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          {protectedRoutes.map(route => (
            <Route key={route.path} path={route.path} element={renderProtectedElement(route)} />
          ))}
          {/* 默认路由重定向到仪表板 */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AnimatePresence>
    </AppLayout>
  );
};

/**
 * 应用路由配置 - 根据认证状态分发路由
 */
const AppContent: React.FC = () => {
  const { isAuthenticated, initializing } = useAuth();
  const location = useLocation();

  if (initializing === true) {
    return (
      <div className={styles.authBootstrap}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <Routes>
      {/* 公共路由 - 登录页面 */}
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            // 已登录用户访问登录页面,重定向到之前访问的页面或仪表板
            <Navigate
              to={(location.state as LocationState)?.from?.pathname ?? '/dashboard'}
              replace
            />
          ) : (
            // 未登录用户显示登录页面
            <LoginPage />
          )
        }
      />

      {/* 受保护的路由 - 需要认证 */}
      <Route path="/*" element={<ProtectedRoutes />} />
    </Routes>
  );
};

/**
 * App初始化组件 - 用于初始化MessageManager
 */
const AppInitializer: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { message } = AntdApp.useApp();

  useEffect(() => {
    // 初始化全局消息管理器
    MessageManager.init(message);
  }, [message]);

  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <ErrorHandlingProvider>
          <AuthProvider>
            <AntdApp>
              <AppInitializer>
                <BrowserRouter
                  future={{
                    v7_startTransition: true,
                    v7_relativeSplatPath: true,
                  }}
                >
                  <AppContent />
                </BrowserRouter>
              </AppInitializer>
            </AntdApp>
          </AuthProvider>
        </ErrorHandlingProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;
