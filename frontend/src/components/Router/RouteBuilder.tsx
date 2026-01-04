import React from "react";
import { Navigate, Route } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import LazyRoute from "./LazyRoute";
import { RouteConfig } from "@/constants/routes";
import { PERMISSIONS } from "@/hooks/usePermission";

// 路由组件属性类型
export interface RouteComponentProps {
  title?: string;
  permissions?: Array<{ resource: string; action: string }>;
  [key: string]: unknown;
}

interface RouteBuilderConfig extends RouteConfig {
  lazy?: boolean;
  component?:
    | React.ComponentType<RouteComponentProps>
    | React.LazyExoticComponent<React.ComponentType<RouteComponentProps>>;
  preload?: () => void;
  children?: RouteBuilderConfig[];
  errorBoundary?: boolean;
  fallback?: React.ReactNode;
  element?: React.ReactNode;
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
      element,
      children,
      ...props
    } = config;

    // 如果有明确的 element 属性（如重定向），使用 Route
    if (element !== null && element !== undefined) {
      return <Route key={path} path={path} element={element} {...props} />;
    }

    // 如果没有组件，但有子路由，创建容器路由
    if (!Component && children && children.length > 0) {
      return (
        <Route key={path} path={path} {...props}>
          {children.map((child, _index) => RouteBuilder.buildRoute(child))}
        </Route>
      );
    }

    // 如果没有组件也没有子路由，返回重定向
    if (!Component) {
      return <Route key={path} path={path} element={<Navigate to="/" replace />} {...props} />;
    }

    // 构建路由属性（不传递 key 和 element，这些由 Route 组件处理）
    const routeProps = {
      path,
      title,
      permissions,
      errorBoundary,
      fallback,
      ...props,
    };

    // 根据是否懒加载选择不同的路由组件
    if (lazy) {
      return (
        <LazyRoute
          {...routeProps}
          component={
            Component as React.LazyExoticComponent<React.ComponentType<RouteComponentProps>>
          }
          preload={preload}
        />
      );
    }

    return (
      <ProtectedRoute
        {...routeProps}
        component={Component as React.ComponentType<RouteComponentProps>}
      />
    );
  }

  /**
   * 构建路由树
   */
  static buildRoutes(configs: RouteBuilderConfig[]): JSX.Element[] {
    return configs.map((config) => RouteBuilder.buildRoute(config));
  }

  /**
   * 创建重定向路由
   */
  static createRedirect(from: string, to: string, replace = true): JSX.Element {
    return <Route key={from} path={from} element={<Navigate to={to} replace={replace} />} />;
  }

  /**
   * 根据权限配置创建受保护路由
   */
  static createProtectedRoute(
    path: string,
    component: React.ComponentType<RouteComponentProps>,
    permissionKey: keyof typeof PERMISSIONS,
    title?: string,
  ): JSX.Element {
    return RouteBuilder.buildRoute({
      path,
      component,
      permissions: [PERMISSIONS[permissionKey]],
      title: (title !== null && title !== undefined && title !== '') ? title : (path.split("/").pop() !== null && path.split("/").pop() !== undefined && path.split("/").pop() !== '') ? path.split("/").pop()! : '',
    });
  }

  /**
   * 创建懒加载路由
   */
  static createLazyRoute(
    path: string,
    component: React.LazyExoticComponent<React.ComponentType<RouteComponentProps>>,
    options?: {
      title?: string;
      permissions?: Array<{ resource: string; action: string }>;
      preload?: () => void;
      fallback?: React.ReactNode;
    },
  ): JSX.Element {
    return RouteBuilder.buildRoute({
      path,
      component,
      lazy: true,
      title: (options?.title !== null && options?.title !== undefined && options?.title !== '') ? options.title : (path.split("/").pop() !== null && path.split("/").pop() !== undefined && path.split("/").pop() !== '') ? path.split("/").pop()! : '',
      permissions: options?.permissions,
      preload: options?.preload,
      fallback: options?.fallback,
    });
  }
}

// 预定义的路由构建函数
export const AssetRoutes = {
  list: (Component: React.ComponentType<RouteComponentProps>) =>
    RouteBuilder.createProtectedRoute("/assets/list", Component, "ASSET_VIEW", "资产列表"),

  new: (Component: React.ComponentType<RouteComponentProps>) =>
    RouteBuilder.createProtectedRoute("/assets/new", Component, "ASSET_CREATE", "创建资产"),

  import: (Component: React.ComponentType<RouteComponentProps>) =>
    RouteBuilder.createProtectedRoute("/assets/import", Component, "ASSET_IMPORT", "资产导入"),

  analytics: (Component: React.ComponentType<RouteComponentProps>) =>
    RouteBuilder.createProtectedRoute("/assets/analytics", Component, "ASSET_VIEW", "资产分析"),
};

export const SystemRoutes = {
  users: (Component: React.ComponentType<RouteComponentProps>) =>
    RouteBuilder.createProtectedRoute("/system/users", Component, "USER_VIEW", "用户管理"),

  roles: (Component: React.ComponentType<RouteComponentProps>) =>
    RouteBuilder.createProtectedRoute("/system/roles", Component, "ROLE_VIEW", "角色管理"),

  organizations: (Component: React.ComponentType<RouteComponentProps>) =>
    RouteBuilder.createProtectedRoute(
      "/system/organizations",
      Component,
      "ORGANIZATION_VIEW",
      "组织架构",
    ),

  logs: (Component: React.ComponentType<any>) =>
    RouteBuilder.createProtectedRoute("/system/logs", Component, "SYSTEM_LOGS", "操作日志"),
};

export default RouteBuilder;
