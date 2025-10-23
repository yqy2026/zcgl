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
const DictionaryPage = React.lazy(() => import('../pages/System/DictionaryPage'))
const OrganizationPage = React.lazy(() => import('../pages/System/OrganizationPage'))
const TemplateManagementPage = React.lazy(() => import('../pages/System/TemplateManagementPage'))
const UserManagementPage = React.lazy(() => import('../pages/System/UserManagementPage'))
const RoleManagementPage = React.lazy(() => import('../pages/System/RoleManagementPage'))
const OperationLogPage = React.lazy(() => import('../pages/System/OperationLogPage'))
const SystemSettingsPage = React.lazy(() => import('../pages/System/SystemSettingsPage'))
const OwnershipManagementPage = React.lazy(() => import('../pages/Ownership/OwnershipManagementPage'))
const ProjectManagementPage = React.lazy(() => import('../pages/Project/ProjectManagementPage'))
const ContractListPage = React.lazy(() => import('../pages/Rental/ContractListPage'))
const ContractCreatePage = React.lazy(() => import('../pages/Rental/ContractCreatePage'))
const RentLedgerPage = React.lazy(() => import('../pages/Rental/RentLedgerPage'))
const RentStatisticsPage = React.lazy(() => import('../pages/Rental/RentStatisticsPage'))
const PDFImportPage = React.lazy(() => import('../pages/Contract/PDFImportPage'))
import SystemErrorBoundary from '../components/System/SystemErrorBoundary'
import {
  UserManagementGuard,
  RoleManagementGuard,
  SystemLogsGuard,
  AssetManagementGuard
} from '../components/System/PermissionGuard'

// 加载组件
const LoadingSpinner: React.FC = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '200px'
  }}>
    <Spin size="large" />
    <div style={{ marginTop: '16' }}>加载中...</div>
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
          <Route path="/assets/create" element={<AssetCreatePage />} />
          <Route path="/assets/import" element={<AssetImportPage />} />
          <Route path="/assets/analytics" element={<AssetAnalyticsPage />} />
          <Route path="/assets/:id" element={<AssetDetailPage />} />
          <Route path="/assets/:id/edit" element={<AssetCreatePage />} />

          {/* 租赁管理 */}
          <Route path="/rental" element={<Navigate to="/rental/contracts" replace />} />
          <Route path="/rental/contracts" element={<ContractListPage />} />
          <Route path="/rental/contracts/new" element={<ContractCreatePage />} />
          <Route path="/rental/contracts/pdf-import" element={<PDFImportPage />} />
          <Route path="/rental/ledger" element={<RentLedgerPage />} />
          <Route path="/rental/statistics" element={<RentStatisticsPage />} />

          {/* 兼容旧路径重定向 */}
          <Route path="/rental/rent-ledger" element={<RentLedgerPage />} />

          {/* 权属方管理 */}
          <Route path="/ownership" element={<OwnershipManagementPage />} />

          {/* 项目管理 */}
          <Route path="/project" element={<ProjectManagementPage />} />

          {/* 系统管理 */}
          <Route path="/system/users" element={
            <SystemErrorBoundary>
              <UserManagementGuard>
                <UserManagementPage />
              </UserManagementGuard>
            </SystemErrorBoundary>
          } />
          <Route path="/system/roles" element={
            <SystemErrorBoundary>
              <RoleManagementGuard>
                <RoleManagementPage />
              </RoleManagementGuard>
            </SystemErrorBoundary>
          } />
          <Route path="/system/organizations" element={
            <SystemErrorBoundary>
              <OrganizationPage />
            </SystemErrorBoundary>
          } />
          <Route path="/system/dictionaries" element={
            <SystemErrorBoundary>
              <DictionaryPage />
            </SystemErrorBoundary>
          } />
          <Route path="/system/templates" element={
            <SystemErrorBoundary>
              <TemplateManagementPage />
            </SystemErrorBoundary>
          } />
          <Route path="/system/logs" element={
            <SystemErrorBoundary>
              <SystemLogsGuard>
                <OperationLogPage />
              </SystemLogsGuard>
            </SystemErrorBoundary>
          } />
          <Route path="/system/settings" element={
            <SystemErrorBoundary>
              <SystemSettingsPage />
            </SystemErrorBoundary>
          } />
          {/* 兼容旧的枚举字段路由，重定向到字典管理 */}
          <Route path="/system/enum-fields" element={<Navigate to="/system/dictionaries" replace />} />

          {/* 财务管理 - 暂时重定向到工作台 */}
          <Route path="/finance/*" element={<Navigate to="/dashboard" replace />} />

          {/* 文档中心 - 暂时重定向到工作台 */}
          <Route path="/documents/*" element={<Navigate to="/dashboard" replace />} />

          {/* 系统设置 - 暂时重定向到工作台 */}
          <Route path="/settings/*" element={<Navigate to="/dashboard" replace />} />

          {/* 404页面 */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  )
}

export default AppRoutes