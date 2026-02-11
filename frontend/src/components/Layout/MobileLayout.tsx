import React from 'react';
import { Layout, Typography, Space, Avatar, Button } from 'antd';
import { UserOutlined, BellOutlined } from '@ant-design/icons';

import MobileMenu from './MobileMenu';
import styles from './MobileLayout.module.css';

const { Header, Content, Footer } = Layout;
const { Text } = Typography;

interface MobileLayoutProps {
  children: React.ReactNode;
}

const MobileLayout: React.FC<MobileLayoutProps> = ({ children }) => {
  return (
    <Layout className={styles.mobileLayout}>
      {/* 移动端头部 */}
      <Header className={styles.mobileHeader}>
        {/* 左侧：菜单按钮和标题 */}
        <div className={styles.mobileHeaderLeft}>
          <MobileMenu />
          <div className={styles.mobileHeaderTitleWrapper}>
            <Text strong className={styles.mobileHeaderTitle}>
              资产管理系统
            </Text>
          </div>
        </div>

        {/* 右侧：用户信息 */}
        <Space size="small" className={styles.mobileHeaderRight}>
          <Button
            type="text"
            icon={<BellOutlined />}
            size="small"
            aria-label="通知"
            className={styles.notificationButton}
          />
          <Avatar
            size="small"
            icon={<UserOutlined />}
            className={styles.userAvatar}
          />
        </Space>
      </Header>

      {/* 主内容区 */}
      <Content className={styles.mobileContent}>
        {children}
      </Content>

      {/* 页脚 */}
      <Footer className={styles.mobileFooter}>
        <Text type="secondary">资产管理系统 ©2024</Text>
      </Footer>
    </Layout>
  );
};

export default MobileLayout;
