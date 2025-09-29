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