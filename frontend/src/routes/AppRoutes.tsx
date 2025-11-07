import React from 'react'

/**
 * 受保护的路由配置
 * 这些路由需要用户认证后才能访问,并会被 AppLayout 包装
 * 注意: 登录页面路由不应该在此定义,应该在 App.tsx 中作为公共路由处理
 */
export const protectedRoutes = [
  // 仪表板 - 首页
  {
    path: '/dashboard',
    element: React.lazy(() => import('../pages/Dashboard/DashboardPage'))
  },

  // 资产管理模块
  {
    path: '/assets/list',
    element: React.lazy(() => import('../pages/Assets/AssetListPage'))
  },
  {
    path: '/assets/new',
    element: React.lazy(() => import('../pages/Assets/AssetCreatePage'))
  },
  {
    path: '/assets/import',
    element: React.lazy(() => import('../pages/Assets/AssetImportPage'))
  },
  {
    path: '/assets/analytics',
    element: React.lazy(() => import('../pages/Assets/AssetAnalyticsPage'))
  },
  {
    path: '/assets/:id',
    element: React.lazy(() => import('../pages/Assets/AssetDetailPage'))
  },

  // 租赁管理模块
  {
    path: '/rental/contracts',
    element: React.lazy(() => import('../pages/Rental/ContractListPage'))
  },
  {
    path: '/rental/contracts/new',
    element: React.lazy(() => import('../pages/Rental/ContractCreatePage'))
  },
  {
    path: '/rental/contracts/pdf-import',
    element: React.lazy(() => import('../pages/Contract/PDFImportPage'))
  },
  {
    path: '/rental/ledger',
    element: React.lazy(() => import('../pages/Rental/RentLedgerPage'))
  },
  {
    path: '/rental/statistics',
    element: React.lazy(() => import('../pages/Rental/RentStatisticsPage'))
  },

  // 权属方管理
  {
    path: '/ownership',
    element: React.lazy(() => import('../pages/Ownership/OwnershipManagementPage'))
  },

  // 项目管理
  {
    path: '/project',
    element: React.lazy(() => import('../pages/Project/ProjectManagementPage'))
  },

  // 个人中心
  {
    path: '/profile',
    element: React.lazy(() => import('../pages/Profile/ProfilePage'))
  },

  // 系统管理
  {
    path: '/system/users',
    element: React.lazy(() => import('../pages/System/UserManagementPage'))
  },
  {
    path: '/system/roles',
    element: React.lazy(() => import('../pages/System/RoleManagementPage'))
  },
  {
    path: '/system/organizations',
    element: React.lazy(() => import('../pages/System/OrganizationPage'))
  },
  {
    path: '/system/dictionaries',
    element: React.lazy(() => import('../pages/System/DictionaryPage'))
  },
  {
    path: '/system/logs',
    element: React.lazy(() => import('../pages/System/OperationLogPage'))
  },
  {
    path: '/system/templates',
    element: React.lazy(() => import('../pages/System/TemplateManagementPage'))
  },
  {
    path: '/system/settings',
    element: React.lazy(() => import('../pages/System/SystemSettingsPage'))
  },
]