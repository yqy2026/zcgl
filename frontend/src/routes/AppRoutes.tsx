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
const TestAnalyticsPage = React.lazy(() => import('../TestAnalyticsPage'))
const UXDemoPage = React.lazy(() => import('../pages/UXDemoPage'))
const TestApp = React.lazy(() => import('../TestApp'))
const ApiTest = React.lazy(() => import('../pages/Test/ApiTest'))
const AssetDebug = React.lazy(() => import('../pages/Debug/AssetDebug'))
const DataMappingTest = React.lazy(() => import('../pages/Test/DataMappingTest'))
const ImportTest = React.lazy(() => import('../pages/Test/ImportTest'))
const SimpleAssetTest = React.lazy(() => import('../pages/Test/SimpleAssetTest'))
const DictionaryTestPage = React.lazy(() => import('../pages/Test/DictionaryTestPage'))
const DebugImportTest = React.lazy(() => import('../pages/Test/DebugImportTest'))
const AsyncImportTestPage = React.lazy(() => import('../pages/Test/AsyncImportTestPage'))
const OwnershipSelectTest = React.lazy(() => import('../pages/Test/OwnershipSelectTest'))
const TemplateTestPage = React.lazy(() => import('../pages/Test/TemplateTestPage'))
const DictionaryPage = React.lazy(() => import('../pages/System/DictionaryPage'))
const OrganizationPage = React.lazy(() => import('../pages/System/OrganizationPage'))
const TemplateManagementPage = React.lazy(() => import('../pages/System/TemplateManagementPage'))
const OwnershipManagementPage = React.lazy(() => import('../pages/Ownership/OwnershipManagementPage'))
const ProjectManagementPage = React.lazy(() => import('../pages/Project/ProjectManagementPage'))
const ContractListPage = React.lazy(() => import('../pages/Rental/ContractListPage'))
const ContractCreatePage = React.lazy(() => import('../pages/Rental/ContractCreatePage'))
const RentLedgerPage = React.lazy(() => import('../pages/Rental/RentLedgerPage'))
const RentStatisticsPage = React.lazy(() => import('../pages/Rental/RentStatisticsPage'))

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
          <Route path="/test-analytics" element={<TestAnalyticsPage />} />
          <Route path="/assets/:id" element={<AssetDetailPage />} />
          <Route path="/assets/:id/edit" element={<AssetCreatePage />} />
          
          {/* 租赁管理 */}
          <Route path="/rental" element={<Navigate to="/rental/contracts" replace />} />
          <Route path="/rental/contracts" element={<ContractListPage />} />
          <Route path="/rental/contracts/new" element={<ContractCreatePage />} />
          <Route path="/rental/ledger" element={<RentLedgerPage />} />
          <Route path="/rental/statistics" element={<RentStatisticsPage />} />

          {/* 权属方管理 */}
          <Route path="/ownership" element={<OwnershipManagementPage />} />

          {/* 项目管理 */}
          <Route path="/project" element={<ProjectManagementPage />} />

          {/* 系统管理 */}
          <Route path="/system/dictionaries" element={<DictionaryPage />} />
          <Route path="/system/organizations" element={<OrganizationPage />} />
          <Route path="/system/templates" element={<TemplateManagementPage />} />
          {/* 兼容旧的枚举字段路由，重定向到字典管理 */}
          <Route path="/system/enum-fields" element={<Navigate to="/system/dictionaries" replace />} />

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
          <Route path="/test/api" element={<ApiTest />} />
          <Route path="/test/mapping" element={<DataMappingTest />} />
          <Route path="/test/import" element={<ImportTest />} />
          <Route path="/test/simple" element={<SimpleAssetTest />} />
          <Route path="/test/debug-import" element={<DebugImportTest />} />
          <Route path="/test/async-import" element={<AsyncImportTestPage />} />
          <Route path="/test/dictionary" element={<DictionaryTestPage />} />
          <Route path="/test/ownership-select" element={<OwnershipSelectTest />} />
          <Route path="/test/template" element={<TemplateTestPage />} />
          <Route path="/debug/assets" element={<AssetDebug />} />
          
          {/* 404页面 */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  )
}

export default AppRoutes