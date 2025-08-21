import React from 'react'
import { Layout, Menu, Typography } from 'antd'
import {
  DashboardOutlined,
  HomeOutlined,
  SearchOutlined,
  FileExcelOutlined,
  BarChartOutlined,
  SettingOutlined,
  PlusOutlined,
  UnorderedListOutlined,
  UploadOutlined,
  DownloadOutlined,
  LineChartOutlined,
  PieChartOutlined,
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
          key: '/assets',
          icon: <UnorderedListOutlined />,
          label: '资产列表',
        },
        {
          key: '/assets/new',
          icon: <PlusOutlined />,
          label: '新增资产',
        },
        {
          key: '/assets/search',
          icon: <SearchOutlined />,
          label: '高级搜索',
        },
      ],
    },
    {
      key: 'data',
      icon: <FileExcelOutlined />,
      label: '数据管理',
      children: [
        {
          key: '/data/import',
          icon: <UploadOutlined />,
          label: '数据导入',
        },
        {
          key: '/data/export',
          icon: <DownloadOutlined />,
          label: '数据导出',
        },
        {
          key: '/data/import-export',
          icon: <FileExcelOutlined />,
          label: '导入导出',
        },
      ],
    },
    {
      key: 'analytics',
      icon: <BarChartOutlined />,
      label: '数据分析',
      children: [
        {
          key: '/analytics/occupancy',
          icon: <LineChartOutlined />,
          label: '出租率分析',
        },
        {
          key: '/analytics/distribution',
          icon: <PieChartOutlined />,
          label: '资产分布',
        },
        {
          key: '/analytics/area',
          icon: <BarChartOutlined />,
          label: '面积统计',
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
          icon: <SettingOutlined />,
          label: '用户管理',
        },
        {
          key: '/system/roles',
          icon: <SettingOutlined />,
          label: '角色管理',
        },
        {
          key: '/system/logs',
          icon: <SettingOutlined />,
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
    
    return [pathname]
  }

  // 获取展开的菜单项
  const getOpenKeys = () => {
    const pathname = location.pathname
    
    if (pathname.startsWith('/assets')) return ['assets']
    if (pathname.startsWith('/data')) return ['data']
    if (pathname.startsWith('/analytics')) return ['analytics']
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