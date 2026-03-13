/**
 * 路由常量定义
 * 统一路由命名规范，使用 kebab-case
 */

// 基础路径常量
export const BASE_PATHS = {
  DASHBOARD: '/dashboard',
  ASSETS: '/assets',
  CONTRACT_GROUPS: '/contract-groups',
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
  ANALYTICS_SIMPLE: '/assets/analytics-simple',
  DETAIL_PATH: '/assets/:id',
  EDIT_PATH: '/assets/:id/edit',
  DETAIL: (id: string) => `/assets/${id}`,
  EDIT: (id: string) => `/assets/${id}/edit`,
} as const;

// 已退休旧租赁路由
export const LEGACY_RENTAL_ROUTES = {
  CONTRACTS: {
    LIST: '/rental/contracts',
    NEW: '/rental/contracts/new',
    CREATE: '/rental/contracts/create',
    PDF_IMPORT: '/rental/contracts/pdf-import',
    DETAIL_PATH: '/rental/contracts/:id',
    EDIT_PATH: '/rental/contracts/:id/edit',
    RENEW_PATH: '/rental/contracts/:id/renew',
    DETAIL: (id: string) => `/rental/contracts/${id}`,
    EDIT: (id: string) => `/rental/contracts/${id}/edit`,
    RENEW: (id: string) => `/rental/contracts/${id}/renew`,
  },
  LEDGER: '/rental/ledger',
  STATISTICS: '/rental/statistics',
} as const;

export const CONTRACT_GROUP_ROUTES = {
  LIST: '/contract-groups',
  NEW: '/contract-groups/new',
  IMPORT: '/contract-groups/import',
  DETAIL_PATH: '/contract-groups/:id',
  EDIT_PATH: '/contract-groups/:id/edit',
  DETAIL: (id: string) => `/contract-groups/${id}`,
  EDIT: (id: string) => `/contract-groups/${id}/edit`,
} as const;

// 系统管理路由
export const SYSTEM_ROUTES = {
  PARTIES: '/system/parties',
  PARTY_DETAIL_PATH: '/system/parties/:id',
  PARTY_DETAIL: (id: string) => `/system/parties/${id}`,
  USERS: '/system/users',
  ROLES: '/system/roles',
  ORGANIZATIONS: '/system/organizations',
  DICTIONARIES: '/system/dictionaries',
  TEMPLATES: '/system/templates',
  LOGS: '/system/logs',
  SETTINGS: '/system/settings',
  DATA_POLICIES: '/system/data-policies',
} as const;

// 其他模块路由
export const OTHER_ROUTES = {
  OWNERSHIP: '/ownership',
  PROJECT: '/project',
} as const;

export const OWNERSHIP_ROUTES = {
  LIST: '/ownership',
  DETAIL_PATH: '/ownership/:id',
  EDIT_PATH: '/ownership/:id/edit',
  DETAIL: (id: string) => `/ownership/${id}`,
  EDIT: (id: string) => `/ownership/${id}/edit`,
} as const;

export const PROJECT_ROUTES = {
  LIST: '/project',
  DETAIL_PATH: '/project/:id',
  EDIT_PATH: '/project/:id/edit',
  DETAIL: (id: string) => `/project/${id}`,
  EDIT: (id: string) => `/project/${id}/edit`,
} as const;

export const PROFILE_ROUTES = {
  PROFILE: '/profile',
} as const;

export const PROPERTY_CERTIFICATE_ROUTES = {
  LIST: '/property-certificates',
  IMPORT: '/property-certificates/import',
  DETAIL_PATH: '/property-certificates/:id',
  DETAIL: (id: string) => `/property-certificates/${id}`,
} as const;

const LEGACY_RENTAL_RETIRED_TITLE = '旧租赁前端已退休';

// 页面重定向配置
export const REDIRECTS = {
  ROOT: '/dashboard',
  ASSETS_ROOT: '/assets/list',
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

const LEGACY_RENTAL_PDF_IMPORT_REDIRECT_TITLE = '跳转至PDF导入';

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
        permissions: [{ resource: 'asset', action: 'read' }],
      },
      {
        path: ASSET_ROUTES.NEW,
        title: '创建资产',
        permissions: [{ resource: 'asset', action: 'create' }],
      },
      {
        path: ASSET_ROUTES.IMPORT,
        title: '资产导入',
        permissions: [{ resource: 'asset', action: 'create' }],
      },
      {
        path: ASSET_ROUTES.ANALYTICS,
        title: '资产分析',
        permissions: [{ resource: 'analytics', action: 'read' }],
      },
      {
        path: ASSET_ROUTES.ANALYTICS_SIMPLE,
        title: '简易分析',
        permissions: [{ resource: 'analytics', action: 'read' }],
      },
      {
        path: ASSET_ROUTES.DETAIL_PATH,
        title: '资产详情',
        permissions: [{ resource: 'asset', action: 'read' }],
      },
    ],
  },
  {
    path: '/rental',
    title: LEGACY_RENTAL_RETIRED_TITLE,
    icon: 'bank',
    breadcrumb: [LEGACY_RENTAL_RETIRED_TITLE],
    children: [
      {
        path: LEGACY_RENTAL_ROUTES.CONTRACTS.LIST,
        title: LEGACY_RENTAL_RETIRED_TITLE,
        permissions: [{ resource: 'contract', action: 'read' }],
      },
      {
        path: LEGACY_RENTAL_ROUTES.CONTRACTS.NEW,
        title: LEGACY_RENTAL_RETIRED_TITLE,
        permissions: [{ resource: 'contract', action: 'read' }],
      },
      {
        path: LEGACY_RENTAL_ROUTES.CONTRACTS.CREATE,
        title: LEGACY_RENTAL_RETIRED_TITLE,
        permissions: [{ resource: 'contract', action: 'read' }],
      },
      {
        path: LEGACY_RENTAL_ROUTES.CONTRACTS.PDF_IMPORT,
        title: LEGACY_RENTAL_PDF_IMPORT_REDIRECT_TITLE,
        permissions: [{ resource: 'contract_group', action: 'create' }],
      },
      {
        path: LEGACY_RENTAL_ROUTES.CONTRACTS.RENEW_PATH,
        title: LEGACY_RENTAL_RETIRED_TITLE,
        permissions: [{ resource: 'contract', action: 'read' }],
      },
      {
        path: LEGACY_RENTAL_ROUTES.CONTRACTS.DETAIL_PATH,
        title: LEGACY_RENTAL_RETIRED_TITLE,
        permissions: [{ resource: 'contract', action: 'read' }],
      },
      {
        path: LEGACY_RENTAL_ROUTES.CONTRACTS.EDIT_PATH,
        title: LEGACY_RENTAL_RETIRED_TITLE,
        permissions: [{ resource: 'contract', action: 'read' }],
      },
      {
        path: LEGACY_RENTAL_ROUTES.LEDGER,
        title: LEGACY_RENTAL_RETIRED_TITLE,
        permissions: [{ resource: 'contract', action: 'read' }],
      },
      {
        path: LEGACY_RENTAL_ROUTES.STATISTICS,
        title: LEGACY_RENTAL_RETIRED_TITLE,
        permissions: [{ resource: 'contract', action: 'read' }],
      },
    ],
  },
  {
    path: CONTRACT_GROUP_ROUTES.LIST,
    title: '合同组管理',
    icon: 'file-text',
    breadcrumb: ['合同组管理'],
    children: [
      {
        path: CONTRACT_GROUP_ROUTES.LIST,
        title: '合同组列表',
        permissions: [{ resource: 'contract_group', action: 'read' }],
      },
      {
        path: CONTRACT_GROUP_ROUTES.NEW,
        title: '新建合同组',
        permissions: [{ resource: 'contract_group', action: 'create' }],
      },
      {
        path: CONTRACT_GROUP_ROUTES.IMPORT,
        title: 'PDF导入',
        permissions: [{ resource: 'contract_group', action: 'create' }],
      },
      {
        path: CONTRACT_GROUP_ROUTES.DETAIL_PATH,
        title: '合同组详情',
        permissions: [{ resource: 'contract_group', action: 'read' }],
      },
      {
        path: CONTRACT_GROUP_ROUTES.EDIT_PATH,
        title: '编辑合同组',
        permissions: [{ resource: 'contract_group', action: 'update' }],
      },
    ],
  },
  {
    path: '/ownership',
    title: '权属方管理',
    icon: 'team',
    breadcrumb: ['权属方管理'],
    children: [
      {
        path: OWNERSHIP_ROUTES.LIST,
        title: '权属方列表',
        permissions: [{ resource: 'ownership', action: 'read' }],
      },
      {
        path: OWNERSHIP_ROUTES.DETAIL_PATH,
        title: '权属方详情',
        permissions: [{ resource: 'ownership', action: 'read' }],
      },
      {
        path: OWNERSHIP_ROUTES.EDIT_PATH,
        title: '编辑权属方',
        permissions: [{ resource: 'ownership', action: 'update' }],
      },
    ],
  },
  {
    path: '/project',
    title: '项目管理',
    icon: 'project',
    breadcrumb: ['项目管理'],
    children: [
      {
        path: PROJECT_ROUTES.LIST,
        title: '项目列表',
        permissions: [{ resource: 'project', action: 'read' }],
      },
      {
        path: PROJECT_ROUTES.DETAIL_PATH,
        title: '项目详情',
        permissions: [{ resource: 'project', action: 'read' }],
      },
      {
        path: PROJECT_ROUTES.EDIT_PATH,
        title: '编辑项目',
        permissions: [{ resource: 'project', action: 'update' }],
      },
    ],
  },
  {
    path: PROPERTY_CERTIFICATE_ROUTES.LIST,
    title: '产权证管理',
    icon: 'file-text',
    breadcrumb: ['产权证管理'],
    children: [
      {
        path: PROPERTY_CERTIFICATE_ROUTES.LIST,
        title: '产权证列表',
        permissions: [{ resource: 'property_certificate', action: 'read' }],
      },
      {
        path: PROPERTY_CERTIFICATE_ROUTES.IMPORT,
        title: '产权证导入',
        permissions: [{ resource: 'property_certificate', action: 'create' }],
      },
      {
        path: PROPERTY_CERTIFICATE_ROUTES.DETAIL_PATH,
        title: '产权证详情',
        permissions: [{ resource: 'property_certificate', action: 'read' }],
      },
    ],
  },
  {
    path: PROFILE_ROUTES.PROFILE,
    title: '个人中心',
  },
  {
    path: '/system',
    title: '系统管理',
    icon: 'setting',
    breadcrumb: ['系统管理'],
    children: [
      {
        path: SYSTEM_ROUTES.PARTIES,
        title: '主体管理',
        permissions: [{ resource: 'party', action: 'read' }],
      },
      {
        path: SYSTEM_ROUTES.PARTY_DETAIL_PATH,
        title: '主体详情',
        permissions: [{ resource: 'party', action: 'read' }],
      },
      {
        path: SYSTEM_ROUTES.USERS,
        title: '用户管理',
        permissions: [{ resource: 'user', action: 'read' }],
      },
      {
        path: SYSTEM_ROUTES.ROLES,
        title: '角色管理',
        permissions: [{ resource: 'role', action: 'read' }],
      },
      {
        path: SYSTEM_ROUTES.ORGANIZATIONS,
        title: '组织架构',
        permissions: [{ resource: 'organization', action: 'read' }],
      },
      {
        path: SYSTEM_ROUTES.DICTIONARIES,
        title: '字典管理',
        permissions: [{ resource: 'dictionary', action: 'read' }],
      },
      {
        path: SYSTEM_ROUTES.TEMPLATES,
        title: '模板管理',
        permissions: [{ resource: 'llm_prompt', action: 'read' }],
      },
      {
        path: SYSTEM_ROUTES.LOGS,
        title: '操作日志',
        permissions: [{ resource: 'operation_log', action: 'read' }],
      },
      {
        path: SYSTEM_ROUTES.SETTINGS,
        title: '系统设置',
        permissions: [
          { resource: 'system_settings', action: 'read' },
          { resource: 'system_settings', action: 'update' },
        ],
      },
      {
        path: SYSTEM_ROUTES.DATA_POLICIES,
        title: '数据策略包',
        permissions: [{ resource: 'role', action: 'update' }],
      },
    ],
  },
];

// 导出所有路由常量
export const ROUTES = {
  BASE_PATHS,
  ASSET_ROUTES,
  LEGACY_RENTAL_ROUTES,
  CONTRACT_GROUP_ROUTES,
  SYSTEM_ROUTES,
  OTHER_ROUTES,
  OWNERSHIP_ROUTES,
  PROJECT_ROUTES,
  PROFILE_ROUTES,
  PROPERTY_CERTIFICATE_ROUTES,
  REDIRECTS,
  NOT_FOUND_REDIRECT,
} as const;

// 类型导出
export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES];
