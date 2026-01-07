import React from 'react';
import { Breadcrumb } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import {
  HomeOutlined,
  UserOutlined,
  TeamOutlined,
  ApartmentOutlined,
  BookOutlined,
  FileAddOutlined,
  AuditOutlined,
} from '@ant-design/icons';

interface BreadcrumbItem {
  title: string;
  icon?: React.ReactNode;
  path?: string;
}

const SystemBreadcrumb: React.FC = () => {
  const location = useLocation();

  // 系统管理页面的路由配置
  const systemRoutes: Record<string, BreadcrumbItem[]> = {
    '/system/users': [
      { title: '首页', icon: <HomeOutlined />, path: '/dashboard' },
      { title: '系统管理' },
      { title: '用户管理', icon: <UserOutlined /> },
    ],
    '/system/roles': [
      { title: '首页', icon: <HomeOutlined />, path: '/dashboard' },
      { title: '系统管理' },
      { title: '角色管理', icon: <TeamOutlined /> },
    ],
    '/system/organizations': [
      { title: '首页', icon: <HomeOutlined />, path: '/dashboard' },
      { title: '系统管理' },
      { title: '组织架构', icon: <ApartmentOutlined /> },
    ],
    '/system/dictionaries': [
      { title: '首页', icon: <HomeOutlined />, path: '/dashboard' },
      { title: '系统管理' },
      { title: '字典管理', icon: <BookOutlined /> },
    ],
    '/system/templates': [
      { title: '首页', icon: <HomeOutlined />, path: '/dashboard' },
      { title: '系统管理' },
      { title: '数据模板', icon: <FileAddOutlined /> },
    ],
    '/system/logs': [
      { title: '首页', icon: <HomeOutlined />, path: '/dashboard' },
      { title: '系统管理' },
      { title: '操作日志', icon: <AuditOutlined /> },
    ],
  };

  const getBreadcrumbItems = (): BreadcrumbItem[] => {
    const pathname = location.pathname;

    // 精确匹配系统管理路由
    if (systemRoutes[pathname] !== null && systemRoutes[pathname] !== undefined) {
      return systemRoutes[pathname];
    }

    // 默认面包屑（用于非系统管理页面）
    return [{ title: '首页', icon: <HomeOutlined />, path: '/dashboard' }, { title: '系统管理' }];
  };

  const breadcrumbItems = getBreadcrumbItems();

  return (
    <div
      style={{
        padding: '16px 0',
        borderBottom: '1px solid #f0f0f0',
        backgroundColor: '#fafafa',
      }}
    >
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '0 24px',
        }}
      >
        <Breadcrumb
          items={breadcrumbItems.map((item, index) => ({
            key: index,
            title: (
              <span>
                {item.icon !== null && item.icon !== undefined && (
                  <span style={{ marginRight: 8 }}>{item.icon}</span>
                )}
                {item.path !== null && item.path !== undefined && item.path !== '' ? (
                  <Link to={item.path} style={{ color: '#1890ff' }}>
                    {item.title}
                  </Link>
                ) : (
                  <span
                    style={{
                      color: index === breadcrumbItems.length - 1 ? '#000' : '#666',
                      fontWeight: index === breadcrumbItems.length - 1 ? 500 : 'normal',
                    }}
                  >
                    {item.title}
                  </span>
                )}
              </span>
            ),
          }))}
        />
      </div>
    </div>
  );
};

export default SystemBreadcrumb;
