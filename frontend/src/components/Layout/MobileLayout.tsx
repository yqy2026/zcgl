import React from 'react';
import { Layout, Typography, Space, Avatar, Button } from 'antd';
import { UserOutlined, BellOutlined } from '@ant-design/icons';

import MobileMenu from './MobileMenu';

const { Header, Content, Footer } = Layout;
const { Text } = Typography;

interface MobileLayoutProps {
  children: React.ReactNode;
}

const MobileLayout: React.FC<MobileLayoutProps> = ({ children }) => {
  return (
    <Layout style={{ minHeight: '100%' }}>
      {/* 移动端头部 */}
      <Header
        style={{
          padding: '0 16px',
          background: 'var(--color-bg-primary)',
          borderBottom: '1px solid var(--color-border-light)',
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
            <Text strong style={{ fontSize: '16px', color: 'var(--color-primary)' }}>
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
            aria-label="通知"
            style={{
              fontSize: '16px',
              width: 44,
              height: 44,
              minWidth: 44,
              minHeight: 44,
            }}
          />
          <Avatar
            size="small"
            icon={<UserOutlined />}
            style={{
              backgroundColor: 'var(--color-primary)',
              width: 36,
              height: 36,
              minWidth: 36,
              minHeight: 36,
              cursor: 'pointer',
            }}
            aria-label="用户信息"
          />
        </Space>
      </Header>

      {/* 主内容区 */}
      <Content
        style={{
          marginTop: 56, // 头部高度
          padding: 0,
          background: 'var(--color-bg-tertiary)',
          minHeight: 'calc(100% - 56px)', // 减去头部的高度
          overflow: 'auto',
        }}
      >
        {children}
      </Content>

      {/* 页脚 */}
      <Footer
        style={{
          textAlign: 'center',
          background: 'var(--color-bg-primary)',
          borderTop: '1px solid var(--color-border-light)',
          padding: '8px 16px',
          fontSize: '12px',
        }}
      >
        <Text type="secondary">资产管理系统 ©2024</Text>
      </Footer>
    </Layout>
  );
};

export default MobileLayout;
