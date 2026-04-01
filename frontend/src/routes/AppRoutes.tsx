import React from 'react';
import { Navigate } from 'react-router-dom';
import type { AuthzAction, ResourceType } from '@/types/capability';
import LegacyRouteRedirect from './LegacyRouteRedirect';
import {
  ASSET_ROUTES,
  CONTRACT_GROUP_ROUTES,
  LEGACY_RENTAL_ROUTES,
  MANAGER_ROUTES,
  OWNERSHIP_ROUTES,
  OWNER_ROUTES,
  PROJECT_ROUTES,
  PROFILE_ROUTES,
  SYSTEM_ROUTES,
  BASE_PATHS,
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
const legacyRentalRetiredPage = React.lazy(() => import('../pages/Rental/LegacyRentalRetiredPage'));
const assetListPage = React.lazy(() => import('../pages/Assets/AssetListPage'));
const assetDetailPage = React.lazy(() => import('../pages/Assets/AssetDetailPage'));
const contractGroupListPage = React.lazy(
  () => import('../pages/ContractGroup/ContractGroupListPage')
);
const contractGroupDetailPage = React.lazy(
  () => import('../pages/ContractGroup/ContractGroupDetailPage')
);
const propertyCertificateListPage = React.lazy(
  () => import('../pages/PropertyCertificate/PropertyCertificateList')
);
const propertyCertificateDetailPage = React.lazy(
  () => import('../pages/PropertyCertificate/PropertyCertificateDetailPage')
);
const projectManagementPage = React.lazy(() => import('../pages/Project/ProjectManagementPage'));
const projectDetailPage = React.lazy(() => import('../pages/Project/ProjectDetailPage'));

const legacyRentalPdfImportRedirect: React.FC = () => (
  <Navigate to={CONTRACT_GROUP_ROUTES.IMPORT} replace />
);

const baseProtectedRoutes: ProtectedRouteItem[] = [
  // 仪表板 - 首页
  {
    path: BASE_PATHS.DASHBOARD,
    element: React.lazy(() => import('../pages/Dashboard/DashboardPage')),
    capabilityGuardBypass: true,
  },
  {
    path: BASE_PATHS.ASSETS,
    element: () => <LegacyRouteRedirect legacyPath={BASE_PATHS.ASSETS} />,
    permissions: [{ resource: 'asset', action: 'read' }],
  },

  // 资产管理模块 - 注意路由顺序，更具体的路径要在前面
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
    path: ASSET_ROUTES.ANALYTICS,
    element: React.lazy(() => import('../pages/Assets/AssetAnalyticsPage')),
    permissions: [{ resource: 'analytics', action: 'read' }],
  },
  {
    path: ASSET_ROUTES.ANALYTICS_SIMPLE,
    element: React.lazy(() => import('../pages/Assets/SimpleAnalyticsPage')),
    permissions: [{ resource: 'analytics', action: 'read' }],
  },
  {
    path: ASSET_ROUTES.LIST,
    element: () => <LegacyRouteRedirect legacyPath={ASSET_ROUTES.LIST} />,
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  {
    path: ASSET_ROUTES.DETAIL_PATH,
    element: assetDetailPage,
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  {
    path: OWNER_ROUTES.ASSETS,
    element: assetListPage,
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  {
    path: OWNER_ROUTES.ASSET_DETAIL_PATH,
    element: assetDetailPage,
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  {
    path: MANAGER_ROUTES.ASSETS,
    element: assetListPage,
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  {
    path: MANAGER_ROUTES.ASSET_DETAIL_PATH,
    element: assetDetailPage,
    permissions: [{ resource: 'asset', action: 'read' }],
  },
  {
    path: OWNER_ROUTES.CUSTOMER_DETAIL_PATH,
    element: React.lazy(() => import('../pages/Customer/CustomerDetailPage')),
    permissions: [{ resource: 'analytics', action: 'read' }],
  },
  {
    path: MANAGER_ROUTES.CUSTOMER_DETAIL_PATH,
    element: React.lazy(() => import('../pages/Customer/CustomerDetailPage')),
    permissions: [{ resource: 'analytics', action: 'read' }],
  },

  // 租赁管理模块 - 注意路由顺序，具体路径必须在动态路径之前
  {
    path: LEGACY_RENTAL_ROUTES.CONTRACTS.LIST,
    element: legacyRentalRetiredPage,
    permissions: [{ resource: 'contract', action: 'read' }],
  },
  {
    path: LEGACY_RENTAL_ROUTES.CONTRACTS.NEW, // 具体路由 - 创建合同
    element: legacyRentalRetiredPage,
    permissions: [{ resource: 'contract', action: 'read' }],
  },
  {
    path: LEGACY_RENTAL_ROUTES.CONTRACTS.CREATE, // 具体路由 - 创建合同（备用）
    element: legacyRentalRetiredPage,
    permissions: [{ resource: 'contract', action: 'read' }],
  },
  {
    path: LEGACY_RENTAL_ROUTES.CONTRACTS.PDF_IMPORT, // 具体路由 - PDF导入
    element: legacyRentalPdfImportRedirect,
    permissions: [{ resource: 'contract_group', action: 'create' }],
  },
  {
    path: LEGACY_RENTAL_ROUTES.CONTRACTS.RENEW_PATH, // 具体路由 - 续签合同（必须在 :id/edit 之前）
    element: legacyRentalRetiredPage,
    permissions: [{ resource: 'contract', action: 'read' }],
  },
  {
    path: LEGACY_RENTAL_ROUTES.CONTRACTS.DETAIL_PATH, // 动态路由 - 合同详情页
    element: legacyRentalRetiredPage,
    permissions: [{ resource: 'contract', action: 'read' }],
  },
  {
    path: LEGACY_RENTAL_ROUTES.CONTRACTS.EDIT_PATH, // 动态路由 - 编辑合同
    element: legacyRentalRetiredPage,
    permissions: [{ resource: 'contract', action: 'read' }],
  },
  {
    path: LEGACY_RENTAL_ROUTES.LEDGER,
    element: legacyRentalRetiredPage,
    permissions: [{ resource: 'contract', action: 'read' }],
  },
  {
    path: LEGACY_RENTAL_ROUTES.STATISTICS,
    element: legacyRentalRetiredPage,
    permissions: [{ resource: 'contract', action: 'read' }],
  },

  {
    path: CONTRACT_GROUP_ROUTES.LIST,
    element: () => <LegacyRouteRedirect legacyPath={CONTRACT_GROUP_ROUTES.LIST} />,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: CONTRACT_GROUP_ROUTES.NEW,
    element: React.lazy(() => import('../pages/ContractGroup/ContractGroupFormPage')),
    permissions: [{ resource: 'contract_group', action: 'create' }],
  },
  {
    path: CONTRACT_GROUP_ROUTES.IMPORT,
    element: React.lazy(() => import('../pages/Contract/PDFImportPage')),
    permissions: [{ resource: 'contract_group', action: 'create' }],
  },
  {
    path: CONTRACT_GROUP_ROUTES.DETAIL_PATH,
    element: contractGroupDetailPage,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: OWNER_ROUTES.CONTRACT_GROUPS,
    element: contractGroupListPage,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: OWNER_ROUTES.CONTRACT_GROUP_DETAIL_PATH,
    element: contractGroupDetailPage,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: MANAGER_ROUTES.CONTRACT_GROUPS,
    element: contractGroupListPage,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: MANAGER_ROUTES.CONTRACT_GROUP_DETAIL_PATH,
    element: contractGroupDetailPage,
    permissions: [{ resource: 'contract_group', action: 'read' }],
  },
  {
    path: CONTRACT_GROUP_ROUTES.EDIT_PATH,
    element: React.lazy(() => import('../pages/ContractGroup/ContractGroupFormPage')),
    permissions: [{ resource: 'contract_group', action: 'update' }],
  },
  {
    path: PROPERTY_CERTIFICATE_ROUTES.LIST,
    element: () => <LegacyRouteRedirect legacyPath={PROPERTY_CERTIFICATE_ROUTES.LIST} />,
    permissions: [{ resource: 'property_certificate', action: 'read' }],
  },
  {
    path: PROPERTY_CERTIFICATE_ROUTES.IMPORT,
    element: React.lazy(() => import('../pages/PropertyCertificate/PropertyCertificateImport')),
    permissions: [{ resource: 'property_certificate', action: 'create' }],
  },
  {
    path: PROPERTY_CERTIFICATE_ROUTES.DETAIL_PATH,
    element: propertyCertificateDetailPage,
    permissions: [{ resource: 'property_certificate', action: 'read' }],
  },
  {
    path: OWNER_ROUTES.PROPERTY_CERTIFICATES,
    element: propertyCertificateListPage,
    permissions: [{ resource: 'property_certificate', action: 'read' }],
  },
  {
    path: OWNER_ROUTES.PROPERTY_CERTIFICATE_DETAIL_PATH,
    element: propertyCertificateDetailPage,
    permissions: [{ resource: 'property_certificate', action: 'read' }],
  },

  // 权属方管理 - 注意路由顺序，详情页必须在列表页之前
  {
    path: OWNERSHIP_ROUTES.EDIT_PATH,
    element: React.lazy(() => import('../pages/Ownership/OwnershipManagementPage')),
    permissions: [{ resource: 'party', action: 'read' }],
  },
  {
    path: OWNERSHIP_ROUTES.DETAIL_PATH,
    element: React.lazy(() => import('../pages/Ownership/OwnershipDetailPage')),
    permissions: [{ resource: 'party', action: 'read' }],
  },
  {
    path: OWNERSHIP_ROUTES.LIST,
    element: React.lazy(() => import('../pages/Ownership/OwnershipManagementPage')),
    permissions: [{ resource: 'party', action: 'read' }],
  },

  // 项目管理 - 注意路由顺序，详情页必须在列表页之前
  {
    path: PROJECT_ROUTES.EDIT_PATH,
    element: projectManagementPage,
    permissions: [{ resource: 'project', action: 'read' }],
  },
  {
    path: PROJECT_ROUTES.DETAIL_PATH,
    element: projectDetailPage,
    permissions: [{ resource: 'project', action: 'read' }],
  },
  {
    path: PROJECT_ROUTES.LIST,
    element: () => <LegacyRouteRedirect legacyPath={PROJECT_ROUTES.LIST} />,
    permissions: [{ resource: 'project', action: 'read' }],
  },
  {
    path: MANAGER_ROUTES.PROJECTS,
    element: projectManagementPage,
    permissions: [{ resource: 'project', action: 'read' }],
  },
  {
    path: MANAGER_ROUTES.PROJECT_DETAIL_PATH,
    element: projectDetailPage,
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
    element: React.lazy(() => import('../pages/System/UserManagementPage')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.ROLES,
    element: React.lazy(() => import('../pages/System/RoleManagementPage')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.ORGANIZATIONS,
    element: React.lazy(() => import('../pages/System/OrganizationPage')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.DICTIONARIES,
    element: React.lazy(() => import('../pages/System/DictionaryPage')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.LOGS,
    element: React.lazy(() => import('../pages/System/OperationLogPage')),
    adminOnly: true,
  },
  {
    path: SYSTEM_ROUTES.TEMPLATES,
    element: React.lazy(() => import('../pages/System/TemplateManagementPage')),
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
