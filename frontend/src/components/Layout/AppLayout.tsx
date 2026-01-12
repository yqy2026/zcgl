import React, { useState } from 'react'
import { Layout, Typography } from 'antd'

import AppHeader from './AppHeader'
import AppSidebar from './AppSidebar'
import AppBreadcrumb from './AppBreadcrumb'
import styles from './Layout.module.css'

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
    <Layout className={styles.appLayout}>
      {/* 侧边栏 */}
      <AppSidebar collapsed={collapsed} />

      <Layout style={{ background: 'transparent' }}>
        {/* 头部 */}
        <AppHeader
          collapsed={collapsed}
          onToggleCollapsed={toggleCollapsed}
        />

        {/* 面包屑导航 */}
        <div className={styles.breadcrumb}>
          <AppBreadcrumb />
        </div>

        {/* 主内容区 */}
        <Content className={styles.content}>
          {children}
        </Content>

        {/* 页脚 */}
        <Footer className={styles.footer}>
          <Typography.Text type="secondary">
            土地房产资产管理系统 ©2024 Created by Asset Management Team
          </Typography.Text>
        </Footer>
      </Layout>
    </Layout>
  )
}

export default AppLayout
