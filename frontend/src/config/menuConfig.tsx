/**
 * 菜单配置
 *
 * 统一的菜单项配置，用于侧边栏和移动端菜单
 */

import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  HomeOutlined,
  BarChartOutlined,
  SettingOutlined,
  UnorderedListOutlined,
  UserOutlined,
  TeamOutlined,
  AuditOutlined,
  BookOutlined,
  ApartmentOutlined,
  IdcardOutlined,
  AccountBookOutlined,
  FileTextOutlined,
  AppstoreOutlined,
  FileAddOutlined,
} from '@ant-design/icons';

export type MenuItemKey = string;

export interface MenuItemConfig {
  key: string;
  icon?: React.ReactNode;
  label: string;
  children?: MenuItemConfig[];
}

/**
 * 菜单项配置
 */
export const MENU_ITEMS: MenuProps['items'] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '数据看板',
  },
  {
    key: 'assets',
    icon: <HomeOutlined />,
    label: '资产管理',
    children: [
      {
        key: '/assets/list',
        icon: <UnorderedListOutlined />,
        label: '资产列表',
      },
      {
        key: '/assets/analytics',
        icon: <BarChartOutlined />,
        label: '数据分析',
      },
      {
        key: '/property-certificates',
        icon: <FileTextOutlined />,
        label: '产权证管理',
      },
    ],
  },
  {
    key: '/ownership',
    icon: <IdcardOutlined />,
    label: '权属方管理',
  },
  {
    key: '/project',
    icon: <AppstoreOutlined />,
    label: '项目管理',
  },
  {
    key: 'rental',
    icon: <AccountBookOutlined />,
    label: '租赁管理',
    children: [
      {
        key: '/rental/contracts',
        icon: <UnorderedListOutlined />,
        label: '合同列表',
      },
      {
        key: '/rental/contracts/pdf-import',
        icon: <FileTextOutlined />,
        label: 'PDF智能导入',
      },
      {
        key: '/rental/ledger',
        icon: <AccountBookOutlined />,
        label: '租金台账',
      },
      {
        key: '/rental/statistics',
        icon: <BarChartOutlined />,
        label: '统计报表',
      },
    ],
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
        key: '/system/templates',
        icon: <FileAddOutlined />,
        label: '数据模板',
      },
      {
        key: '/system/logs',
        icon: <AuditOutlined />,
        label: '操作日志',
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

  // 资产详情页面特殊处理
  if (pathname.match(/^\/assets\/\d+$/)) {
    return ['/assets/list'];
  }
  if (pathname.match(/^\/assets\/\d+\/edit$/)) {
    return ['/assets/list'];
  }

  // 权属方管理页面
  if (pathname === '/ownership') {
    return ['/ownership'];
  }
  if (pathname.startsWith('/property-certificates')) {
    return ['/property-certificates'];
  }

  return [pathname];
}

/**
 * 获取展开的菜单项
 */
export function getOpenKeys(pathname: string): string[] {
  if (pathname.startsWith('/assets')) {
    return ['assets'];
  }
  if (pathname.startsWith('/property-certificates')) {
    return ['assets'];
  }
  if (pathname.startsWith('/rental')) {
    return ['rental'];
  }
  if (pathname.startsWith('/system')) {
    return ['system'];
  }

  return [];
}
