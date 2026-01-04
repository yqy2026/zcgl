import React, { Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Spin, App as AntdApp } from 'antd'
import { protectedRoutes } from './routes/AppRoutes'
import AppLayout from './components/Layout/AppLayout'
import LoginPage from './pages/LoginPage'
import ErrorBoundary from './components/ErrorHandling/ErrorBoundary'
import { AuthService } from './services/authService'
import { AuthProvider } from './contexts/AuthContext'
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

const ProtectedRoutes: React.FC = () => {
  const isAuthenticated = AuthService.isAuthenticated()
  const location = useLocation()

  // 未认证用户重定向到登录页面
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // 已认证用户,渲染带布局的应用路由
  return (
    <AppLayout>
      <Routes>
        {protectedRoutes.map((route, index) => (
          <Route
            key={index}
            path={route.path}
            element={
              <Suspense fallback={<Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: '100px' }} />}>
                <route.element />
              </Suspense>
            }
          />
        ))}
        {/* 默认路由重定向到仪表板 */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppLayout>
  )
}

/**
 * 应用路由配置 - 根据认证状态分发路由
 */
const AppContent: React.FC = () => {
  const isAuthenticated = AuthService.isAuthenticated()
  const location = useLocation()

  return (
    <Routes>
      {/* 公共路由 - 登录页面 */}
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            // 已登录用户访问登录页面,重定向到之前访问的页面或仪表板
            <Navigate to={(((location.state as LocationState)?.from?.pathname !== null && (location.state as LocationState)?.from?.pathname !== undefined && (location.state as LocationState)?.from?.pathname !== '') ? (location.state as LocationState)?.from?.pathname : '/dashboard') as string} replace />

          ) : (
            // 未登录用户显示登录页面
            <LoginPage />
          )
        }
      />

      {/* 受保护的路由 - 需要认证 */}
      <Route path="/*" element={<ProtectedRoutes />} />
    </Routes>
  )
}

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AntdApp>
          <BrowserRouter
            future={{
              v7_startTransition: true,
              v7_relativeSplatPath: true,
            }}
          >
            <AppContent />
          </BrowserRouter>
        </AntdApp>
      </AuthProvider>
    </ErrorBoundary>
  )
}


export default App
