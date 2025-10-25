import React from 'react'
import { Navigate } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import LazyRoute from './LazyRoute'
import { RouteConfig } from '@/constants/routes'
import { PERMISSIONS } from '@/hooks/usePermission'

interface RouteBuilderConfig extends RouteConfig {
  lazy?: boolean
  component?: React.ComponentType<any> | React.LazyExoticComponent<React.ComponentType<any>>
  preload?: () => void
  children?: RouteBuilderConfig[]
}

/**
 * 路由构建器
 * 根据配置自动生成路由组件，支持嵌套路由
 */
class RouteBuilder {
  /**
   * 构建单个路由
   */
  static buildRoute(config: RouteBuilderConfig): JSX.Element {
    const {
      path,
      component: Component,
      lazy = false,
      permissions,
      errorBoundary = true,
      fallback,
      preload,
      title,
      children,
      ...props
    } = config

    // 如果没有组件，可能是重定向路由或容器路由
    if (!Component) {
      if (children && children.length > 0) {
        // 容器路由，渲染子路由
        return (
          <Route key={path} path={path} {...props}>
            {children.map((child, index) => (
              <React.Fragment key={child.path || index}>
                {RouteBuilder.buildRoute(child)}
              </React.Fragment>
            ))}
          </Route>
        )
      }

      // 重定向路由
      return (
        <Route key={path} path={path} element={<Navigate to="/" replace />} {...props} />
      )
    }

    // 构建路由属性
    const routeProps = {
      key: path,
      path,
      title,
      permissions,
      errorBoundary,
      fallback,
      ...props
    }

    // 根据是否懒加载选择不同的路由组件
    if (lazy) {
      return (
        <LazyRoute
          {...routeProps}
          component={Component as React.LazyExoticComponent<React.ComponentType<any>>}
          preload={preload}
        />
      )
    }

    return (
      <ProtectedRoute
        {...routeProps}
        component={Component as React.ComponentType<any>}
      />
    )
  }

  /**
   * 构建路由树
   */
  static buildRoutes(configs: RouteBuilderConfig[]): JSX.Element[] {
    return configs.map(config => RouteBuilder.buildRoute(config))
  }

  /**
   * 创建重定向路由
   */
  static createRedirect(from: string, to: string, replace = true): JSX.Element {
    return (
      <Route
        key={from}
        path={from}
        element={<Navigate to={to} replace={replace} />}
      />
    )
  }

  /**
   * 根据权限配置创建受保护路由
   */
  static createProtectedRoute(
    path: string,
    component: React.ComponentType<any>,
    permissionKey: keyof typeof PERMISSIONS,
    title?: string
  ): JSX.Element {
    return RouteBuilder.buildRoute({
      path,
      component,
      permissions: [PERMISSIONS[permissionKey]],
      title: title || path.split('/').pop() || '',
    })
  }

  /**
   * 创建懒加载路由
   */
  static createLazyRoute(
    path: string,
    component: React.LazyExoticComponent<React.ComponentType<any>>,
    options?: {
      title?: string
      permissions?: Array<{ resource: string; action: string }>
      preload?: () => void
      fallback?: React.ReactNode
    }
  ): JSX.Element {
    return RouteBuilder.buildRoute({
      path,
      component,
      lazy: true,
      title: options?.title || path.split('/').pop() || '',
      permissions: options?.permissions,
      preload: options?.preload,
      fallback: options?.fallback,
    })
  }
}

// 预定义的路由构建函数
export const AssetRoutes = {
  list: (Component: React.ComponentType<any>) =>
    RouteBuilder.createProtectedRoute('/assets/list', Component, 'ASSET_VIEW', '资产列表'),

  new: (Component: React.ComponentType<any>) =>
    RouteBuilder.createProtectedRoute('/assets/new', Component, 'ASSET_CREATE', '创建资产'),

  import: (Component: React.ComponentType<any>) =>
    RouteBuilder.createProtectedRoute('/assets/import', Component, 'ASSET_IMPORT', '资产导入'),

  analytics: (Component: React.ComponentType<any>) =>
    RouteBuilder.createProtectedRoute('/assets/analytics', Component, 'ASSET_VIEW', '资产分析'),
}

export const SystemRoutes = {
  users: (Component: React.ComponentType<any>) =>
    RouteBuilder.createProtectedRoute('/system/users', Component, 'USER_VIEW', '用户管理'),

  roles: (Component: React.ComponentType<any>) =>
    RouteBuilder.createProtectedRoute('/system/roles', Component, 'ROLE_VIEW', '角色管理'),

  organizations: (Component: React.ComponentType<any>) =>
    RouteBuilder.createProtectedRoute('/system/organizations', Component, 'ORGANIZATION_VIEW', '组织架构'),

  logs: (Component: React.ComponentType<any>) =>
    RouteBuilder.createProtectedRoute('/system/logs', Component, 'SYSTEM_LOGS', '操作日志'),
}

export default RouteBuilder