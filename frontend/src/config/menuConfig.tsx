/**
 * 菜单配置
 *
 * 统一的菜单项配置，用于侧边栏和移动端菜单
 */

import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  HomeOutlined,
  SettingOutlined,
  UserOutlined,
  TeamOutlined,
  AuditOutlined,
  BookOutlined,
  ApartmentOutlined,
  FileTextOutlined,
  FileAddOutlined,
  BarChartOutlined,
  AccountBookOutlined,
  FileProtectOutlined,
} from '@ant-design/icons';

export type MenuItemKey = string;

export interface MenuItemConfig {
  key: string;
  icon?: React.ReactNode;
  label: string;
  children?: MenuItemConfig[];
}

export const MENU_GROUP_KEYS = {
  PROJECT: 'project-group',
  CONTRACT_CENTER: 'contract-center-group',
} as const;

export const MENU_ACTION_KEYS = {
  PROJECT_LIST: 'project:list',
  CONTRACT_CENTER_LIST: 'contract-center:list',
} as const;

const MENU_NAVIGATION_TARGETS: Record<string, string> = {
  [MENU_ACTION_KEYS.PROJECT_LIST]: '/project',
  [MENU_ACTION_KEYS.CONTRACT_CENTER_LIST]: '/contract-center',
};

/**
 * 菜单项配置
 */
export const MENU_ITEMS: MenuProps['items'] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '工作台',
  },
  {
    key: MENU_GROUP_KEYS.PROJECT,
    icon: <ApartmentOutlined />,
    label: '项目运营',
    children: [
      {
        key: MENU_ACTION_KEYS.PROJECT_LIST,
        icon: <ApartmentOutlined />,
        label: '项目列表',
      },
    ],
  },
  {
    key: '/asset-files',
    icon: <HomeOutlined />,
    label: '资产资源',
    children: [
      {
        key: '/assets/list',
        icon: <HomeOutlined />,
        label: '资产台账',
      },
      {
        key: '/property-certificates',
        icon: <FileProtectOutlined />,
        label: '产权证管理',
      },
      {
        key: '/system/templates',
        icon: <FileAddOutlined />,
        label: '数据模板',
      },
    ],
  },
  {
    key: MENU_GROUP_KEYS.CONTRACT_CENTER,
    icon: <FileTextOutlined />,
    label: '合同中心',
    children: [
      {
        key: MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
        icon: <FileTextOutlined />,
        label: '合同关系列表',
      },
      {
        key: '/contract-center/import',
        icon: <FileAddOutlined />,
        label: 'PDF导入',
      },
    ],
  },
  {
    key: '/operations/ledger',
    icon: <AccountBookOutlined />,
    label: '经营台账',
  },
  {
    key: '/customer-center',
    icon: <TeamOutlined />,
    label: '主体中心',
    children: [
      {
        key: '/system/parties',
        icon: <TeamOutlined />,
        label: '主体管理',
      },
    ],
  },
  {
    key: '/analytics',
    icon: <BarChartOutlined />,
    label: '经营分析',
  },
  {
    key: 'system',
    icon: <SettingOutlined />,
    label: '系统管理',
    children: [
      {
        key: '/system/users',
        icon: <UserOutlined />,
        label: '用户管理',
      },
      {
        key: '/system/roles',
        icon: <TeamOutlined />,
        label: '角色管理',
      },
      {
        key: '/system/organizations',
        icon: <ApartmentOutlined />,
        label: '组织架构',
      },
      {
        key: '/system/dictionaries',
        icon: <BookOutlined />,
        label: '字典管理',
      },
      {
        key: '/system/settings',
        icon: <SettingOutlined />,
        label: '系统设置',
      },
      {
        key: '/system/logs',
        icon: <AuditOutlined />,
        label: '操作日志',
      },
      {
        key: '/system/data-policies',
        icon: <FileTextOutlined />,
        label: '数据策略包',
      },
    ],
  },
];

/**
 * 获取当前选中的菜单项
 */
export function getSelectedKeys(pathname: string): string[] {
  // 精确匹配
  if (pathname === '/') {
    return ['/dashboard'];
  }

  if (pathname === '/analytics' || pathname.startsWith('/analytics/')) {
    return ['/analytics'];
  }
  if (pathname === '/contract-center' || pathname.startsWith('/contract-center/')) {
    if (pathname === '/contract-center/import') {
      return ['/contract-center/import'];
    }
    return [MENU_ACTION_KEYS.CONTRACT_CENTER_LIST];
  }
  if (pathname.startsWith('/assets/')) {
    return ['/assets/list'];
  }
  if (pathname === '/property-certificates' || pathname.startsWith('/property-certificates/')) {
    return ['/property-certificates'];
  }
  if (pathname.startsWith('/contract-groups/')) {
    return [MENU_ACTION_KEYS.CONTRACT_CENTER_LIST];
  }
  if (pathname === '/operations/ledger' || pathname.startsWith('/operations/ledger/')) {
    return ['/operations/ledger'];
  }
  if (pathname === '/project' || pathname.startsWith('/project/')) {
    return [MENU_ACTION_KEYS.PROJECT_LIST];
  }

  if (pathname.startsWith('/contract-groups')) {
    return [MENU_ACTION_KEYS.CONTRACT_CENTER_LIST];
  }
  if (pathname.startsWith('/system/parties')) {
    return ['/system/parties'];
  }

  return [pathname];
}

/**
 * 获取展开的菜单项
 */
export function getOpenKeys(pathname: string): string[] {
  if (pathname.startsWith('/project')) {
    return [MENU_GROUP_KEYS.PROJECT];
  }
  if (pathname.startsWith('/assets')) {
    return ['/asset-files'];
  }
  if (pathname.startsWith('/property-certificates')) {
    return ['/asset-files'];
  }
  if (pathname.startsWith('/contract-groups')) {
    return [MENU_GROUP_KEYS.CONTRACT_CENTER];
  }
  if (pathname.startsWith('/contract-center')) {
    return [MENU_GROUP_KEYS.CONTRACT_CENTER];
  }
  if (pathname.startsWith('/system/parties')) {
    return ['/customer-center'];
  }
  if (pathname.startsWith('/analytics')) {
    return [];
  }
  if (pathname.startsWith('/finance')) {
    return [];
  }
  // 数据模板菜单已迁移至资产资源（#79），URL 仍为 /system/templates
  if (pathname === '/system/templates' || pathname.startsWith('/system/templates/')) {
    return ['/asset-files'];
  }
  if (pathname.startsWith('/system')) {
    return ['system'];
  }

  return [];
}

export function getMenuNavigationPath(key: string): string | undefined {
  if (MENU_NAVIGATION_TARGETS[key] != null) {
    return MENU_NAVIGATION_TARGETS[key];
  }
  return key.startsWith('/') ? key : undefined;
}
