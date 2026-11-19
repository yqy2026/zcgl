/**
 * 菜单配置
 *
 * 对齐原型 asset-ops-v5 侧栏：本月（徽标=未完成件数）/ 报送 / 物业 /
 * 合同（分组标题，不可点：上游合同、终端合同）/ 台账 / 档案（红字 缺 N 份）/
 * 数据导入。「录入已签合同」不占菜单位——原型从合同页「＋ 录入已签合同」
 * 按钮进入（路由保留）。徽标由 AppSidebar 组合渲染。
 */

import type { MenuProps } from 'antd';
import {
  SettingOutlined,
  UserOutlined,
  TeamOutlined,
  AuditOutlined,
  BookOutlined,
  ApartmentOutlined,
  FileDoneOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  SwapOutlined,
  CalendarOutlined,
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
  CONTRACTS: 'asset-operations-contracts',
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
        key: '/asset-operations/monthly',
        icon: <CalendarOutlined />,
        label: '本月',
      },
      {
        key: '/asset-operations/occupancy-reports',
        icon: <FileDoneOutlined />,
        label: '报送',
      },
      {
        key: '/asset-operations/units',
        icon: <DatabaseOutlined />,
        label: '物业',
      },
      {
        key: MENU_GROUP_KEYS.CONTRACTS,
        type: 'group',
        label: '合同',
        children: [
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
        key: '/asset-operations/ledgers',
        icon: <BookOutlined />,
        label: '台账',
      },
      {
        key: '/asset-operations/archive',
        icon: <FileTextOutlined />,
        label: '档案',
      },
      {
        key: '/asset-operations/imports',
        icon: <FileTextOutlined />,
        label: '数据导入',
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
    // 录入页从合同页按钮进入，返回时高亮来源不确定，默认高亮上游合同。
    return ['/asset-operations/contracts/upstream'];
  }
  if (pathname.startsWith('/asset-operations/occupancy-reports')) {
    return ['/asset-operations/occupancy-reports'];
  }
  if (pathname.startsWith('/asset-operations/monthly')) {
    return ['/asset-operations/monthly'];
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
