import { useState, useEffect, useCallback } from 'react';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import { AuthStorage } from '@/utils/AuthStorage';

const permLogger = createLogger('usePermission');

export interface Permission {
  resource: string;
  action: string;
  granted: boolean;
}

export interface UserPermissions {
  userId: string;
  username: string;
  roles: string[];
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

const usePermission = () => {
  const [userPermissions, setUserPermissions] = useState<UserPermissions | null>(null);
  const [loading, setLoading] = useState(false);

  // 加载用户权限信息
  const loadUserPermissions = useCallback(async () => {
    setLoading(true);
    try {
      // Get auth data from centralized AuthStorage
      const authData = AuthStorage.getAuthData();

      if (authData == null) {
        setUserPermissions(null);
        return;
      }

      // Create user permissions object
      const userPermissionsData: UserPermissions = {
        userId: authData.user.id,
        username: authData.user.username,
        roles: authData.user.role ? [authData.user.role] : [],
        permissions: authData.permissions,
        organizationId: authData.user.organization_id,
      };

      setUserPermissions(userPermissionsData);
    } catch (error) {
      permLogger.error('Failed to load user permissions:', error as Error);
      MessageManager.error('Failed to load permissions');
    } finally {
      setLoading(false);
    }
  }, []);

  // 检查是否有特定权限
  const hasPermission = useCallback(
    (resource: string, action: string): boolean => {
      if (!userPermissions) return false;

      // 管理员拥有所有权限
      if (userPermissions.roles.includes('admin')) {
        return true;
      }

      // Check if user has permission matching resource and action
      return userPermissions.permissions.some(
        perm => perm.resource === resource && perm.action === action
      );
    },
    [userPermissions]
  );

  // 检查是否有任意一个权限
  const hasAnyPermission = useCallback(
    (permissions: Array<{ resource: string; action: string }>): boolean => {
      return permissions.some(permission => hasPermission(permission.resource, permission.action));
    },
    [hasPermission]
  );

  // 检查是否有所有权限
  const hasAllPermissions = useCallback(
    (permissions: Array<{ resource: string; action: string }>): boolean => {
      return permissions.every(permission => hasPermission(permission.resource, permission.action));
    },
    [hasPermission]
  );

  // 检查角色
  const hasRole = useCallback(
    (roleCode: string): boolean => {
      if (!userPermissions) return false;
      return userPermissions.roles.includes(roleCode);
    },
    [userPermissions]
  );

  // 检查是否是管理员
  const isAdmin = useCallback((): boolean => {
    return hasRole('admin');
  }, [hasRole]);

  // 检查是否有组织访问权限
  const canAccessOrganization = useCallback(
    (organizationId: string): boolean => {
      if (!userPermissions) return false;

      // 管理员可以访问所有组织
      if (isAdmin()) return true;

      // 检查是否是同一组织的用户
      return userPermissions.organizationId === organizationId;
    },
    [userPermissions, isAdmin]
  );

  // 权限装饰器 - 用于包装组件
  const requirePermission = useCallback(
    (resource: string, action: string, fallback?: React.ReactNode) => {
      if (hasPermission(resource, action)) {
        return null;
      }
      return fallback ?? <div>Access Denied</div>;
    },
    [hasPermission]
  );

  // 页面权限检查
  const checkPageAccess = useCallback(
    (pagePermissions: Array<{ resource: string; action: string }>): boolean => {
      // 如果没有配置权限要求，则允许访问
      if (pagePermissions == null || pagePermissions.length === 0) {
        return true;
      }

      return hasAnyPermission(pagePermissions);
    },
    [hasAnyPermission]
  );

  // 获取可访问的菜单项
  const getAccessibleMenuItems = useCallback(
    (menuItems: MenuItem[]) => {
      if (userPermissions == null) return [];

      return menuItems.filter(item => {
        if (item.permission == null) return true;
        return hasPermission(item.permission.resource, item.permission.action);
      });
    },
    [userPermissions, hasPermission]
  );

  // 刷新权限信息
  const refreshPermissions = useCallback(async () => {
    await loadUserPermissions();
  }, [loadUserPermissions]);

  useEffect(() => {
    loadUserPermissions();
  }, [loadUserPermissions]);

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

// 权限常量定义
export const PERMISSIONS = {
  // 用户管理权限
  USER_VIEW: { resource: 'user', action: 'view' },
  USER_CREATE: { resource: 'user', action: 'create' },
  USER_EDIT: { resource: 'user', action: 'edit' },
  USER_DELETE: { resource: 'user', action: 'delete' },
  USER_LOCK: { resource: 'user', action: 'lock' },

  // 角色管理权限
  ROLE_VIEW: { resource: 'role', action: 'view' },
  ROLE_CREATE: { resource: 'role', action: 'create' },
  ROLE_EDIT: { resource: 'role', action: 'edit' },
  ROLE_DELETE: { resource: 'role', action: 'delete' },
  ROLE_ASSIGN_PERMISSIONS: { resource: 'role', action: 'assign_permissions' },

  // 组织管理权限
  ORGANIZATION_VIEW: { resource: 'organization', action: 'view' },
  ORGANIZATION_CREATE: { resource: 'organization', action: 'create' },
  ORGANIZATION_EDIT: { resource: 'organization', action: 'edit' },
  ORGANIZATION_DELETE: { resource: 'organization', action: 'delete' },

  // 资产管理权限
  ASSET_VIEW: { resource: 'asset', action: 'view' },
  ASSET_CREATE: { resource: 'asset', action: 'create' },
  ASSET_EDIT: { resource: 'asset', action: 'edit' },
  ASSET_DELETE: { resource: 'asset', action: 'delete' },
  ASSET_IMPORT: { resource: 'asset', action: 'import' },
  ASSET_EXPORT: { resource: 'asset', action: 'export' },

  // 租赁管理权限
  RENTAL_VIEW: { resource: 'rental', action: 'view' },
  RENTAL_CREATE: { resource: 'rental', action: 'create' },
  RENTAL_EDIT: { resource: 'rental', action: 'edit' },
  RENTAL_DELETE: { resource: 'rental', action: 'delete' },

  // 系统管理权限
  SYSTEM_SETTINGS: { resource: 'system', action: 'settings' },
  SYSTEM_LOGS: { resource: 'system', action: 'logs' },
  SYSTEM_BACKUP: { resource: 'system', action: 'backup' },
  SYSTEM_DICTIONARY: { resource: 'system', action: 'dictionary' },
} as const;

// 页面权限配置
export const PAGE_PERMISSIONS = {
  '/system/users': [PERMISSIONS.USER_VIEW],
  '/system/roles': [PERMISSIONS.ROLE_VIEW],
  '/system/organizations': [PERMISSIONS.ORGANIZATION_VIEW],
  '/system/dictionaries': [PERMISSIONS.SYSTEM_DICTIONARY],
  '/system/logs': [PERMISSIONS.SYSTEM_LOGS],
  '/system/settings': [PERMISSIONS.SYSTEM_SETTINGS],
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
