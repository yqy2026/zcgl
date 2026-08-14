import React from 'react';
import { Layout, Button, Space, Tooltip, Typography } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { NotificationCenter } from '@/components/Notification';
import { SEARCH_ROUTES } from '@/constants/routes';

import UserActionMenu from './UserActionMenu';

import styles from './Layout.module.css';

const { Header } = Layout;

interface AppHeaderProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

const AppHeader: React.FC<AppHeaderProps> = ({ collapsed, onToggleCollapsed }) => {
  const navigate = useNavigate();

  const handleOpenGlobalSearch = () => {
    navigate(SEARCH_ROUTES.LIST);
  };

  return (
    <Header className={styles.header}>
      {/* 左侧 */}
      <div className={styles.headerLeft}>
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={onToggleCollapsed}
          className={styles.headerToggleButton}
          aria-label={collapsed ? '展开侧边栏' : '折叠侧边栏'}
        />

        <div className={styles.headerTitleWrapper}>
          <Typography.Text strong className={styles.headerTitle}>
            土地物业资产运营管理系统
          </Typography.Text>
        </div>
      </div>

      {/* 右侧 */}
      <Space size={8} className={styles.headerRight} wrap>
        <Tooltip title="全局搜索">
          <Button
            type="text"
            className={styles.headerIconButton}
            icon={<SearchOutlined className={styles.headerActionIcon} />}
            onClick={handleOpenGlobalSearch}
            aria-label="全局搜索"
          />
        </Tooltip>

        {/* 通知 */}
        <div className={styles.notificationSlot}>
          <NotificationCenter />
        </div>

        {/* 用户信息 */}
        <UserActionMenu
          shouldShowName
          buttonClassName={styles.userInfoButton}
          avatarClassName={styles.userAvatar}
          userTextClassName={styles.userText}
        />
      </Space>
    </Header>
  );
};

export default AppHeader;
