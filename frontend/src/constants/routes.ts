/**
 * 路由常量定义
 * 统一路由命名规范，使用 kebab-case
 */

// 基础路径常量
export const BASE_PATHS = {
  DASHBOARD: '/dashboard',
  ASSETS: '/assets',
  RENTAL: '/rental',
  OWNERSHIP: '/ownership',
  PROJECT: '/project',
  SYSTEM: '/system',
  FINANCE: '/finance',
  DOCUMENTS: '/documents',
} as const;

// 资产管理路由
export const ASSET_ROUTES = {
  LIST: '/assets/list',
  NEW: '/assets/new',
  IMPORT: '/assets/import',
  ANALYTICS: '/assets/analytics',
  DETAIL: (id: string) => `/assets/${id}`,
  EDIT: (id: string) => `/assets/${id}/edit`,
} as const;

// 租赁管理路由
export const RENTAL_ROUTES = {
  CONTRACTS: {
    LIST: '/rental/contracts',
    NEW: '/rental/contracts/new',
    PDF_IMPORT: '/rental/contracts/pdf-import',
    DETAIL: (id: string) => `/rental/contracts/${id}`,
    EDIT: (id: string) => `/rental/contracts/${id}/edit`,
  },
  LEDGER: '/rental/ledger',
  STATISTICS: '/rental/statistics',
} as const;

// 系统管理路由
export const SYSTEM_ROUTES = {
  USERS: '/system/users',
  ROLES: '/system/roles',
  ORGANIZATIONS: '/system/organizations',
  DICTIONARIES: '/system/dictionaries',
  TEMPLATES: '/system/templates',
  LOGS: '/system/logs',
  SETTINGS: '/system/settings',
} as const;

// 其他模块路由
export const OTHER_ROUTES = {
  OWNERSHIP: '/ownership',
  PROJECT: '/project',
} as const;

// 页面重定向配置
export const REDIRECTS = {
  ROOT: '/dashboard',
  ASSETS_ROOT: '/assets/list',
  RENTAL_ROOT: '/rental/contracts',
} as const;

// 404 处理
export const NOT_FOUND_REDIRECT = '/dashboard';

// 路由类型定义
export interface RouteConfig {
  path: string;
  title: string;
  icon?: string;
  permissions?: Array<{ resource: string; action: string }>;
  breadcrumb?: string[];
  children?: RouteConfig[];
}

// 完整路由配置树
export const ROUTE_CONFIG: RouteConfig[] = [
  {
    path: '/dashboard',
    title: '工作台',
    icon: 'dashboard',
    breadcrumb: ['工作台'],
  },
  {
    path: '/assets',
    title: '资产管理',
    icon: 'home',
    breadcrumb: ['资产管理'],
    children: [
      {
        path: ASSET_ROUTES.LIST,
        title: '资产列表',
        permissions: [{ resource: 'asset', action: 'view' }],
      },
      {
        path: ASSET_ROUTES.NEW,
        title: '创建资产',
        permissions: [{ resource: 'asset', action: 'create' }],
      },
      {
        path: ASSET_ROUTES.IMPORT,
        title: '资产导入',
        permissions: [{ resource: 'asset', action: 'import' }],
      },
      {
        path: ASSET_ROUTES.ANALYTICS,
        title: '资产分析',
        permissions: [{ resource: 'asset', action: 'view' }],
      },
    ],
  },
  {
    path: '/rental',
    title: '租赁管理',
    icon: 'bank',
    breadcrumb: ['租赁管理'],
    children: [
      {
        path: RENTAL_ROUTES.CONTRACTS.LIST,
        title: '合同列表',
        permissions: [{ resource: 'rental', action: 'view' }],
      },
      {
        path: RENTAL_ROUTES.CONTRACTS.NEW,
        title: '创建合同',
        permissions: [{ resource: 'rental', action: 'create' }],
      },
      {
        path: RENTAL_ROUTES.CONTRACTS.PDF_IMPORT,
        title: 'PDF导入合同',
        permissions: [{ resource: 'rental', action: 'create' }],
      },
      {
        path: RENTAL_ROUTES.LEDGER,
        title: '租金台账',
        permissions: [{ resource: 'rental', action: 'view' }],
      },
      {
        path: RENTAL_ROUTES.STATISTICS,
        title: '租赁统计',
        permissions: [{ resource: 'rental', action: 'view' }],
      },
    ],
  },
  {
    path: '/ownership',
    title: '权属方管理',
    icon: 'team',
    breadcrumb: ['权属方管理'],
  },
  {
    path: '/project',
    title: '项目管理',
    icon: 'project',
    breadcrumb: ['项目管理'],
  },
  {
    path: '/system',
    title: '系统管理',
    icon: 'setting',
    breadcrumb: ['系统管理'],
    children: [
      {
        path: SYSTEM_ROUTES.USERS,
        title: '用户管理',
        permissions: [{ resource: 'user', action: 'view' }],
      },
      {
        path: SYSTEM_ROUTES.ROLES,
        title: '角色管理',
        permissions: [{ resource: 'role', action: 'view' }],
      },
      {
        path: SYSTEM_ROUTES.ORGANIZATIONS,
        title: '组织架构',
        permissions: [{ resource: 'organization', action: 'view' }],
      },
      {
        path: SYSTEM_ROUTES.DICTIONARIES,
        title: '字典管理',
        permissions: [{ resource: 'system', action: 'dictionary' }],
      },
      {
        path: SYSTEM_ROUTES.TEMPLATES,
        title: '模板管理',
      },
      {
        path: SYSTEM_ROUTES.LOGS,
        title: '操作日志',
        permissions: [{ resource: 'system', action: 'logs' }],
      },
      {
        path: SYSTEM_ROUTES.SETTINGS,
        title: '系统设置',
      },
    ],
  },
];

// 导出所有路由常量
export const ROUTES = {
  BASE_PATHS,
  ASSET_ROUTES,
  RENTAL_ROUTES,
  SYSTEM_ROUTES,
  OTHER_ROUTES,
  REDIRECTS,
  NOT_FOUND_REDIRECT,
} as const;

// 类型导出
export type RoutePath = typeof ROUTES[keyof typeof ROUTES];