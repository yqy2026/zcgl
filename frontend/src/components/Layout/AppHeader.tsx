import React from 'react';
import { Layout, Button, Avatar, Dropdown, Modal, Space, Tooltip, Typography } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import type { MenuProps } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  SearchOutlined,
  UserOutlined,
  SettingOutlined,
  QuestionCircleOutlined,
  ExclamationCircleOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { AuthService } from '@/services/authService';
import { NotificationCenter } from '@/components/Notification';
import { useRoutePerspective } from '@/routes/perspective';

import styles from './Layout.module.css';

const { Header } = Layout;

interface AppHeaderProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

const AppHeader: React.FC<AppHeaderProps> = ({ collapsed, onToggleCollapsed }) => {
  const navigate = useNavigate();
  const { perspective } = useRoutePerspective();
  const { logout } = useAuth();
  const user = AuthService.getLocalUser();

  // 处理退出登录
  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('退出登录失败:', error);
      // 即使API失败，也要跳转到登录页面
      navigate('/login');
    }
  };

  // 处理退出登录确认对话框
  const handleLogoutConfirm = () => {
    Modal.confirm({
      title: '确认退出登录',
      icon: <ExclamationCircleOutlined />,
      content: '退出后需要重新登录才能访问系统',
      okText: '确认退出',
      cancelText: '取消',
      okType: 'danger',
      onOk: handleLogout,
    });
  };

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'help',
      icon: <QuestionCircleOutlined />,
      label: '帮助中心',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  // 通知菜单已移除，使用 NotificationCenter 组件替代

  const handleUserMenuClick = ({ key }: { key: string }) => {
    switch (key) {
      case 'profile':
        navigate('/profile');
        break;
      case 'settings':
        MessageManager.info('系统设置功能开发中');
        break;
      case 'help':
        MessageManager.info('帮助中心功能开发中');
        break;
      case 'logout':
        handleLogoutConfirm();
        break;
    }
  };

  const handleLanguageSwitch = () => {
    MessageManager.info('多语言切换功能开发中');
  };

  const handleOpenHelpDocs = () => {
    MessageManager.info('帮助文档功能开发中');
  };

  const handleOpenGlobalSearch = () => {
    if (perspective === 'owner') {
      navigate('/owner/search');
      return;
    }
    if (perspective === 'manager') {
      navigate('/manager/search');
      return;
    }
    MessageManager.info('请先进入业主视角或经营视角后再使用全局搜索');
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
            土地房产资产管理系统
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

        {/* 语言切换 */}
        <Tooltip title="语言切换">
          <Button
            type="text"
            className={styles.headerIconButton}
            icon={<GlobalOutlined className={styles.headerActionIcon} />}
            onClick={handleLanguageSwitch}
            aria-label="语言切换"
          />
        </Tooltip>

        {/* 帮助 */}
        <Tooltip title="帮助文档">
          <Button
            type="text"
            className={styles.headerIconButton}
            icon={<QuestionCircleOutlined className={styles.headerActionIcon} />}
            onClick={handleOpenHelpDocs}
            aria-label="帮助文档"
          />
        </Tooltip>

        {/* 通知 */}
        <div className={styles.notificationSlot}>
          <NotificationCenter />
        </div>

        {/* 用户信息 */}
        <Dropdown
          menu={{
            items: userMenuItems,
            onClick: handleUserMenuClick,
          }}
          placement="bottomRight"
          trigger={['click']}
        >
          <Button
            type="text"
            className={styles.userInfoButton}
            aria-label="用户菜单"
            aria-haspopup="menu"
          >
            <Avatar size="small" icon={<UserOutlined />} className={styles.userAvatar} />
            <Typography.Text strong className={styles.userText}>
              {user?.full_name ?? user?.username ?? '用户'}
            </Typography.Text>
          </Button>
        </Dropdown>
      </Space>
    </Header>
  );
};

export default AppHeader;
