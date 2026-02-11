import React from 'react';
import { Layout, Menu } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import styles from './Layout.module.css';
import { MENU_ITEMS, getSelectedKeys, getOpenKeys } from '@/config/menuConfig';

const { Sider } = Layout;

interface AppSidebarProps {
  collapsed: boolean;
}

const AppSidebar: React.FC<AppSidebarProps> = ({ collapsed }) => {
  const location = useLocation();
  const navigate = useNavigate();

  // 处理菜单点击
  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <Sider
      trigger={null}
      collapsible
      collapsed={collapsed}
      width={240}
      className={styles.sidebar}
      aria-label="主导航侧边栏"
    >
      {/* Logo区域 */}
      <div
        className={
          collapsed ? `${styles.sidebarLogo} ${styles.sidebarLogoCollapsed}` : styles.sidebarLogo
        }
      >
        <HomeOutlined className={styles.sidebarLogoIcon} aria-hidden />
        {!collapsed && <span className={styles.sidebarLogoText}>资产管理</span>}
      </div>

      {/* 菜单 */}
      <Menu
        theme="light"
        mode="inline"
        selectedKeys={getSelectedKeys(location.pathname)}
        defaultOpenKeys={getOpenKeys(location.pathname)}
        items={MENU_ITEMS}
        onClick={handleMenuClick}
        className={styles.sidebarMenu}
        aria-label="系统主菜单"
      />
    </Sider>
  );
};

export default AppSidebar;
