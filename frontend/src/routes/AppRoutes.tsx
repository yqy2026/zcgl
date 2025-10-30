import React from 'react'
import { Navigate } from 'react-router-dom'

// 路由定义 - 只包含已存在的页面文件
export const routes = [
  {
    path: '/login',
    element: React.lazy(() => import('../pages/LoginPage'))
  },
  {
    path: '/',
    element: React.lazy(() => import('../pages/LoginPage'))
  },
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
    path: '/system/settings',
    element: React.lazy(() => import('../pages/System/SystemSettingsPage'))
  },
]