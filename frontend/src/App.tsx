import React, { Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { ConfigProvider, Spin } from 'antd'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { routes } from './routes/AppRoutes'
import AppLayout from './components/Layout/AppLayout'
import LoginPage from './pages/LoginPage'
import { AuthService } from './services/authService'
import { AuthProvider } from './contexts/AuthContext'
import './App.css'

// 创建查询客户端
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
})

// 简单的应用组件，内部处理路由逻辑
const AppContent: React.FC = () => {
  // 使用AuthService检查认证状态
  const isAuthenticated = AuthService.isAuthenticated()
  const location = useLocation()

  // 如果未登录，显示登录页面
  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  // 如果已登录但在登录页面，重定向到仪表板
  if (location.pathname === '/login') {
    return <Navigate to="/dashboard" replace />
  }

  // 如果已登录，显示主应用布局和路由
  return (
    <AppLayout>
      <Routes>
        {routes.map((route, index) => (
          <Route key={index} path={route.path} element={
            <Suspense fallback={<Spin size="large" />}>
              <route.element />
            </Suspense>
          } />
        ))}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppLayout>
  )
}

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ConfigProvider
          theme={{
            token: {
              colorPrimary: '#1890ff',
              colorSuccess: '#52c41a',
              colorWarning: '#faad14',
              colorError: '#f5222d',
              borderRadius: 8,
            },
          }}
        >
          <BrowserRouter>
            <AppContent />
          </BrowserRouter>
        </ConfigProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App