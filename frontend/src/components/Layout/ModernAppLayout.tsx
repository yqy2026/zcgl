/**
 * @deprecated 此组件已废弃，请使用 AppLayout.tsx 或 ResponsiveLayout.tsx
 *
 * ModernAppLayout 是一个现代化的布局实现，但未被采用
 * 推荐使用:
 * - 桌面端: import { AppLayout } from '@/components/Layout'
 * - 响应式: import { ResponsiveLayout } from '@/components/Layout'
 * 最后更新: 2025-12-24
 */

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
      label: '工作台',
    },
    {
      key: '/assets',
      icon: <BuildingOutlined />,
      label: '资产管理',
      children: [
        { key: '/assets/list', label: '资产列表' },
        { key: '/assets/new', label: '新增资产' },
        { key: '/assets/import', label: '批量导入' },
        { key: '/assets/analytics', label: '资产分析' },
      ],
    },
    // ... 其他菜单项
  ]

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{
          background: token.colorBgContainer,
          borderRight: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}>
          <Title level={5} style={{ margin: 0 }}>
            {collapsed ? '资产' : '资产管理系统'}
          </Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px',
          background: token.colorBgContainer,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          display: 'flex',
          alignItems: 'center',
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <div style={{ flex: 1 }} />
          <Space size="middle">
            <Badge count={5}>
              <Button type="text" icon={<BellOutlined />} />
            </Badge>
            <Dropdown menu={{ items: [
              { key: 'profile', icon: <UserOutlined />, label: '个人资料' },
              { key: 'settings', icon: <SettingOutlined />, label: '设置' },
              { type: 'divider' },
              { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
            ]}}>
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <Text>管理员</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: 24 }}>
          <div style={{
            padding: 24,
            background: token.colorBgContainer,
            borderRadius: token.borderRadiusLG,
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
