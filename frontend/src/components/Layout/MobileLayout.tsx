import React from 'react';
import { Layout, Typography, Space, Button } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { NotificationCenter } from '@/components/Notification';
import { SEARCH_ROUTES } from '@/constants/routes';

import MobileMenu from './MobileMenu';
import UserActionMenu from './UserActionMenu';
import styles from './MobileLayout.module.css';

const { Header, Content, Footer } = Layout;
const { Text } = Typography;

interface MobileLayoutProps {
  children: React.ReactNode;
}

const MobileLayout: React.FC<MobileLayoutProps> = ({ children }) => {
  const navigate = useNavigate();

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

        {/* 右侧：全局操作和用户菜单 */}
        <Space size="small" className={styles.mobileHeaderRight}>
          <Button
            type="text"
            icon={<SearchOutlined />}
            size="small"
            onClick={() => navigate(SEARCH_ROUTES.LIST)}
            aria-label="全局搜索"
            className={styles.headerActionButton}
          />
          <div className={styles.notificationSlot}>
            <NotificationCenter />
          </div>
          <UserActionMenu />
        </Space>
      </Header>

      {/* 主内容区 */}
      <Content className={styles.mobileContent}>{children}</Content>

      {/* 页脚 */}
      <Footer className={styles.mobileFooter}>
        <Text type="secondary">资产管理系统 ©2024</Text>
      </Footer>
    </Layout>
  );
};

export default MobileLayout;
