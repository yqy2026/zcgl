import React from 'react'
import { Layout, Menu, Typography } from 'antd'
import {
  DashboardOutlined,
  HomeOutlined,
  BarChartOutlined,
  SettingOutlined,
  PlusOutlined,
  UnorderedListOutlined,
  UploadOutlined,
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
} from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'
import type { MenuProps } from 'antd'

const { Sider } = Layout
const { Text } = Typography

interface AppSidebarProps {
  collapsed: boolean
}

const AppSidebar: React.FC<AppSidebarProps> = ({ collapsed }) => {
  const location = useLocation()
  const navigate = useNavigate()

  // 菜单项配置
  const menuItems: MenuProps['items'] = [
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
          key: '/assets/new',
          icon: <PlusOutlined />,
          label: '新增资产',
        },
        {
          key: '/assets/import',
          icon: <UploadOutlined />,
          label: '数据导入',
        },
        {
          key: '/assets/analytics',
          icon: <BarChartOutlined />,
          label: '数据分析',
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
          key: '/rental/contracts/new',
          icon: <PlusOutlined />,
          label: '新建合同',
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
  ]

  // 获取当前选中的菜单项
  const getSelectedKeys = () => {
    const pathname = location.pathname

    // 精确匹配
    if (pathname === '/') return ['/dashboard']

    // 资产详情页面特殊处理
    if (pathname.match(/^\/assets\/\d+$/)) return ['/assets']
    if (pathname.match(/^\/assets\/\d+\/edit$/)) return ['/assets']

    // 权属方管理页面
    if (pathname === '/ownership') return ['/ownership']

    return [pathname]
  }

  // 获取展开的菜单项
  const getOpenKeys = () => {
    const pathname = location.pathname

    if (pathname.startsWith('/assets') && !pathname.startsWith('/assets/list')) return ['assets']
    if (pathname.startsWith('/rental')) return ['rental']
    if (pathname.startsWith('/system')) return ['system']

    return []
  }

  // 处理菜单点击
  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Sider
      trigger={null}
      collapsible
      collapsed={collapsed}
      width={240}
      style={{
        background: '#001529',
        borderRight: '1px solid #f0f0f0',
      }}
    >
      {/* Logo区域 */}
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 24px',
          background: '#002140',
          borderBottom: '1px solid #1f1f1f',
        }}
      >
        {collapsed ? (
          <HomeOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
        ) : (
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <HomeOutlined style={{ fontSize: '24px', color: '#1890ff', marginRight: 12 }} />
            <Text strong style={{ color: '#fff', fontSize: '16px' }}>
              资产管理
            </Text>
          </div>
        )}
      </div>

      {/* 菜单 */}
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={getSelectedKeys()}
        defaultOpenKeys={getOpenKeys()}
        items={menuItems}
        onClick={handleMenuClick}
        style={{
          borderRight: 0,
          background: '#001529',
        }}
      />
    </Sider>
  )
}

export default AppSidebar