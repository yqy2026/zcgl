import React, { Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import ErrorBoundary from '../components/ErrorHandling/ErrorBoundary'
import RouteBuilder from '../components/Router/RouteBuilder'
import { PERMISSIONS } from '../hooks/usePermission'
import { ROUTE_CONFIG, REDIRECTS, NOT_FOUND_REDIRECT } from '../constants/routes'

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

// 路由配置
const ROUTE_BUILDER_CONFIG = [
  // 根路径重定向
  {
    path: '/',
    element: <Navigate to={REDIRECTS.ROOT} replace />,
    title: '根重定向',
  },

  // 工作台
  {
    path: '/dashboard',
    component: DashboardPage,
    lazy: true,
    title: '工作台',
  },

  // 资产管理模块 - 嵌套路由
  {
    path: '/assets',
    title: '资产管理',
    children: [
      {
        path: '',
        element: <Navigate to="/assets/list" replace />,
      },
      {
        path: 'list',
        component: AssetListPage,
        lazy: true,
        permissions: [PERMISSIONS.ASSET_VIEW],
        title: '资产列表',
      },
      {
        path: 'new',
        component: AssetCreatePage,
        lazy: true,
        permissions: [PERMISSIONS.ASSET_CREATE],
        title: '创建资产',
      },
      {
        path: 'import',
        component: AssetImportPage,
        lazy: true,
        permissions: [PERMISSIONS.ASSET_IMPORT],
        title: '资产导入',
      },
      {
        path: 'analytics',
        component: AssetAnalyticsPage,
        lazy: true,
        permissions: [PERMISSIONS.ASSET_VIEW],
        title: '资产分析',
      },
      {
        path: ':id',
        component: AssetDetailPage,
        lazy: true,
        permissions: [PERMISSIONS.ASSET_VIEW],
        title: '资产详情',
      },
      {
        path: ':id/edit',
        component: AssetCreatePage,
        lazy: true,
        permissions: [PERMISSIONS.ASSET_EDIT],
        title: '编辑资产',
      },
    ],
  },

  // 租赁管理模块 - 嵌套路由
  {
    path: '/rental',
    title: '租赁管理',
    children: [
      {
        path: '',
        element: <Navigate to="/rental/contracts" replace />,
      },
      {
        path: 'contracts',
        children: [
          {
            path: '',
            component: ContractListPage,
            lazy: true,
            permissions: [PERMISSIONS.RENTAL_VIEW],
            title: '合同列表',
          },
          {
            path: 'new',
            component: ContractCreatePage,
            lazy: true,
            permissions: [PERMISSIONS.RENTAL_CREATE],
            title: '创建合同',
          },
          {
            path: 'pdf-import',
            component: PDFImportPage,
            lazy: true,
            permissions: [PERMISSIONS.RENTAL_CREATE],
            title: 'PDF导入合同',
          },
        ],
      },
      {
        path: 'ledger',
        component: RentLedgerPage,
        lazy: true,
        permissions: [PERMISSIONS.RENTAL_VIEW],
        title: '租金台账',
      },
      {
        path: 'statistics',
        component: RentStatisticsPage,
        lazy: true,
        permissions: [PERMISSIONS.RENTAL_VIEW],
        title: '租赁统计',
      },
    ],
  },

  // 权属方管理
  {
    path: '/ownership',
    component: OwnershipManagementPage,
    lazy: true,
    title: '权属方管理',
  },

  // 项目管理
  {
    path: '/project',
    component: ProjectManagementPage,
    lazy: true,
    title: '项目管理',
  },

  // 系统管理模块 - 嵌套路由
  {
    path: '/system',
    title: '系统管理',
    children: [
      {
        path: 'users',
        component: UserManagementPage,
        lazy: true,
        permissions: [PERMISSIONS.USER_VIEW],
        title: '用户管理',
      },
      {
        path: 'roles',
        component: RoleManagementPage,
        lazy: true,
        permissions: [PERMISSIONS.ROLE_VIEW],
        title: '角色管理',
      },
      {
        path: 'organizations',
        component: OrganizationPage,
        lazy: true,
        permissions: [PERMISSIONS.ORGANIZATION_VIEW],
        title: '组织架构',
      },
      {
        path: 'dictionaries',
        component: DictionaryPage,
        lazy: true,
        permissions: [PERMISSIONS.SYSTEM_DICTIONARY],
        title: '字典管理',
      },
      {
        path: 'templates',
        component: TemplateManagementPage,
        lazy: true,
        title: '模板管理',
      },
      {
        path: 'logs',
        component: OperationLogPage,
        lazy: true,
        permissions: [PERMISSIONS.SYSTEM_LOGS],
        title: '操作日志',
      },
      {
        path: 'settings',
        component: SystemSettingsPage,
        lazy: true,
        title: '系统设置',
      },
    ],
  },

  // 临时重定向路由
  {
    path: '/finance/*',
    element: <Navigate to="/dashboard" replace />,
    title: '财务模块重定向',
  },
  {
    path: '/documents/*',
    element: <Navigate to="/dashboard" replace />,
    title: '文档模块重定向',
  },
  {
    path: '/settings/*',
    element: <Navigate to="/dashboard" replace />,
    title: '设置模块重定向',
  },

  // 404页面
  {
    path: '*',
    element: <Navigate to={NOT_FOUND_REDIRECT} replace />,
    title: '404重定向',
  },
]

const AppRoutes: React.FC = () => {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          {RouteBuilder.buildRoutes(ROUTE_BUILDER_CONFIG)}
        </Routes>
      </Suspense>
    </ErrorBoundary>
  )
}

export default AppRoutes