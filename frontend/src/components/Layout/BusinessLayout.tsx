import React, { useState } from 'react'
import { Layout, Menu, Breadcrumb, Avatar, Dropdown, Space, Typography, Badge } from 'antd'
import {
  HomeOutlined,
  BuildOutlined,
  TeamOutlined,
  DollarOutlined,
  FileTextOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Header, Sider, Content } = Layout
const { Title, Text } = Typography

interface BusinessLayoutProps {
  children: React.ReactNode
}

const BusinessLayout: React.FC<BusinessLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  // 导航菜单配置
  const menuItems = [
    {
      key: '/dashboard',
      icon: <HomeOutlined />,
      label: '工作台',
    },
    {
      key: '/assets',
      icon: <BuildOutlined />,
      label: '资产管理',
      children: [
        {
          key: '/assets/list',
          label: '资产清单',
        },
        {
          key: '/assets/new',
          label: '新增资产',
        },
        {
          key: '/assets/import',
          label: '批量导入',
        },
        {
          key: '/assets/analytics',
          label: '资产分析',
        },
      ],
    },
    {
      key: '/rental',
      icon: <TeamOutlined />,
      label: '租赁管理',
      children: [
        {
          key: '/rental/overview',
          label: '出租概况',
        },
        {
          key: '/rental/tenants',
          label: '租户管理',
        },
        {
          key: '/rental/contracts',
          label: '合同管理',
        },
        {
          key: '/rental/payments',
          label: '收租记录',
        },
      ],
    },
    {
      key: '/finance',
      icon: <DollarOutlined />,
      label: '财务管理',
      children: [
        {
          key: '/finance/overview',
          label: '财务概况',
        },
        {
          key: '/finance/records',
          label: '收支记录',
        },
        {
          key: '/finance/reports',
          label: '财务报表',
        },
      ],
    },
    {
      key: '/documents',
      icon: <FileTextOutlined />,
      label: '文档中心',
      children: [
        {
          key: '/documents/contracts',
          label: '合同文档',
        },
        {
          key: '/documents/certificates',
          label: '证照资料',
        },
        {
          key: '/documents/others',
          label: '其他文档',
        },
      ],
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      children: [
        {
          key: '/settings/profile',
          label: '个人设置',
        },
        {
          key: '/settings/data',
          label: '数据管理',
        },
      ],
    },
  ]

  // 用户下拉菜单
  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
      onClick: () => navigate('/settings/profile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        // 处理退出登录逻辑
        console.log('退出登录')
      },
    },
  ]

  // 生成面包屑
  const generateBreadcrumb = () => {
    const pathSnippets = location.pathname.split('/').filter(i => i)
    
    const breadcrumbItems = [
      {
        title: (
          <span onClick={() => navigate('/dashboard')} style={{ cursor: 'pointer' }}>
            <HomeOutlined /> 首页
          </span>
        ),
      },
    ]

    // 根据路径生成面包屑
    if (pathSnippets.length > 0) {
      const pathMap: Record<string, string> = {
        'dashboard': '工作台',
        'assets': '资产管理',
        'rental': '租赁管理',
        'finance': '财务管理',
        'documents': '文档中心',
        'settings': '系统设置',
        'list': '资产清单',
        'new': '新增资产',
        'import': '批量导入',
        'analytics': '资产分析',
        'overview': '概况',
        'tenants': '租户管理',
        'contracts': '合同管理',
        'payments': '收租记录',
        'records': '收支记录',
        'reports': '报表',
        'certificates': '证照资料',
        'others': '其他文档',
        'profile': '个人设置',
        'data': '数据管理',
      }

      pathSnippets.forEach((snippet, index) => {
        const url = `/${pathSnippets.slice(0, index + 1).join('/')}`
        const isLast = index === pathSnippets.length - 1
        
        breadcrumbItems.push({
          title: isLast ? (
            <span>{pathMap[snippet] || snippet}</span>
          ) : (
            <span onClick={() => navigate(url)} style={{ cursor: 'pointer' }}>
              {pathMap[snippet] || snippet}
            </span>
          ),
        })
      })
    }

    return breadcrumbItems
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        width={240}
        style={{
          background: '#fff',
          borderRight: '1px solid #f0f0f0',
        }}
      >
        {/* Logo区域 */}
        <div style={{ 
          height: '64px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? '0' : '0 24px',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <BuildOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
          {!collapsed && (
            <Title level={4} style={{ margin: '0 0 0 12px', color: '#1890ff' }}>
              资产管理
            </Title>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={['/assets', '/rental', '/finance']}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0, marginTop: '8px' }}
        />
      </Sider>

      {/* 主要内容区域 */}
      <Layout>
        {/* 顶部导航栏 */}
        <Header style={{ 
          background: '#fff', 
          padding: '0 24px', 
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          {/* 左侧：折叠按钮和面包屑 */}
          <Space size="large">
            <span
              onClick={() => setCollapsed(!collapsed)}
              style={{ 
                fontSize: '18px', 
                cursor: 'pointer',
                padding: '4px',
              }}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </span>
            
            <Breadcrumb items={generateBreadcrumb()} />
          </Space>

          {/* 右侧：通知和用户信息 */}
          <Space size="large">
            {/* 通知铃铛 */}
            <Badge count={5} size="small">
              <BellOutlined 
                style={{ fontSize: '18px', cursor: 'pointer' }}
                onClick={() => navigate('/notifications')}
              />
            </Badge>

            {/* 用户下拉菜单 */}
            <Dropdown
              menu={{ items: userMenuItems }}
              placement="bottomRight"
              arrow
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar size="small" icon={<UserOutlined />} />
                <Text>管理员</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* 页面内容 */}
        <Content style={{ 
          margin: '0',
          background: '#f5f5f5',
          minHeight: 'calc(100vh - 64px)',
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

export default BusinessLayout