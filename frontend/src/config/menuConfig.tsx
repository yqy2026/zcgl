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
    label: '工作台',
  },
  {
    key: '/project',
    icon: <ApartmentOutlined />,
    label: '项目运营',
    children: [
      {
        key: '/project',
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
    ],
  },
  {
    key: '/contract-center',
    icon: <FileTextOutlined />,
    label: '合同中心',
    children: [
      {
        key: '/contract-center/import',
        icon: <FileAddOutlined />,
        label: 'PDF导入',
      },
    ],
  },
  {
    key: '/finance/ledger',
    icon: <AccountBookOutlined />,
    label: '财务台账',
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
        key: '/system/templates',
        icon: <FileAddOutlined />,
        label: '数据模板',
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
    return ['/contract-center'];
  }
  if (pathname.startsWith('/assets/')) {
    return ['/assets/list'];
  }
  if (pathname.startsWith('/contract-groups/')) {
    return ['/contract-center'];
  }
  if (pathname === '/finance/ledger' || pathname.startsWith('/finance/ledger/')) {
    return ['/finance/ledger'];
  }
  if (pathname.startsWith('/project/')) {
    return ['/project'];
  }

  if (pathname.startsWith('/contract-groups')) {
    return ['/contract-center'];
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
    return ['/project'];
  }
  if (pathname.startsWith('/assets')) {
    return ['/asset-files'];
  }
  if (pathname.startsWith('/contract-groups')) {
    return ['/contract-center'];
  }
  if (pathname.startsWith('/contract-center')) {
    return ['/contract-center'];
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
  if (pathname.startsWith('/system')) {
    return ['system'];
  }

  return [];
}
