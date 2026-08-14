import React, { useId, useState } from 'react';
import { Drawer, Menu, Button, Space, Typography } from 'antd';
import { MenuOutlined, CloseOutlined, HomeOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  MENU_ITEMS,
  getSelectedKeys,
  getOpenKeys,
  getMenuNavigationPath,
} from '@/config/menuConfig';
import styles from './MobileMenu.module.css';

const { Text } = Typography;

// antd 弹层 z-index 需要数值 prop，无法直接用 CSS var()；
// 从 variables.css --z-index-modal 同源读取（单一真相源），jsdom/无样式环境回退到 token 文档值
const DRAWER_Z_INDEX = (() => {
  const raw = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue('--z-index-modal')
    .trim();
  const parsed = Number.parseInt(raw, 10);
  return Number.isNaN(parsed) ? 1050 : parsed;
})();

const MobileMenu: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  // antd v6 Drawer 有 title 时会注入 aria-labelledby 指向标题（覆盖 aria-label），
  // 需显式 aria-labelledby 指向 sr-only 命名元素，保证对话框可访问名称为「移动端导航菜单」
  const drawerLabelId = useId();

  // 处理菜单点击
  const handleMenuClick = ({ key }: { key: string }) => {
    const targetPath = getMenuNavigationPath(key);
    if (targetPath != null) {
      navigate(targetPath);
    }
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

      {/* 抽屉的可访问名称锚点（视觉隐藏，供 aria-labelledby 引用） */}
      <span id={drawerLabelId} className="sr-only">
        移动端导航菜单
      </span>

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
        // antd 弹层基础 z-index 为 1000，低于移动顶栏 --z-index-fixed(1030)，
        // 否则抽屉头部（含关闭按钮）被顶栏覆盖无法点击；取值同 --z-index-modal
        zIndex={DRAWER_Z_INDEX}
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
        aria-labelledby={drawerLabelId}
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
