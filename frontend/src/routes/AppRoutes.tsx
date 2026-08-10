import React from 'react';
import type { AuthzAction, ResourceType } from '@/types/capability';
import CanonicalEntryRedirect from './CanonicalEntryRedirect';
import {
  ASSET_ROUTES,
  CONTRACT_CENTER_ROUTES,
  CONTRACT_GROUP_ROUTES,
  CUSTOMER_ROUTES,
  PROJECT_ROUTES,
  PROFILE_ROUTES,
  SEARCH_ROUTES,
  SYSTEM_ROUTES,
  BASE_PATHS,
  ANALYTICS_ROUTES,
  OPERATIONS_ROUTES,
  PROPERTY_CERTIFICATE_ROUTES,
} from '@/constants/routes';

export interface ProtectedRouteItem {
  path: string;
  element: React.ComponentType;
  permissions?: Array<{ action: AuthzAction; resource: ResourceType }>;
  permissionMode?: 'any' | 'all';
  adminOnly?: boolean;
  capabilityGuardBypass?: boolean;
  fallback?: React.ReactNode;
}

/**
 * 受保护的路由配置
 * 这些路由需要用户认证后才能访问,并会被 AppLayout 包装
 * 注意: 登录页面路由不应该在此定义,应该在 App.tsx 中作为公共路由处理
 */
const assetListPage = React.lazy(() => import('../pages/Assets/AssetListPage'));
const assetDetailPage = React.lazy(() => import('../pages/Assets/AssetDetailPage'));
const contractGroupListPage = React.lazy(
  () => import('../pages/ContractGroup/ContractGroupListPage')
);
const contractGroupDetailPage = React.lazy(
  () => import('../pages/ContractGroup/ContractGroupDetailPage')
);
const projectManagementPage = React.lazy(() => import('../pages/Project/ProjectManagementPage'));
const projectDetailPage = React.lazy(() => import('../pages/Project/ProjectDetailPage'));

const baseProtectedRoutes: ProtectedRouteItem[] = [
  // 仪表板 - 首页
  {
    path: BASE_PATHS.DASHBOARD,
    element: React.lazy(() => import('../pages/Dashboard/DashboardPage')),
    capabilityGuardBypass: true,
  },
  {
    path: BASE_PATHS.ASSETS,
    element: () => <CanonicalEntryRedirect targetPath={ASSET_ROUTES.LIST} resource="asset" />,
    permissions: [{ resource: 'asset', action: 'read' }],
  },

  // 资产资源模块 - 注意路由顺序，更具体的路径要在前面
  {
    path: ASSET_ROUTES.NEW,
    element: React.lazy(() => import('../pages/Assets/AssetCreatePage')),
    permissions: [{ resource: 'asset', action: 'create' }],
  },
  {
    path: ASSET_ROUTES.IMPORT,
    element: React.lazy(() => import('../pages/Assets/AssetImportPage')),
    permissions: [{ resource: 'asset', action: 'create' }],
  },
  {
    path: ANALYTICS_ROUTES.OVERVIEW,
    element: React.lazy(() => import('../pages/Assets/AssetAnalyticsPage')),
    permissions: [{ resource: 'analytics', action: 'read' }],
  },
  {
    path: OPERATIONS_ROUTES.LEDGER,
    element: React.lazy(() => import('../pages/OperationsLedger/OperationsLedgerPage')),
    permissions: [{ resource: 'contract', action: 'read' }],
  },
  {
    path: ASSET_ROUTES.ANALYTICS,
    element: React.lazy(() => import('../pages/Assets/AssetAnalyticsPage')),
    permissions: [{ resource: 'analytics', action: 'read' }],
  },
  {
    path: PROPERTY_CERTIFICATE_ROUTES.LIST,
    element: React.lazy(() => import('../pages/PropertyCertificate/PropertyCertificateList')),
    permissions: [{ resource: 'property_certificate', action: 'read' }],
  },
  {
    path: PROPERTY_CERTIFICATE_ROUTES.IMPORT,
    element: React.lazy(() => import('../pages/PropertyCertificate/PropertyCertificateImport')),
    permissions: [{ resource: 'property_certificate', action: 'create' }],
  },
  {
    path: PROPERTY_CERTIFICATE_ROUTES.DETAIL_PATH,
    element: React.lazy(() => import('../pages/PropertyCertificate/PropertyCertificateDetailPage')),
    permissions: [{ resource: 'property_certificate', action: 'read' }],
  },
  {
    path: ASSET_ROUTES.LIST,
    element: assetListPage,
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  // 更具体的路径要在 DETAIL_PATH 之前注册（编辑/历史）
  {
    path: ASSET_ROUTES.EDIT_PATH,
    element: React.lazy(() => import('../pages/Assets/AssetCreatePage')),
    permissions: [{ resource: 'asset', action: 'update' }],
  },
  {
    path: ASSET_ROUTES.HISTORY_PATH,
    element: React.lazy(() => import('../pages/Assets/AssetHistoryPage')),
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  {
    path: ASSET_ROUTES.DETAIL_PATH,
    element: assetDetailPage,
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  {
    path: CUSTOMER_ROUTES.DETAIL_PATH,
    element: React.lazy(() => import('../pages/Customer/CustomerDetailPage')),
    permissions: [{ resource: 'analytics', action: 'read' }],
  },
  {
    path: SEARCH_ROUTES.LIST,
    element: React.lazy(() => import('../pages/Search/GlobalSearchPage')),
    permissions: [{ resource: 'search', action: 'read' }],
  },

  {
    path: CONTRACT_CENTER_ROUTES.LIST,
    element: contractGroupListPage,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: '/contract-center/list',
    element: () => (
      <CanonicalEntryRedirect targetPath={CONTRACT_CENTER_ROUTES.LIST} resource="contract_group" />
    ),
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: CONTRACT_CENTER_ROUTES.NEW,
    element: React.lazy(() => import('../pages/ContractGroup/ContractGroupFormPage')),
    permissions: [{ resource: 'contract_group', action: 'create' }],
  },
  {
    path: CONTRACT_CENTER_ROUTES.IMPORT,
    element: React.lazy(() => import('../pages/Contract/PDFImportPage')),
    permissions: [{ resource: 'contract_group', action: 'create' }],
  },
  {
    path: CONTRACT_CENTER_ROUTES.DETAIL_PATH,
    element: contractGroupDetailPage,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: CONTRACT_CENTER_ROUTES.EDIT_PATH,
    element: React.lazy(() => import('../pages/ContractGroup/ContractGroupFormPage')),
    permissions: [{ resource: 'contract_group', action: 'update' }],
  },
  {
    path: CONTRACT_CENTER_ROUTES.NEW_CONTRACT_PATH,
    element: React.lazy(() => import('../pages/ContractGroup/ContractInGroupFormPage')),
    permissions: [{ resource: 'contract_group', action: 'create' }],
  },
  {
    path: CONTRACT_GROUP_ROUTES.LIST,
    element: contractGroupListPage,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: CONTRACT_GROUP_ROUTES.NEW,
    element: React.lazy(() => import('../pages/ContractGroup/ContractGroupFormPage')),
    permissions: [{ resource: 'contract_group', action: 'create' }],
  },
  {
    path: CONTRACT_GROUP_ROUTES.DETAIL_PATH,
    element: contractGroupDetailPage,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: CONTRACT_GROUP_ROUTES.EDIT_PATH,
    element: React.lazy(() => import('../pages/ContractGroup/ContractGroupFormPage')),
    permissions: [{ resource: 'contract_group', action: 'update' }],
  },
  {
    path: CONTRACT_GROUP_ROUTES.NEW_CONTRACT_PATH,
    element: React.lazy(() => import('../pages/ContractGroup/ContractInGroupFormPage')),
    permissions: [{ resource: 'contract_group', action: 'create' }],
  },
  // 项目运营 - 注意路由顺序，详情页必须在列表页之前
  {
    path: PROJECT_ROUTES.EDIT_PATH,
    element: projectManagementPage,
    permissions: [{ resource: 'project', action: 'read' }],
  },
  {
    path: '/project/list',
    element: () => <CanonicalEntryRedirect targetPath={PROJECT_ROUTES.LIST} resource="project" />,
    permissions: [{ resource: 'project', action: 'read' }],
  },
  {
    path: PROJECT_ROUTES.DETAIL_PATH,
    element: projectDetailPage,
    permissions: [{ resource: 'project', action: 'read' }],
  },
  {
    path: PROJECT_ROUTES.LIST,
    element: projectManagementPage,
    permissions: [{ resource: 'project', action: 'read' }],
  },

  // 个人中心
  {
    path: PROFILE_ROUTES.PROFILE,
    element: React.lazy(() => import('../pages/ProfilePage')),
    capabilityGuardBypass: true,
  },

  // 系统管理
  {
    path: SYSTEM_ROUTES.PARTY_DETAIL_PATH,
    element: React.lazy(() => import('../pages/System/PartyDetailPage')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.PARTIES,
    element: React.lazy(() => import('../pages/System/PartyListPage')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.USERS,
    element: React.lazy(() => import('../pages/System/UserManagement')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.ROLES,
    element: React.lazy(() => import('../pages/System/RoleManagement')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.ORGANIZATIONS,
    element: React.lazy(() => import('../pages/System/Organization')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.DICTIONARIES,
    element: React.lazy(() => import('../pages/System/DictionaryPage')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.TEMPLATES,
    element: React.lazy(() => import('../pages/System/TemplateManagementPage')),
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  {
    path: SYSTEM_ROUTES.LOGS,
    element: React.lazy(() => import('../pages/System/OperationLog')),
    adminOnly: true,
  },

  {
    path: SYSTEM_ROUTES.SETTINGS,
    element: React.lazy(() => import('../pages/System/SystemSettingsPage')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.DATA_POLICIES,
    element: React.lazy(() => import('../pages/System/DataPolicyManagementPage')),
    adminOnly: true,
  },
];

export const protectedRoutes: ProtectedRouteItem[] = baseProtectedRoutes;
