import React from 'react';
import { Layout, Menu } from 'antd';
import type { MenuProps } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import styles from './Layout.module.css';
import {
  MENU_ITEMS,
  getSelectedKeys,
  getOpenKeys,
  getMenuNavigationPath,
} from '@/config/menuConfig';
import { useAssetOpsMenuBadges } from '@/hooks/useAssetOpsMenuBadges';

const { Sider } = Layout;

interface AppSidebarProps {
  collapsed: boolean;
}

/**
 * 原型 v5 侧栏徽标：本月 = 未完成件数；档案 = 红字「缺 N 份」。
 * 徽标数据不可用时不渲染（不假装为 0），页面自身会暴露加载错误。
 */
function withMenuBadges(
  items: MenuProps['items'],
  badges: { monthlyLeft: number | null; archiveMissing: number | null },
): MenuProps['items'] {
  return (items ?? []).map(item => {
    if (item != null && typeof item === 'object' && 'key' in item) {
      const key = String(item.key);
      if (key === '/asset-operations/monthly' && badges.monthlyLeft != null) {
        return {
          ...item,
          label: (
            <span>
              本月
              <BadgeCount value={badges.monthlyLeft} />
            </span>
          ),
        } as NonNullable<MenuProps['items']>[number];
      }
      if (key === '/asset-operations/archive' && badges.archiveMissing != null) {
        return {
          ...item,
          label: (
            <span>
              档案
              <span
                style={{ marginLeft: 6, fontSize: 12, color: 'var(--color-error, #cf1322)' }}
              >
                缺 {badges.archiveMissing} 份
              </span>
            </span>
          ),
        } as NonNullable<MenuProps['items']>[number];
      }
    }
    return item;
  });
}

function BadgeCount({ value }: { value: number }): React.ReactElement {
  if (value <= 0) {
    return <></>;
  }
  return (
    <span
      style={{ marginLeft: 6, fontSize: 12, fontVariantNumeric: 'tabular-nums' }}
      aria-label={`未完成 ${value} 件`}
    >
      {value}
    </span>
  );
}

const AppSidebar: React.FC<AppSidebarProps> = ({ collapsed }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const badges = useAssetOpsMenuBadges();

  // 处理菜单点击
  const handleMenuClick = ({ key }: { key: string }) => {
    const targetPath = getMenuNavigationPath(key);
    if (targetPath != null) {
      navigate(targetPath);
    }
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
        items={withMenuBadges(MENU_ITEMS, badges)}
        onClick={handleMenuClick}
        className={styles.sidebarMenu}
        aria-label="系统主菜单"
      />
    </Sider>
  );
};

export default AppSidebar;
