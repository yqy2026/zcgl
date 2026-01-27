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
    <Sider trigger={null} collapsible collapsed={collapsed} width={240} className={styles.sidebar}>
      {/* Logo区域 */}
      <div
        className={
          collapsed ? `${styles.sidebarLogo} ${styles.sidebarLogoCollapsed}` : styles.sidebarLogo
        }
      >
        <HomeOutlined className={styles.sidebarLogoIcon} />
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
      />
    </Sider>
  );
};

export default AppSidebar;
