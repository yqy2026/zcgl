/**
 * 菜单配置
 *
 * v5 一次性切换后的菜单：资产运营 + 主体管理 + 系统管理。
 * 旧业务入口（工作台/资产台账/产权证/合同中心/经营台账/经营分析）已随
 * V1-4 切换移除，见 docs/archive/backend-plans/2026-10-23-asset-operations-v5-v1.md。
 */

import type { MenuProps } from 'antd';
import {
  SettingOutlined,
  UserOutlined,
  TeamOutlined,
  AuditOutlined,
  BookOutlined,
  ApartmentOutlined,
  FileTextOutlined,
  FileAddOutlined,
  DatabaseOutlined,
  SwapOutlined,
} from '@ant-design/icons';

export type MenuItemKey = string;

export interface MenuItemConfig {
  key: string;
  icon?: React.ReactNode;
  label: string;
  children?: MenuItemConfig[];
}

export const MENU_GROUP_KEYS = {
  ASSET_OPERATIONS: 'asset-operations-group',
} as const;

/**
 * 菜单项配置
 */
export const MENU_ITEMS: MenuProps['items'] = [
  {
    key: MENU_GROUP_KEYS.ASSET_OPERATIONS,
    icon: <DatabaseOutlined />,
    label: '资产运营',
    children: [
      {
        key: '/asset-operations/units',
        icon: <DatabaseOutlined />,
        label: '资产单元',
      },
      {
        key: '/asset-operations/contracts/intake',
        icon: <FileAddOutlined />,
        label: '录入已签合同',
      },
      {
        key: '/asset-operations/contracts/upstream',
        icon: <FileTextOutlined />,
        label: '上游合同',
      },
      {
        key: '/asset-operations/contracts/terminal',
        icon: <SwapOutlined />,
        label: '终端合同',
      },
    ],
  },
  {
    key: '/system/parties',
    icon: <TeamOutlined />,
    label: '主体管理',
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
  if (pathname.startsWith('/asset-operations/contracts/terminal')) {
    return ['/asset-operations/contracts/terminal'];
  }
  if (pathname.startsWith('/asset-operations/contracts/upstream')) {
    return ['/asset-operations/contracts/upstream'];
  }
  if (pathname.startsWith('/asset-operations/contracts/intake')) {
    return ['/asset-operations/contracts/intake'];
  }
  if (pathname.startsWith('/asset-operations/units')) {
    return ['/asset-operations/units'];
  }
  if (pathname.startsWith('/system/parties')) {
    return ['/system/parties'];
  }
  if (pathname.startsWith('/system')) {
    return [pathname];
  }
  return [pathname];
}

/**
 * 获取展开的菜单项
 */
export function getOpenKeys(pathname: string): string[] {
  if (pathname.startsWith('/asset-operations')) {
    return [MENU_GROUP_KEYS.ASSET_OPERATIONS];
  }
  if (pathname.startsWith('/system')) {
    return ['system'];
  }
  return [];
}

export function getMenuNavigationPath(key: string): string | undefined {
  return key.startsWith('/') ? key : undefined;
}
