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
    key: '/owner',
    icon: <HomeOutlined />,
    label: '业主视角',
    children: [
      {
        key: '/owner/assets',
        icon: <UnorderedListOutlined />,
        label: '业主资产',
      },
      {
        key: '/owner/contract-groups',
        icon: <FileTextOutlined />,
        label: '业主合同组',
      },
      {
        key: '/ownership',
        icon: <IdcardOutlined />,
        label: '权属方管理',
      },
      {
        key: '/owner/property-certificates',
        icon: <FileTextOutlined />,
        label: '产权证管理',
      },
    ],
  },
  {
    key: '/manager',
    icon: <AppstoreOutlined />,
    label: '经营视角',
    children: [
      {
        key: '/manager/assets',
        icon: <HomeOutlined />,
        label: '经营资产',
      },
      {
        key: '/manager/contract-groups',
        icon: <FileTextOutlined />,
        label: '经营合同组',
      },
      {
        key: '/manager/projects',
        icon: <AppstoreOutlined />,
        label: '经营项目',
      },
    ],
  },
  {
    key: 'rental',
    icon: <AccountBookOutlined />,
    label: '旧租赁前端已退休',
    children: [
      {
        key: '/rental/contracts',
        icon: <FileTextOutlined />,
        label: '旧租赁前端已退休',
      },
    ],
  },
  {
    key: 'system',
    icon: <SettingOutlined />,
    label: '系统管理',
    children: [
      {
        key: '/system/parties',
        icon: <IdcardOutlined />,
        label: '主体管理',
      },
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

  if (pathname.startsWith('/owner/assets/')) {
    return ['/owner/assets'];
  }
  if (pathname.startsWith('/owner/contract-groups/')) {
    return ['/owner/contract-groups'];
  }
  if (pathname.startsWith('/owner/property-certificates/')) {
    return ['/owner/property-certificates'];
  }
  if (pathname.startsWith('/manager/assets/')) {
    return ['/manager/assets'];
  }
  if (pathname.startsWith('/manager/contract-groups/')) {
    return ['/manager/contract-groups'];
  }
  if (pathname.startsWith('/manager/projects/')) {
    return ['/manager/projects'];
  }

  // 权属方管理页面
  if (pathname === '/ownership') {
    return ['/ownership'];
  }
  if (pathname.startsWith('/property-certificates')) {
    return [];
  }
  if (pathname.startsWith('/contract-groups')) {
    return [];
  }
  if (pathname === '/rental/contracts/pdf-import') {
    return [];
  }
  if (pathname.startsWith('/rental')) {
    return ['/rental/contracts'];
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
  if (pathname.startsWith('/owner/')) {
    return ['/owner'];
  }
  if (pathname === '/ownership') {
    return ['/owner'];
  }
  if (pathname.startsWith('/owner/property-certificates')) {
    return ['/owner'];
  }
  if (pathname.startsWith('/manager/')) {
    return ['/manager'];
  }
  if (pathname.startsWith('/rental')) {
    return ['rental'];
  }
  if (pathname.startsWith('/system')) {
    return ['system'];
  }

  return [];
}
