import React from 'react';
import type { AuthzAction, ResourceType } from '@/types/capability';
import { ASSET_OPERATIONS_V5_ROUTES, PROFILE_ROUTES, SYSTEM_ROUTES } from '@/constants/routes';

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
 * v5 一次性切换后的生产路由：资产运营 + 系统管理 + 个人中心。
 * 旧业务路由（工作台/资产/产权证/合同中心/项目/经营台账/经营分析/搜索）
 * 已随 V1-4 切换移除，见 docs/archive/backend-plans/2026-10-23-asset-operations-v5-v1.md。
 */
const baseProtectedRoutes: ProtectedRouteItem[] = [
  // 资产运营
  {
    path: ASSET_OPERATIONS_V5_ROUTES.UNITS,
    element: React.lazy(() => import('../pages/AssetOperations/AssetUnitsPage')),
    permissions: [{ resource: 'asset_ops', action: 'read' }],
  },
  {
    path: ASSET_OPERATIONS_V5_ROUTES.INTAKE,
    element: React.lazy(() => import('../pages/AssetOperations/ContractIntakePage')),
    permissions: [{ resource: 'asset_ops', action: 'write' }],
  },
  {
    path: ASSET_OPERATIONS_V5_ROUTES.TERMINAL_ACTIONS,
    element: React.lazy(async () => {
      const module = await import('../pages/AssetOperations/LifecycleActionsPage');
      return { default: module.TerminalActionsPage };
    }),
    permissions: [{ resource: 'asset_ops', action: 'write' }],
  },
  {
    path: ASSET_OPERATIONS_V5_ROUTES.UPSTREAM_ACTIONS,
    element: React.lazy(async () => {
      const module = await import('../pages/AssetOperations/LifecycleActionsPage');
      return { default: module.UpstreamActionsPage };
    }),
    permissions: [{ resource: 'asset_ops', action: 'write' }],
  },
  {
    path: ASSET_OPERATIONS_V5_ROUTES.UPSTREAM_CONTRACTS,
    element: React.lazy(async () => {
      const module = await import('../pages/AssetOperations/ContractListsPage');
      return { default: module.UpstreamContractsPage };
    }),
    permissions: [{ resource: 'asset_ops', action: 'read' }],
  },
  {
    path: ASSET_OPERATIONS_V5_ROUTES.TERMINAL_CONTRACTS,
    element: React.lazy(async () => {
      const module = await import('../pages/AssetOperations/ContractListsPage');
      return { default: module.TerminalContractsPage };
    }),
    permissions: [{ resource: 'asset_ops', action: 'read' }],
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
