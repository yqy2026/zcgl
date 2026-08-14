import React from 'react';
import { Avatar, Button, Dropdown, Modal, Typography } from 'antd';
import type { MenuProps } from 'antd';
import {
  ExclamationCircleOutlined,
  LogoutOutlined,
  SettingOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';
import { SYSTEM_ROUTES } from '@/constants/routes';
import { AuthService } from '@/services/authService';

import styles from './MobileLayout.module.css';

interface UserActionMenuProps {
  shouldShowName?: boolean;
  buttonClassName?: string;
  avatarClassName?: string;
  userTextClassName?: string;
}

const UserActionMenu: React.FC<UserActionMenuProps> = ({
  shouldShowName = false,
  buttonClassName = styles.userActionButton,
  avatarClassName = styles.userAvatar,
  userTextClassName,
}) => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const user = AuthService.getLocalUser();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('退出登录失败:', error);
      navigate('/login');
    }
  };

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

  const items: MenuProps['items'] = [
    { key: 'profile', icon: <UserOutlined />, label: '个人资料' },
    { key: 'settings', icon: <SettingOutlined />, label: '系统设置' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ];

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'profile') {
      navigate('/profile');
    } else if (key === 'settings') {
      navigate(SYSTEM_ROUTES.SETTINGS);
    } else if (key === 'logout') {
      handleLogoutConfirm();
    }
  };

  return (
    <Dropdown
      menu={{ items, onClick: handleMenuClick }}
      placement="bottomRight"
      trigger={['click']}
    >
      <Button
        type="text"
        className={buttonClassName}
        aria-label="用户菜单"
        aria-haspopup="menu"
      >
        <Avatar size="small" icon={<UserOutlined />} className={avatarClassName} />
        {shouldShowName ? (
          <Typography.Text strong className={userTextClassName}>
            {user?.full_name ?? user?.username ?? '用户'}
          </Typography.Text>
        ) : null}
      </Button>
    </Dropdown>
  );
};

export default UserActionMenu;
