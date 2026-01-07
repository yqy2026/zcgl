import React, { useState } from 'react';
import { Drawer, Menu, Button, Space, Typography } from 'antd';
import {
  MenuOutlined,
  CloseOutlined,
  DashboardOutlined,
  HomeOutlined,
  SearchOutlined,
  FileExcelOutlined,
  BarChartOutlined,
  SettingOutlined,
  PlusOutlined,
  UnorderedListOutlined,
  UploadOutlined,
  DownloadOutlined,
  LineChartOutlined,
  PieChartOutlined,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import type { MenuProps } from 'antd';

const { Text } = Typography;

const MobileMenu: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // 菜单项配置（与侧边栏相同）
  const menuItems: MenuProps['items'] = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '数据看板',
    },
    {
      key: 'assets',
      icon: <HomeOutlined />,
      label: '资产管理',
      children: [
        {
          key: '/assets',
          icon: <UnorderedListOutlined />,
          label: '资产列表',
        },
        {
          key: '/assets/new',
          icon: <PlusOutlined />,
          label: '新增资产',
        },
        {
          key: '/assets/search',
          icon: <SearchOutlined />,
          label: '高级搜索',
        },
      ],
    },
    {
      key: 'data',
      icon: <FileExcelOutlined />,
      label: '数据管理',
      children: [
        {
          key: '/data/import',
          icon: <UploadOutlined />,
          label: '数据导入',
        },
        {
          key: '/data/export',
          icon: <DownloadOutlined />,
          label: '数据导出',
        },
        {
          key: '/data/import-export',
          icon: <FileExcelOutlined />,
          label: '导入导出',
        },
      ],
    },
    {
      key: 'analytics',
      icon: <BarChartOutlined />,
      label: '数据分析',
      children: [
        {
          key: '/analytics/occupancy',
          icon: <LineChartOutlined />,
          label: '出租率分析',
        },
        {
          key: '/analytics/distribution',
          icon: <PieChartOutlined />,
          label: '资产分布',
        },
        {
          key: '/analytics/area',
          icon: <BarChartOutlined />,
          label: '面积统计',
        },
      ],
    },
    {
      key: 'system',
      icon: <SettingOutlined />,
      label: '系统管理',
      children: [
        {
          key: '/system/users',
          icon: <SettingOutlined />,
          label: '用户管理',
        },
        {
          key: '/system/roles',
          icon: <SettingOutlined />,
          label: '角色管理',
        },
        {
          key: '/system/logs',
          icon: <SettingOutlined />,
          label: '操作日志',
        },
      ],
    },
  ];

  // 获取当前选中的菜单项
  const getSelectedKeys = () => {
    const pathname = location.pathname;

    if (pathname === '/') {
      return ['/dashboard'];
    }
    if (pathname.match(/^\/assets\/\d+$/)) {
      return ['/assets'];
    }
    if (pathname.match(/^\/assets\/\d+\/edit$/)) {
      return ['/assets'];
    }

    return [pathname];
  };

  // 获取展开的菜单项
  const getOpenKeys = () => {
    const pathname = location.pathname;

    if (pathname.startsWith('/assets')) {
      return ['assets'];
    }
    if (pathname.startsWith('/data')) {
      return ['data'];
    }
    if (pathname.startsWith('/analytics')) {
      return ['analytics'];
    }
    if (pathname.startsWith('/system')) {
      return ['system'];
    }

    return [];
  };

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
        style={{
          fontSize: '16px',
          width: 40,
          height: 40,
        }}
      />

      {/* 抽屉菜单 */}
      <Drawer
        title={
          <Space>
            <HomeOutlined style={{ color: '#1890ff' }} />
            <Text strong>资产管理系统</Text>
          </Space>
        }
        placement="left"
        onClose={hideMenu}
        open={visible}
        width={280}
        styles={{
          body: { padding: 0 },
        }}
        extra={<Button type="text" icon={<CloseOutlined />} onClick={hideMenu} />}
      >
        <Menu
          mode="inline"
          selectedKeys={getSelectedKeys()}
          defaultOpenKeys={getOpenKeys()}
          items={menuItems}
          onClick={handleMenuClick}
          style={{
            borderRight: 0,
            height: '100%',
          }}
        />
      </Drawer>
    </>
  );
};

export default MobileMenu;
