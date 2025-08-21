import React, { Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import ErrorBoundary from '../components/ErrorHandling/ErrorBoundary'

// 懒加载页面组件
const DashboardPage = React.lazy(() => import('../pages/Dashboard/DashboardPage'))
const AssetListPage = React.lazy(() => import('../pages/Assets/AssetListPage'))
const AssetDetailPage = React.lazy(() => import('../pages/Assets/AssetDetailPage'))
const AssetCreatePage = React.lazy(() => import('../pages/Assets/AssetCreatePage'))
const AssetImportPage = React.lazy(() => import('../pages/Assets/AssetImportPage'))
const AssetAnalyticsPage = React.lazy(() => import('../pages/Assets/AssetAnalyticsPage'))
const UXDemoPage = React.lazy(() => import('../pages/UXDemoPage'))
const TestApp = React.lazy(() => import('../TestApp'))

// 加载组件
const LoadingSpinner: React.FC = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    height: '200px' 
  }}>
    <Spin size="large" tip="加载中..." />
  </div>
)

const AppRoutes: React.FC = () => {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          {/* 默认重定向到工作台 */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          
          {/* 工作台 */}
          <Route path="/dashboard" element={<DashboardPage />} />
          
          {/* 资产管理 */}
          <Route path="/assets" element={<Navigate to="/assets/list" replace />} />
          <Route path="/assets/list" element={<AssetListPage />} />
          <Route path="/assets/new" element={<AssetCreatePage />} />
          <Route path="/assets/import" element={<AssetImportPage />} />
          <Route path="/assets/analytics" element={<AssetAnalyticsPage />} />
          <Route path="/assets/:id" element={<AssetDetailPage />} />
          <Route path="/assets/:id/edit" element={<AssetCreatePage />} />
          
          {/* 租赁管理 - 暂时重定向到工作台 */}
          <Route path="/rental/*" element={<Navigate to="/dashboard" replace />} />
          
          {/* 财务管理 - 暂时重定向到工作台 */}
          <Route path="/finance/*" element={<Navigate to="/dashboard" replace />} />
          
          {/* 文档中心 - 暂时重定向到工作台 */}
          <Route path="/documents/*" element={<Navigate to="/dashboard" replace />} />
          
          {/* 系统设置 - 暂时重定向到工作台 */}
          <Route path="/settings/*" element={<Navigate to="/dashboard" replace />} />
          
          {/* UX演示页面 */}
          <Route path="/ux-demo" element={<UXDemoPage />} />
          
          {/* 测试页面 */}
          <Route path="/test" element={<TestApp />} />
          
          {/* 404页面 */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  )
}

export default AppRoutes