import { useState, useEffect, useCallback } from 'react'
import { message } from 'antd'
import { createLogger } from '@/utils/logger'

const permLogger = createLogger('usePermission')

export interface Permission {
  resource: string
  action: string
  granted: boolean
}

export interface UserRole {
  id: string
  name: string
  code: string
  permissions: string[]
}

export interface UserPermissions {
  userId: string
  username: string
  roles: UserRole[]
  permissions: string[]
  organizationId: string
}

export interface MenuItem {
  key: string
  label: string
  icon?: React.ReactNode
  path?: string
  permission?: Permission
  children?: MenuItem[]
}

const usePermission = () => {
  const [userPermissions, setUserPermissions] = useState<UserPermissions | null>(null)
  const [loading, setLoading] = useState(false)

  // 加载用户权限信息
  const loadUserPermissions = useCallback(async () => {
    setLoading(true)
    try {
      // 从localStorage或API获取当前用户信息
      const storedUser = localStorage.getItem('currentUser')
      if (!storedUser) {
        setUserPermissions(null)
        return
      }

      const currentUser = JSON.parse(storedUser)

      // 获取用户详细权限信息
      const userPermissionsData: UserPermissions = {
        userId: currentUser.id,
        username: currentUser.username,
        roles: currentUser.roles || [],
        permissions: currentUser.permissions || [],
        organizationId: currentUser.organization_id
      }

      setUserPermissions(userPermissionsData)
    } catch (error) {
      permLogger.error('加载用户权限失败:', error as Error)
      message.error('加载权限信息失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // 检查是否有特定权限
  const hasPermission = useCallback((resource: string, action: string): boolean => {
    if (!userPermissions) return false

    // 管理员拥有所有权限
    if (userPermissions.roles.some(role => role.code === 'admin')) {
      return true
    }

    const permissionKey = `${resource}:${action}`
    return userPermissions.permissions.includes(permissionKey)
  }, [userPermissions])

  // 检查是否有任意一个权限
  const hasAnyPermission = useCallback((permissions: Array<{ resource: string; action: string }>): boolean => {
    return permissions.some(permission => hasPermission(permission.resource, permission.action))
  }, [hasPermission])

  // 检查是否有所有权限
  const hasAllPermissions = useCallback((permissions: Array<{ resource: string; action: string }>): boolean => {
    return permissions.every(permission => hasPermission(permission.resource, permission.action))
  }, [hasPermission])

  // 检查角色
  const hasRole = useCallback((roleCode: string): boolean => {
    if (!userPermissions) return false
    return userPermissions.roles.some(role => role.code === roleCode)
  }, [userPermissions])

  // 检查是否是管理员
  const isAdmin = useCallback((): boolean => {
    return hasRole('admin')
  }, [hasRole])

  // 检查是否有组织访问权限
  const canAccessOrganization = useCallback((organizationId: string): boolean => {
    if (!userPermissions) return false

    // 管理员可以访问所有组织
    if (isAdmin()) return true

    // 检查是否是同一组织的用户
    return userPermissions.organizationId === organizationId
  }, [userPermissions, isAdmin])

  // 权限装饰器 - 用于包装组件
  const requirePermission = useCallback((
    resource: string,
    action: string,
    fallback?: React.ReactNode
  ) => {
    if (hasPermission(resource, action)) {
      return null
    }
    return fallback || <div>Access Denied</div>
  }, [hasPermission])

  // 页面权限检查
  const checkPageAccess = useCallback((pagePermissions: Array<{ resource: string; action: string }>): boolean => {
    // 如果没有配置权限要求，则允许访问
    if (!pagePermissions || pagePermissions.length === 0) {
      return true
    }

    return hasAnyPermission(pagePermissions)
  }, [hasAnyPermission])

  // 获取可访问的菜单项
  const getAccessibleMenuItems = useCallback((menuItems: MenuItem[]) => {
    if (!userPermissions) return []

    return menuItems.filter(item => {
      if (!item.permission) return true
      return hasPermission(item.permission.resource, item.permission.action)
    })
  }, [userPermissions, hasPermission])

  // 刷新权限信息
  const refreshPermissions = useCallback(async () => {
    await loadUserPermissions()
  }, [loadUserPermissions])

  useEffect(() => {
    loadUserPermissions()
  }, [loadUserPermissions])

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
    refreshPermissions
  }
}

export default usePermission

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
  SYSTEM_DICTIONARY: { resource: 'system', action: 'dictionary' }
} as const

// 页面权限配置
export const PAGE_PERMISSIONS = {
  '/system/users': [PERMISSIONS.USER_VIEW],
  '/system/roles': [PERMISSIONS.ROLE_VIEW],
  '/system/organizations': [PERMISSIONS.ORGANIZATION_VIEW],
  '/system/dictionaries': [PERMISSIONS.SYSTEM_DICTIONARY],
  '/system/logs': [PERMISSIONS.SYSTEM_LOGS],
  '/assets': [PERMISSIONS.ASSET_VIEW],
  '/assets/new': [PERMISSIONS.ASSET_CREATE],
  '/assets/import': [PERMISSIONS.ASSET_IMPORT],
  '/rental': [PERMISSIONS.RENTAL_VIEW],
  '/rental/contracts/new': [PERMISSIONS.RENTAL_CREATE]
}
