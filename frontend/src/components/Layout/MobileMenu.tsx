import React, { useState } from 'react';
import { Drawer, Menu, Button, Space, Typography } from 'antd';
import { MenuOutlined, CloseOutlined, HomeOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { MENU_ITEMS, getSelectedKeys, getOpenKeys } from '@/config/menuConfig';
import styles from './MobileMenu.module.css';

const { Text } = Typography;

const MobileMenu: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // 处理菜单点击
  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
    setVisible(false); // 点击后关闭菜单
  };

  // 显示菜单
  const showMenu = () => {
    setVisible(true);
  };

  // 隐藏菜单
  const hideMenu = () => {
    setVisible(false);
  };

  return (
    <>
      {/* 触发按钮 */}
      <Button
        type="text"
        icon={<MenuOutlined />}
        onClick={showMenu}
        aria-label="打开菜单"
        className={styles.menuTriggerButton}
      />

      {/* 抽屉菜单 */}
      <Drawer
        title={
          <Space className={styles.drawerTitleGroup}>
            <HomeOutlined className={styles.drawerHomeIcon} aria-label="首页" />
            <Text strong>资产管理系统</Text>
          </Space>
        }
        placement="left"
        onClose={hideMenu}
        open={visible}
        size={280}
        className={styles.mobileMenuDrawer}
        classNames={{ body: styles.drawerBody }}
        extra={
          <Button
            type="text"
            icon={<CloseOutlined />}
            onClick={hideMenu}
            aria-label="关闭菜单"
            className={styles.drawerCloseButton}
          />
        }
        aria-label="移动端导航菜单"
      >
        <Menu
          mode="inline"
          selectedKeys={getSelectedKeys(location.pathname)}
          defaultOpenKeys={getOpenKeys(location.pathname)}
          items={MENU_ITEMS}
          onClick={handleMenuClick}
          className={styles.menuRoot}
        />
      </Drawer>
    </>
  );
};

export default MobileMenu;
