import { useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useCapabilities } from '@/hooks/useCapabilities';
import type { AuthzAction, ResourceType, TemporaryAdminAction } from '@/types/capability';

const ACTION_ALIASES: Record<string, AuthzAction> = {
  view: 'read',
  edit: 'update',
  import: 'create',
  settings: 'update',
  logs: 'read',
  dictionary: 'read',
  lock: 'update',
  assign_permissions: 'update',
};

const RESOURCE_ALIASES: Record<string, ResourceType> = {
  rental: 'rent_contract',
  organization: 'party',
  ownership: 'party',
};

const normalizeAction = (action: string): AuthzAction | TemporaryAdminAction => {
  if (action === 'backup') {
    return 'backup';
  }
  return ACTION_ALIASES[action] ?? (action as AuthzAction);
};

const normalizeResource = (resource: string): ResourceType => {
  if (resource === 'system_settings' || resource === 'operation_log' || resource === 'dictionary') {
    return 'system';
  }
  return RESOURCE_ALIASES[resource] ?? (resource as ResourceType);
};

export interface Permission {
  resource: string;
  action: string;
  granted: boolean;
}

export interface UserPermissions {
  userId: string;
  username: string;
  roles: string[];
  roleIds?: string[];
  isAdmin?: boolean;
  permissions: Array<{ resource: string; action: string }>;
  organizationId?: string;
}

export interface MenuItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  path?: string;
  permission?: Permission;
  children?: MenuItem[];
}

/**
 * @deprecated Phase 3 迁移期兼容壳，请优先使用 useCapabilities。
 */
const usePermission = () => {
  const { user, permissions } = useAuth();
  const { canPerform, hasPartyAccess, loading } = useCapabilities();

  const userPermissions = useMemo<UserPermissions | null>(() => {
    if (user == null) {
      return null;
    }

    return {
      userId: user.id,
      username: user.username,
      roles: user.roles ?? (user.role_name != null ? [user.role_name] : []),
      roleIds: user.role_ids ?? (user.role_id != null ? [user.role_id] : []),
      isAdmin: user.is_admin === true,
      permissions,
      organizationId: user.default_organization_id,
    };
  }, [permissions, user]);

  const hasPermission = useCallback(
    (resource: string, action: string): boolean => {
      const normalizedResource = normalizeResource(resource);
      const normalizedAction = normalizeAction(action);
      return canPerform(normalizedAction, normalizedResource);
    },
    [canPerform]
  );

  const hasAnyPermission = useCallback(
    (requiredPermissions: Array<{ resource: string; action: string }>): boolean => {
      return requiredPermissions.some(permission =>
        hasPermission(permission.resource, permission.action)
      );
    },
    [hasPermission]
  );

  const hasAllPermissions = useCallback(
    (requiredPermissions: Array<{ resource: string; action: string }>): boolean => {
      return requiredPermissions.every(permission =>
        hasPermission(permission.resource, permission.action)
      );
    },
    [hasPermission]
  );

  const hasRole = useCallback(
    (roleCode: string): boolean => {
      return userPermissions?.roles.includes(roleCode) === true;
    },
    [userPermissions?.roles]
  );

  const isAdmin = useCallback((): boolean => {
    return userPermissions?.isAdmin === true;
  }, [userPermissions?.isAdmin]);

  const canAccessOrganization = useCallback(
    (organizationId: string): boolean => {
      if (isAdmin()) {
        return true;
      }

      return (
        hasPartyAccess(organizationId, 'owner', 'party') ||
        hasPartyAccess(organizationId, 'manager', 'party')
      );
    },
    [hasPartyAccess, isAdmin]
  );

  const requirePermission = useCallback(
    (resource: string, action: string, fallback?: React.ReactNode) => {
      if (hasPermission(resource, action)) {
        return null;
      }
      return fallback ?? <div>Access Denied</div>;
    },
    [hasPermission]
  );

  const checkPageAccess = useCallback(
    (pagePermissions: Array<{ resource: string; action: string }>): boolean => {
      if (pagePermissions.length === 0) {
        return true;
      }
      return hasAnyPermission(pagePermissions);
    },
    [hasAnyPermission]
  );

  const getAccessibleMenuItems = useCallback(
    (menuItems: MenuItem[]): MenuItem[] => {
      return menuItems.filter(item => {
        if (item.permission == null) {
          return true;
        }

        return hasPermission(item.permission.resource, item.permission.action);
      });
    },
    [hasPermission]
  );

  const refreshPermissions = useCallback(async () => {
    // 兼容壳：权限刷新统一由 AuthContext.refreshCapabilities 触发。
    return Promise.resolve();
  }, []);

  return {
    userPermissions,
    loading,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    isAdmin,
    canAccessOrganization,
    requirePermission,
    checkPageAccess,
    getAccessibleMenuItems,
    refreshPermissions,
  };
};

export default usePermission;

// 兼容常量：调用方会在 P3e 统一移除。
export const PERMISSIONS = {
  USER_VIEW: { resource: 'user', action: 'read' },
  USER_CREATE: { resource: 'user', action: 'create' },
  USER_EDIT: { resource: 'user', action: 'update' },
  USER_DELETE: { resource: 'user', action: 'delete' },
  USER_LOCK: { resource: 'user', action: 'update' },

  ROLE_VIEW: { resource: 'role', action: 'read' },
  ROLE_CREATE: { resource: 'role', action: 'create' },
  ROLE_EDIT: { resource: 'role', action: 'update' },
  ROLE_DELETE: { resource: 'role', action: 'delete' },
  ROLE_ASSIGN_PERMISSIONS: { resource: 'role', action: 'update' },

  ORGANIZATION_VIEW: { resource: 'party', action: 'read' },
  ORGANIZATION_CREATE: { resource: 'party', action: 'create' },
  ORGANIZATION_EDIT: { resource: 'party', action: 'update' },
  ORGANIZATION_DELETE: { resource: 'party', action: 'delete' },

  ASSET_VIEW: { resource: 'asset', action: 'read' },
  ASSET_CREATE: { resource: 'asset', action: 'create' },
  ASSET_EDIT: { resource: 'asset', action: 'update' },
  ASSET_DELETE: { resource: 'asset', action: 'delete' },
  ASSET_IMPORT: { resource: 'asset', action: 'create' },
  ASSET_EXPORT: { resource: 'asset', action: 'export' },

  RENTAL_VIEW: { resource: 'rent_contract', action: 'read' },
  RENTAL_CREATE: { resource: 'rent_contract', action: 'create' },
  RENTAL_EDIT: { resource: 'rent_contract', action: 'update' },
  RENTAL_DELETE: { resource: 'rent_contract', action: 'delete' },

  SYSTEM_SETTINGS: { resource: 'system_settings', action: 'update' },
  SYSTEM_SETTINGS_READ: { resource: 'system_settings', action: 'read' },
  SYSTEM_LOGS: { resource: 'operation_log', action: 'read' },
  SYSTEM_BACKUP: { resource: 'system_settings', action: 'backup' },
  SYSTEM_DICTIONARY: { resource: 'dictionary', action: 'read' },
  SYSTEM_TEMPLATES: { resource: 'llm_prompt', action: 'read' },
} as const;

export const PAGE_PERMISSIONS = {
  '/system/users': [PERMISSIONS.USER_VIEW],
  '/system/roles': [PERMISSIONS.ROLE_VIEW],
  '/system/organizations': [PERMISSIONS.ORGANIZATION_VIEW],
  '/system/dictionaries': [PERMISSIONS.SYSTEM_DICTIONARY],
  '/system/templates': [PERMISSIONS.SYSTEM_TEMPLATES],
  '/system/logs': [PERMISSIONS.SYSTEM_LOGS],
  '/system/settings': [PERMISSIONS.SYSTEM_SETTINGS_READ, PERMISSIONS.SYSTEM_SETTINGS],
  '/assets/list': [PERMISSIONS.ASSET_VIEW],
  '/assets/new': [PERMISSIONS.ASSET_CREATE],
  '/assets/import': [PERMISSIONS.ASSET_IMPORT],
  '/assets/analytics': [PERMISSIONS.ASSET_VIEW],
  '/assets/analytics-simple': [PERMISSIONS.ASSET_VIEW],
  '/assets/:id': [PERMISSIONS.ASSET_VIEW],
  '/rental/contracts': [PERMISSIONS.RENTAL_VIEW],
  '/rental/contracts/new': [PERMISSIONS.RENTAL_CREATE],
  '/rental/contracts/create': [PERMISSIONS.RENTAL_CREATE],
  '/rental/contracts/pdf-import': [PERMISSIONS.RENTAL_CREATE],
  '/rental/contracts/:id': [PERMISSIONS.RENTAL_VIEW],
  '/rental/contracts/:id/renew': [PERMISSIONS.RENTAL_EDIT],
  '/rental/contracts/:id/edit': [PERMISSIONS.RENTAL_EDIT],
  '/rental/ledger': [PERMISSIONS.RENTAL_VIEW],
  '/rental/statistics': [PERMISSIONS.RENTAL_VIEW],
};
