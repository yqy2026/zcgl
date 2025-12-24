/**
 * @deprecated 此组件已废弃，请使用 AppLayout.tsx
 *
 * BusinessLayout 是一个简单的包装组件，功能已被 AppLayout 完全包含
 * 请使用: import { AppLayout } from '@/components/Layout'
 * 最后更新: 2025-12-24
 */

import React from 'react'
import { Layout } from 'antd'

const { Content } = Layout

interface BusinessLayoutProps {
  children: React.ReactNode
}

const BusinessLayout: React.FC<BusinessLayoutProps> = ({ children }) => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: '0' }}>
        {children}
      </Content>
    </Layout>
  )
}

export default BusinessLayout
