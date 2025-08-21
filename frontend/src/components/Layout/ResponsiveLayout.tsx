import React, { useState, useEffect } from 'react'
import { Layout, Typography } from 'antd'
import { useMediaQuery } from 'react-responsive'

import AppLayout from './AppLayout'
import MobileLayout from './MobileLayout'

const { Text } = Typography

interface ResponsiveLayoutProps {
  children: React.ReactNode
}

const ResponsiveLayout: React.FC<ResponsiveLayoutProps> = ({ children }) => {
  const [isMounted, setIsMounted] = useState(false)
  
  // 响应式断点
  const isDesktop = useMediaQuery({ minWidth: 992 })
  const isTablet = useMediaQuery({ minWidth: 768, maxWidth: 991 })
  const isMobile = useMediaQuery({ maxWidth: 767 })

  useEffect(() => {
    setIsMounted(true)
  }, [])

  // 避免服务端渲染时的不一致
  if (!isMounted) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '100vh' 
        }}>
          <Text>加载中...</Text>
        </div>
      </Layout>
    )
  }

  // 移动端使用特殊布局
  if (isMobile) {
    return <MobileLayout>{children}</MobileLayout>
  }

  // 桌面端和平板端使用标准布局
  return <AppLayout>{children}</AppLayout>
}

export default ResponsiveLayout