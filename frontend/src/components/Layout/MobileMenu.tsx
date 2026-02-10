import React, { useState } from 'react';
import { Drawer, Menu, Button, Space, Typography } from 'antd';
import { MenuOutlined, CloseOutlined, HomeOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { MENU_ITEMS, getSelectedKeys, getOpenKeys } from '@/config/menuConfig';

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
        style={{
          fontSize: '16px',
          width: 44,
          height: 44,
          minWidth: 44,
          minHeight: 44,
        }}
      />

      {/* 抽屉菜单 */}
      <Drawer
        title={
          <Space>
            <HomeOutlined style={{ color: 'var(--color-primary)' }} aria-label="首页" />
            <Text strong>资产管理系统</Text>
          </Space>
        }
        placement="left"
        onClose={hideMenu}
        open={visible}
        size={280}
        styles={{
          body: { padding: 0 },
        }}
        extra={
          <Button
            type="text"
            icon={<CloseOutlined />}
            onClick={hideMenu}
            aria-label="关闭菜单"
            style={{
              width: 44,
              height: 44,
              minWidth: 44,
              minHeight: 44,
            }}
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
          style={{
            borderRight: 0,
            height: '100%',
            background: 'var(--color-bg-primary)',
          }}
        />
      </Drawer>
    </>
  );
};

export default MobileMenu;
