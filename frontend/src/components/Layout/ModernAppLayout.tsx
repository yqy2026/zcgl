import React, { useState } from 'react'
import { 
  Layout, 
  Menu, 
  Avatar, 
  Dropdown, 
  Space, 
  Typography, 
  Badge, 
  Button,
  Divider,
  Tooltip,
  theme
} from 'antd'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  BuildOutlined as BuildingOutlined,
  PlusOutlined,
  SearchOutlined,
  FileExcelOutlined,
  BarChartOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined,
  QuestionCircleOutlined,
  HomeOutlined,
  AppstoreOutlined,
  DatabaseOutlined,
  LineChartOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { useLocation, useNavigate, Outlet } from 'react-router-dom'
import type { MenuProps } from 'antd'

const { Header, Sider, Content } = Layout
const { Text, Title } = Typography

const ModernAppLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { token } = theme.useToken()

  // 现代化的菜单项
  const menuItems: MenuProps['items'] = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表板',
      onClick: () => window.open('/dashboard', '_blank'),
    },
    {
      type: 'divider',
    },
    {
      key: 'assets-group',
      label: '资产管理',
      type: 'group',
    },
    {
      key: '/assets',
      icon: <BuildingOutlined />,
      label: '资产列表',
      onClick: () => window.open('/assets', '_blank'),
    },
    {
      key: '/assets/new',
      icon: <PlusOutlined />,
      label: '新增资产',
      onClick: () => window.open('/assets/new', '_blank'),
    },
    {
      key: '/assets/search',
      icon: <SearchOutlined />,
      label: '高级搜索',
      onClick: () => window.open('/assets/search', '_blank'),
    },
    {
      type: 'divider',
    },
    {
      key: 'data-group',
      label: '数据管理',
      type: 'group',
    },
    {
      key: '/import-export',
      icon: <FileExcelOutlined />,
      label: '导入导出',
      onClick: () => window.open('/import-export', '_blank'),
    },
    {
      key: '/analytics',
      icon: <LineChartOutlined />,
      label: '数据分析',
      onClick: () => window.open('/analytics', '_blank'),
    },
    {
      key: '/reports',
      icon: <BarChartOutlined />,
      label: '报表中心',
      onClick: () => window.open('/reports', '_blank'),
    },
  ]

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'help',
      icon: <QuestionCircleOutlined />,
      label: '帮助中心',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ]

  // 获取当前页面标题
  const getPageTitle = () => {
    const path = location.pathname
    if (path === '/' || path === '/dashboard') return '仪表板'
    if (path === '/assets') return '资产列表'
    if (path === '/assets/new') return '新增资产'
    if (path.includes('/assets/') && path.includes('/edit')) return '编辑资产'
    if (path.includes('/assets/')) return '资产详情'
    if (path === '/import-export') return '导入导出'
    if (path === '/analytics') return '数据分析'
    if (path === '/reports') return '报表中心'
    return '土地物业资产管理系统'
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 现代化侧边栏 */}
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        width={280}
        style={{
          background: '#fff',
          borderRight: `1px solid ${token.colorBorderSecondary}`,
          boxShadow: '2px 0 8px 0 rgba(29,35,41,.05)',
        }}
      >
        {/* Logo区域 */}
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 24px',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}>
            <div style={{
              width: 32,
              height: 32,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: 16,
              fontWeight: 'bold',
            }}>
              <AppstoreOutlined />
            </div>
            {!collapsed && (
              <div>
                <Title level={5} style={{ margin: 0, color: token.colorText }}>
                  资产管理
                </Title>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Asset Management
                </Text>
              </div>
            )}
          </div>
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          style={{
            border: 'none',
            background: 'transparent',
            padding: '16px 8px',
          }}
        />

        {/* 底部用户信息（收起时隐藏） */}
        {!collapsed && (
          <div style={{
            position: 'absolute',
            bottom: 16,
            left: 16,
            right: 16,
            padding: 16,
            background: token.colorBgContainer,
            borderRadius: 8,
            border: `1px solid ${token.colorBorderSecondary}`,
          }}>
            <Space>
              <Avatar size="small" icon={<UserOutlined />} />
              <div>
                <Text strong style={{ fontSize: 14 }}>管理员</Text>
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>在线</Text>
              </div>
            </Space>
          </div>
        )}
      </Sider>

      <Layout>
        {/* 现代化头部 */}
        <Header style={{
          padding: '0 24px',
          background: '#fff',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 4px 0 rgba(0,21,41,.08)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: 16,
                width: 40,
                height: 40,
              }}
            />
            
            <Divider type="vertical" style={{ height: 24 }} />
            
            <div>
              <Title level={4} style={{ margin: 0 }}>
                {getPageTitle()}
              </Title>
            </div>
          </div>

          <Space size="middle">
            {/* 快速操作 */}
            <Tooltip title="新增资产">
              <Button 
                type="primary" 
                icon={<PlusOutlined />}
                onClick={() => window.open('/assets/new', '_blank')}
                style={{
                  borderRadius: 8,
                  boxShadow: '0 2px 4px rgba(24,144,255,0.2)',
                }}
              >
                新增资产
              </Button>
            </Tooltip>

            <Divider type="vertical" style={{ height: 24 }} />

            {/* 通知 */}
            <Tooltip title="通知">
              <Badge count={3} size="small">
                <Button 
                  type="text" 
                  icon={<BellOutlined />}
                  style={{ fontSize: 16 }}
                />
              </Badge>
            </Tooltip>

            {/* 帮助 */}
            <Tooltip title="帮助">
              <Button 
                type="text" 
                icon={<QuestionCircleOutlined />}
                style={{ fontSize: 16 }}
              />
            </Tooltip>

            {/* 用户菜单 */}
            <Dropdown 
              menu={{ items: userMenuItems }} 
              placement="bottomRight"
              arrow
            >
              <Space style={{ cursor: 'pointer', padding: '4px 8px', borderRadius: 8 }}>
                <Avatar size="small" icon={<UserOutlined />} />
                <Text strong>管理员</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* 主内容区 */}
        <Content style={{
          margin: 0,
          background: '#f5f7fa',
          minHeight: 'calc(100vh - 64px)',
          overflow: 'auto',
        }}>
          <div style={{
            padding: 24,
            minHeight: '100%',
          }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}

export default ModernAppLayout