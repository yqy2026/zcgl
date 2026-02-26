import React, { Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Spin, App as AntdApp } from 'antd';
import { protectedRoutes, type ProtectedRouteItem } from './routes/AppRoutes';
import AppLayout from './components/Layout/AppLayout';
import LoginPage from './pages/LoginPage';
import ErrorBoundary from './components/ErrorHandling/ErrorBoundary';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ErrorHandlingProvider } from './contexts/ErrorHandlingContext';
import { PermissionGuard } from './components/System/PermissionGuard';
import { MessageManager } from './utils/messageManager';
import { ThemeProvider } from './components/Common/ThemeProvider';
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

const ProtectedRoutes: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();
  const capabilityGuardEnabled = import.meta.env.VITE_ENABLE_CAPABILITY_GUARD === 'true';

  const renderProtectedElement = (route: ProtectedRouteItem): React.ReactNode => {
    const RouteComponent = route.element;
    const routeElement = (
      <PageTransition>
        <Suspense fallback={<Spin size="large" className={styles.suspenseFallbackSpin} />}>
          <RouteComponent />
        </Suspense>
      </PageTransition>
    );

    const bypassCapabilityGuard = route.capabilityGuardBypass === true;
    const hasRoutePermissions = (route.permissions?.length ?? 0) > 0;
    const shouldEnforceCapabilityGuard = capabilityGuardEnabled && bypassCapabilityGuard === false;
    const shouldEnforceAdminOnly = shouldEnforceCapabilityGuard && route.adminOnly === true;

    if (shouldEnforceAdminOnly && user?.is_admin !== true) {
      return route.fallback ?? <Navigate to="/dashboard" replace />;
    }

    if (shouldEnforceCapabilityGuard && hasRoutePermissions) {
      return (
        <PermissionGuard
          permissions={route.permissions ?? []}
          mode={route.permissionMode ?? 'any'}
          fallback={route.fallback}
        >
          {routeElement}
        </PermissionGuard>
      );
    }

    if (shouldEnforceCapabilityGuard && route.adminOnly !== true) {
      return route.fallback ?? <Navigate to="/dashboard" replace />;
    }

    return routeElement;
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
