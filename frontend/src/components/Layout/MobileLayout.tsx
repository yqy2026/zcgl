import React from 'react'
import { Layout, Typography, Space, Avatar, Button } from 'antd'
import {
  UserOutlined,
  BellOutlined,
} from '@ant-design/icons'

import MobileMenu from './MobileMenu'
import AppBreadcrumb from './AppBreadcrumb'

const { Header, Content, Footer } = Layout
const { Text } = Typography

interface MobileLayoutProps {
  children: React.ReactNode
}

const MobileLayout: React.FC<MobileLayoutProps> = ({ children }) => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 移动端头部 */}
      <Header
        style={{
          padding: '0 16px',
          background: '#fff',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: 56,
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 1000,
        }}
      >
        {/* 左侧：菜单按钮和标题 */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <MobileMenu />
          <div style={{ marginLeft: 12 }}>
            <Text strong style={{ fontSize: '16px', color: '#1890ff' }}>
              资产管理
            </Text>
          </div>
        </div>

        {/* 右侧：用户信息 */}
        <Space size="small">
          <Button
            type="text"
            icon={<BellOutlined />}
            size="small"
            style={{ fontSize: '16px' }}
          />
          <Avatar
            size="small"
            icon={<UserOutlined />}
            style={{ backgroundColor: '#1890ff' }}
          />
        </Space>
      </Header>

      {/* 面包屑导航 */}
      <div
        style={{
          padding: '8px 16px',
          background: '#fff',
          borderBottom: '1px solid #f0f0f0',
          marginTop: 56, // 头部高度
          position: 'sticky',
          top: 56,
          zIndex: 999,
        }}
      >
        <AppBreadcrumb />
      </div>

      {/* 主内容区 */}
      <Content
        style={{
          padding: 0,
          background: '#f5f5f5',
          minHeight: 'calc(100vh - 112px)', // 减去头部和面包屑的高度
          overflow: 'auto',
        }}
      >
        {children}
      </Content>

      {/* 页脚 */}
      <Footer
        style={{
          textAlign: 'center',
          background: '#fff',
          borderTop: '1px solid #f0f0f0',
          padding: '8px 16px',
          fontSize: '12px',
        }}
      >
        <Text type="secondary">
          资产管理系统 ©2024
        </Text>
      </Footer>
    </Layout>
  )
}

export default MobileLayout