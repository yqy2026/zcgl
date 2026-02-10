import React from 'react';
import { Layout, Button, Avatar, Dropdown, Modal, Space, Tooltip, Typography } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import type { MenuProps } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  UserOutlined,
  SettingOutlined,
  QuestionCircleOutlined,
  ExclamationCircleOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { AuthService } from '@/services/authService';
import { NotificationCenter } from '@/components/Notification';

import styles from './Layout.module.css';

const { Header } = Layout;
const HEADER_TOGGLE_BUTTON_STYLE = {
  fontSize: '16px',
  width: 40,
  height: 40,
} as const;
const HEADER_TITLE_WRAPPER_STYLE = { marginLeft: 16 } as const;
const HEADER_ICON_STYLE = { fontSize: '16px' } as const;
const USER_AVATAR_STYLE = { backgroundColor: '#1677ff' } as const;
const USER_TEXT_STYLE = { color: '#1e293b' } as const;

interface AppHeaderProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

const AppHeader: React.FC<AppHeaderProps> = ({ collapsed, onToggleCollapsed }) => {
  const navigate = useNavigate();
  const user = AuthService.getLocalUser();

  // 处理退出登录
  const handleLogout = async () => {
    try {
      await AuthService.logout();
      navigate('/login');
    } catch (error) {
      // eslint-disable-next-line no-console
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

  return (
    <Header className={styles.header}>
      {/* 左侧 */}
      <div className={styles.headerLeft}>
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={onToggleCollapsed}
          style={HEADER_TOGGLE_BUTTON_STYLE}
          aria-label={collapsed ? '展开侧边栏' : '折叠侧边栏'}
        />

        <div style={HEADER_TITLE_WRAPPER_STYLE}>
          <Typography.Text strong className={styles.headerTitle}>
            土地房产资产管理系统
          </Typography.Text>
        </div>
      </div>

      {/* 右侧 */}
      <Space size="middle" className={styles.headerRight}>
        {/* 语言切换 */}
        <Tooltip title="语言切换">
          <Button
            type="text"
            className={styles.headerIconButton}
            icon={<GlobalOutlined style={HEADER_ICON_STYLE} />}
            onClick={handleLanguageSwitch}
            aria-label="语言切换"
          />
        </Tooltip>

        {/* 帮助 */}
        <Tooltip title="帮助文档">
          <Button
            type="text"
            className={styles.headerIconButton}
            icon={<QuestionCircleOutlined style={HEADER_ICON_STYLE} />}
            onClick={handleOpenHelpDocs}
            aria-label="帮助文档"
          />
        </Tooltip>

        {/* 通知 */}
        <NotificationCenter />

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
          >
            <Avatar size="small" icon={<UserOutlined />} style={USER_AVATAR_STYLE} />
            <Typography.Text strong style={USER_TEXT_STYLE}>
              {user?.full_name ?? user?.username ?? '用户'}
            </Typography.Text>
          </Button>
        </Dropdown>
      </Space>
    </Header>
  );
};

export default AppHeader;
