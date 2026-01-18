import React from 'react';

/**
 * 受保护的路由配置
 * 这些路由需要用户认证后才能访问,并会被 AppLayout 包装
 * 注意: 登录页面路由不应该在此定义,应该在 App.tsx 中作为公共路由处理
 */
export const protectedRoutes = [
  // 仪表板 - 首页
  {
    path: '/dashboard',
    element: React.lazy(() => import('../pages/Dashboard/DashboardPage')),
  },

  // 资产管理模块 - 注意路由顺序，更具体的路径要在前面
  {
    path: '/assets/new',
    element: React.lazy(() => import('../pages/Assets/AssetCreatePage')),
  },
  {
    path: '/assets/import',
    element: React.lazy(() => import('../pages/Assets/AssetImportPage')),
  },
  {
    path: '/assets/analytics',
    element: React.lazy(() => import('../pages/Assets/AssetAnalyticsPage')),
  },
  {
    path: '/assets/analytics-simple',
    element: React.lazy(() => import('../pages/Assets/SimpleAnalyticsPage')),
  },
  {
    path: '/assets/list',
    element: React.lazy(() => import('../pages/Assets/AssetListPage')),
  },
  {
    path: '/assets/:id',
    element: React.lazy(() => import('../pages/Assets/AssetDetailPage')),
  },

  // 租赁管理模块 - 注意路由顺序，具体路径必须在动态路径之前
  {
    path: '/rental/contracts',
    element: React.lazy(() => import('../pages/Rental/ContractListPage')),
  },
  {
    path: '/rental/contracts/new', // 具体路由 - 创建合同
    element: React.lazy(() => import('../pages/Rental/ContractCreatePage')),
  },
  {
    path: '/rental/contracts/create', // 具体路由 - 创建合同（备用）
    element: React.lazy(() => import('../pages/Rental/ContractCreatePage')),
  },
  {
    path: '/rental/contracts/pdf-import', // 具体路由 - PDF导入
    element: React.lazy(() => import('../pages/Contract/PDFImportPage')),
  },
  {
    path: '/rental/contracts/:id/renew', // 具体路由 - 续签合同（必须在 :id/edit 之前）
    element: React.lazy(() => import('../pages/Rental/ContractRenewPage')),
  },
  {
    path: '/rental/contracts/:id', // 动态路由 - 合同详情页
    element: React.lazy(() => import('../pages/Rental/ContractDetailPage')),
  },
  {
    path: '/rental/contracts/:id/edit', // 动态路由 - 编辑合同
    element: React.lazy(() => import('../pages/Rental/ContractCreatePage')),
  },
  {
    path: '/rental/ledger',
    element: React.lazy(() => import('../pages/Rental/RentLedgerPage')),
  },
  {
    path: '/rental/statistics',
    element: React.lazy(() => import('../pages/Rental/RentStatisticsPage')),
  },

  // 权属方管理 - 注意路由顺序，详情页必须在列表页之前
  {
    path: '/ownership/:id/edit',
    element: React.lazy(() => import('../pages/Ownership/OwnershipManagementPage')),
  },
  {
    path: '/ownership/:id',
    element: React.lazy(() => import('../pages/Ownership/OwnershipDetailPage')),
  },
  {
    path: '/ownership',
    element: React.lazy(() => import('../pages/Ownership/OwnershipManagementPage')),
  },

  // 项目管理 - 注意路由顺序，详情页必须在列表页之前
  {
    path: '/project/:id/edit',
    element: React.lazy(() => import('../pages/Project/ProjectManagementPage')),
  },
  {
    path: '/project/:id',
    element: React.lazy(() => import('../pages/Project/ProjectDetailPage')),
  },
  {
    path: '/project',
    element: React.lazy(() => import('../pages/Project/ProjectManagementPage')),
  },

  // 个人中心
  {
    path: '/profile',
    element: React.lazy(() => import('../pages/Profile/ProfilePage')),
  },

  // 系统管理
  {
    path: '/system/users',
    element: React.lazy(() => import('../pages/System/UserManagementPage')),
  },
  {
    path: '/system/roles',
    element: React.lazy(() => import('../pages/System/RoleManagementPage')),
  },
  {
    path: '/system/organizations',
    element: React.lazy(() => import('../pages/System/OrganizationPage')),
  },
  {
    path: '/system/dictionaries',
    element: React.lazy(() => import('../pages/System/DictionaryPage')),
  },
  {
    path: '/system/logs',
    element: React.lazy(() => import('../pages/System/OperationLogPage')),
  },
  {
    path: '/system/templates',
    element: React.lazy(() => import('../pages/System/TemplateManagementPage')),
  },
  {
    path: '/system/settings',
    element: React.lazy(() => import('../pages/System/SystemSettingsPage')),
  },
];
