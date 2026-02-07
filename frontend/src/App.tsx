import React, { Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Spin, App as AntdApp } from 'antd';
import { protectedRoutes } from './routes/AppRoutes';
import AppLayout from './components/Layout/AppLayout';
import LoginPage from './pages/LoginPage';
import ErrorBoundary from './components/ErrorHandling/ErrorBoundary';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ErrorHandlingProvider } from './contexts/ErrorHandlingContext';
import { MessageManager } from './utils/messageManager';
import { ThemeProvider } from './components/Common/ThemeProvider';
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
  const { isAuthenticated } = useAuth();
  const location = useLocation();

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
            <Route
              key={route.path}
              path={route.path}
              element={
                <PageTransition>
                  <Suspense
                    fallback={
                      <Spin
                        size="large"
                        style={{ display: 'flex', justifyContent: 'center', marginTop: '100px' }}
                      />
                    }
                  >
                    <route.element />
                  </Suspense>
                </PageTransition>
              }
            />
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
  const { isAuthenticated } = useAuth();
  const location = useLocation();

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
