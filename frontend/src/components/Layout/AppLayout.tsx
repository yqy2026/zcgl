import React, { useState } from 'react'
import { Layout, Typography } from 'antd'

import AppHeader from './AppHeader'
import AppSidebar from './AppSidebar'
import AppBreadcrumb from './AppBreadcrumb'

const { Content, Footer } = Layout

interface AppLayoutProps {
  children: React.ReactNode
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false)

  const toggleCollapsed = () => {
    setCollapsed(!collapsed)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <AppSidebar collapsed={collapsed} />
      
      <Layout>
        {/* 头部 */}
        <AppHeader 
          collapsed={collapsed} 
          onToggleCollapsed={toggleCollapsed}
        />
        
        {/* 面包屑导航 */}
        <div style={{ 
          padding: '12px 24px', 
          background: '#fff', 
          borderBottom: '1px solid #f0f0f0' 
        }}>
          <AppBreadcrumb />
        </div>
        
        {/* 主内容区 */}
        <Content
          style={{
            margin: 0,
            padding: 0,
            background: '#f5f5f5',
            minHeight: 'calc(100vh - 112px)', // 减去头部和面包屑的高度
            overflow: 'auto',
          }}
        >
          {children}
        </Content>
        
        {/* 页脚 */}
        <Footer style={{ 
          textAlign: 'center', 
          background: '#fff',
          borderTop: '1px solid #f0f0f0',
          padding: '12px 24px'
        }}>
          <Typography.Text type="secondary">
            土地房产资产管理系统 ©2024 Created by Asset Management Team
          </Typography.Text>
        </Footer>
      </Layout>
    </Layout>
  )
}

export default AppLayout