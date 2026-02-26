import React from 'react';
import { Navigate } from 'react-router-dom';
import {
  ASSET_ROUTES,
  RENTAL_ROUTES,
  OWNERSHIP_ROUTES,
  PROJECT_ROUTES,
  PROFILE_ROUTES,
  SYSTEM_ROUTES,
  BASE_PATHS,
  PROPERTY_CERTIFICATE_ROUTES,
  ROUTE_CONFIG,
  type RouteConfig,
} from '@/constants/routes';

export interface ProtectedRouteItem {
  path: string;
  element: React.ComponentType;
  permissions?: Array<{ action: string; resource: string }>;
  permissionMode?: 'any' | 'all';
  adminOnly?: boolean;
  capabilityGuardBypass?: boolean;
  fallback?: React.ReactNode;
}

type RoutePermission = { action: string; resource: string };

const collectPermissionsByPath = (routes: RouteConfig[]): Map<string, RoutePermission[]> => {
  const permissionsByPath = new Map<string, RoutePermission[]>();

  const walk = (items: RouteConfig[]): void => {
    for (const route of items) {
      if (route.permissions != null && route.permissions.length > 0) {
        permissionsByPath.set(
          route.path,
          route.permissions.map(permission => ({
            action: permission.action,
            resource: permission.resource,
          }))
        );
      }

      if (route.children != null && route.children.length > 0) {
        walk(route.children);
      }
    }
  };

  walk(routes);
  return permissionsByPath;
};

const ROUTE_PERMISSIONS_BY_PATH = collectPermissionsByPath(ROUTE_CONFIG);

const withDerivedAuthzMetadata = (routes: ProtectedRouteItem[]): ProtectedRouteItem[] => {
  return routes.map(route => {
    if (route.permissions != null || route.adminOnly === true) {
      return route;
    }

    const derivedPermissions = ROUTE_PERMISSIONS_BY_PATH.get(route.path);
    if (derivedPermissions == null || derivedPermissions.length === 0) {
      return route;
    }

    return {
      ...route,
      permissions: derivedPermissions,
    };
  });
};

/**
 * 受保护的路由配置
 * 这些路由需要用户认证后才能访问,并会被 AppLayout 包装
 * 注意: 登录页面路由不应该在此定义,应该在 App.tsx 中作为公共路由处理
 */
const baseProtectedRoutes: ProtectedRouteItem[] = [
  // 仪表板 - 首页
  {
    path: BASE_PATHS.DASHBOARD,
    element: React.lazy(() => import('../pages/Dashboard/DashboardPage')),
    capabilityGuardBypass: true,
  },
  {
    path: BASE_PATHS.ASSETS,
    element: () => <Navigate to={ASSET_ROUTES.LIST} replace />,
    capabilityGuardBypass: true,
  },

  // 资产管理模块 - 注意路由顺序，更具体的路径要在前面
  {
    path: ASSET_ROUTES.NEW,
    element: React.lazy(() => import('../pages/Assets/AssetCreatePage')),
  },
  {
    path: ASSET_ROUTES.IMPORT,
    element: React.lazy(() => import('../pages/Assets/AssetImportPage')),
  },
  {
    path: ASSET_ROUTES.ANALYTICS,
    element: React.lazy(() => import('../pages/Assets/AssetAnalyticsPage')),
  },
  {
    path: ASSET_ROUTES.ANALYTICS_SIMPLE,
    element: React.lazy(() => import('../pages/Assets/SimpleAnalyticsPage')),
  },
  {
    path: ASSET_ROUTES.LIST,
    element: React.lazy(() => import('../pages/Assets/AssetListPage')),
  },
  {
    path: ASSET_ROUTES.DETAIL_PATH,
    element: React.lazy(() => import('../pages/Assets/AssetDetailPage')),
  },

  // 租赁管理模块 - 注意路由顺序，具体路径必须在动态路径之前
  {
    path: RENTAL_ROUTES.CONTRACTS.LIST,
    element: React.lazy(() => import('../pages/Rental/ContractListPage')),
  },
  {
    path: RENTAL_ROUTES.CONTRACTS.NEW, // 具体路由 - 创建合同
    element: React.lazy(() => import('../pages/Rental/ContractCreatePage')),
  },
  {
    path: RENTAL_ROUTES.CONTRACTS.CREATE, // 具体路由 - 创建合同（备用）
    element: React.lazy(() => import('../pages/Rental/ContractCreatePage')),
  },
  {
    path: RENTAL_ROUTES.CONTRACTS.PDF_IMPORT, // 具体路由 - PDF导入
    element: React.lazy(() => import('../pages/Contract/PDFImportPage')),
  },
  {
    path: RENTAL_ROUTES.CONTRACTS.RENEW_PATH, // 具体路由 - 续签合同（必须在 :id/edit 之前）
    element: React.lazy(() => import('../pages/Rental/ContractRenewPage')),
  },
  {
    path: RENTAL_ROUTES.CONTRACTS.DETAIL_PATH, // 动态路由 - 合同详情页
    element: React.lazy(() => import('../pages/Rental/ContractDetailPage')),
  },
  {
    path: RENTAL_ROUTES.CONTRACTS.EDIT_PATH, // 动态路由 - 编辑合同
    element: React.lazy(() => import('../pages/Rental/ContractCreatePage')),
  },
  {
    path: RENTAL_ROUTES.LEDGER,
    element: React.lazy(() => import('../pages/Rental/RentLedgerPage')),
  },
  {
    path: RENTAL_ROUTES.STATISTICS,
    element: React.lazy(() => import('../pages/Rental/RentStatisticsPage')),
  },

  {
    path: PROPERTY_CERTIFICATE_ROUTES.LIST,
    element: React.lazy(() => import('../pages/PropertyCertificate/PropertyCertificateList')),
  },
  {
    path: PROPERTY_CERTIFICATE_ROUTES.IMPORT,
    element: React.lazy(() => import('../pages/PropertyCertificate/PropertyCertificateImport')),
  },
  {
    path: PROPERTY_CERTIFICATE_ROUTES.DETAIL_PATH,
    element: React.lazy(() => import('../pages/PropertyCertificate/PropertyCertificateDetailPage')),
  },

  // 权属方管理 - 注意路由顺序，详情页必须在列表页之前
  {
    path: OWNERSHIP_ROUTES.EDIT_PATH,
    element: React.lazy(() => import('../pages/Ownership/OwnershipManagementPage')),
  },
  {
    path: OWNERSHIP_ROUTES.DETAIL_PATH,
    element: React.lazy(() => import('../pages/Ownership/OwnershipDetailPage')),
  },
  {
    path: OWNERSHIP_ROUTES.LIST,
    element: React.lazy(() => import('../pages/Ownership/OwnershipManagementPage')),
  },

  // 项目管理 - 注意路由顺序，详情页必须在列表页之前
  {
    path: PROJECT_ROUTES.EDIT_PATH,
    element: React.lazy(() => import('../pages/Project/ProjectManagementPage')),
  },
  {
    path: PROJECT_ROUTES.DETAIL_PATH,
    element: React.lazy(() => import('../pages/Project/ProjectDetailPage')),
  },
  {
    path: PROJECT_ROUTES.LIST,
    element: React.lazy(() => import('../pages/Project/ProjectManagementPage')),
  },

  // 个人中心
  {
    path: PROFILE_ROUTES.PROFILE,
    element: React.lazy(() => import('../pages/ProfilePage')),
    capabilityGuardBypass: true,
  },

  // 系统管理
  {
    path: SYSTEM_ROUTES.USERS,
    element: React.lazy(() => import('../pages/System/UserManagementPage')),
  },
  {
    path: SYSTEM_ROUTES.ROLES,
    element: React.lazy(() => import('../pages/System/RoleManagementPage')),
  },
  {
    path: SYSTEM_ROUTES.ORGANIZATIONS,
    element: React.lazy(() => import('../pages/System/OrganizationPage')),
  },
  {
    path: SYSTEM_ROUTES.DICTIONARIES,
    element: React.lazy(() => import('../pages/System/DictionaryPage')),
  },
  {
    path: SYSTEM_ROUTES.LOGS,
    element: React.lazy(() => import('../pages/System/OperationLogPage')),
  },
  {
    path: SYSTEM_ROUTES.TEMPLATES,
    element: React.lazy(() => import('../pages/System/TemplateManagementPage')),
  },
  {
    path: SYSTEM_ROUTES.SETTINGS,
    element: React.lazy(() => import('../pages/System/SystemSettingsPage')),
  },
];

export const protectedRoutes: ProtectedRouteItem[] = withDerivedAuthzMetadata(baseProtectedRoutes);
