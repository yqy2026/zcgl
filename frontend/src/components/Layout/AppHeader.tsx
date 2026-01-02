import React from 'react'
import { Layout, Button, Avatar, Dropdown, Badge, message, Modal, Space, Tooltip, Typography } from 'antd'
import type { MenuProps } from 'antd'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  UserOutlined,
  SettingOutlined,
  QuestionCircleOutlined,
  ExclamationCircleOutlined,
  GlobalOutlined,
  BellOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { AuthService } from '../../services/authService'

const { Header } = Layout
const { Text } = Typography

interface AppHeaderProps {
  collapsed: boolean
  onToggleCollapsed: () => void
}

const AppHeader: React.FC<AppHeaderProps> = ({ collapsed, onToggleCollapsed }) => {
  const navigate = useNavigate()
  const user = AuthService.getLocalUser()

  // 处理退出登录
  const handleLogout = async () => {
    try {
      await AuthService.logout()
      navigate('/login')
    } catch (error) {
      console.error('退出登录失败:', error)
      // 即使API失败，也要跳转到登录页面
      navigate('/login')
    }
  }

  // 处理退出登录确认对话框
  const handleLogoutConfirm = () => {
    Modal.confirm({
      title: '确认退出登录',
      icon: <ExclamationCircleOutlined />,
      content: '退出后需要重新登录才能访问系统',
      okText: '确认退出',
      cancelText: '取消',
      okType: 'danger',
      onOk: handleLogout
    })
  }

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'help',
      icon: <QuestionCircleOutlined />,
      label: '帮助中心',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ]

  // 通知菜单
  const notificationItems: MenuProps['items'] = [
    {
      key: 'notification1',
      label: (
        <div style={{ width: 300 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
            新增资产审核通知
          </div>
          <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
            有3个新增资产等待审核，请及时处理
          </div>
          <div style={{ fontSize: '11px', color: '#bfbfbf', marginTop: 4 }}>
            2分钟前
          </div>
        </div>
      ),
    },
    {
      key: 'notification2',
      label: (
        <div style={{ width: 300 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
            数据导入完成
          </div>
          <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
            Excel数据导入已完成，成功导入156条记录
          </div>
          <div style={{ fontSize: '11px', color: '#bfbfbf', marginTop: 4 }}>
            10分钟前
          </div>
        </div>
      ),
    },
    {
      key: 'notification3',
      label: (
        <div style={{ width: 300 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
            系统维护通知
          </div>
          <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
            系统将于今晚22:00-24:00进行维护升级
          </div>
          <div style={{ fontSize: '11px', color: '#bfbfbf', marginTop: 4 }}>
            1小时前
          </div>
        </div>
      ),
    },
    {
      type: 'divider',
    },
    {
      key: 'viewAll',
      label: (
        <div style={{ textAlign: 'center', color: '#1890ff' }}>
          查看全部通知
        </div>
      ),
    },
  ]

  const handleUserMenuClick = ({ key }: { key: string }) => {
    switch (key) {
      case 'profile':
        navigate('/profile')
        break
      case 'settings':
        message.info('系统设置功能开发中')
        break
      case 'help':
        message.info('帮助中心功能开发中')
        break
      case 'logout':
        handleLogoutConfirm()
        break
    }
  }

  const handleNotificationClick = ({ key }: { key: string }) => {
    if (key === 'viewAll') {
      // View all notifications
    } else {
      // View notification details
    }
  }

  return (
    <Header
      style={{
        padding: '0 24px',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 64,
      }}
    >
      {/* 左侧 */}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={onToggleCollapsed}
          style={{
            fontSize: '16px',
            width: 40,
            height: 40,
          }}
        />

        <div style={{ marginLeft: 16 }}>
          <Typography.Text strong style={{ fontSize: '18px', color: '#1890ff' }}>
            土地房产资产管理系统
          </Typography.Text>
        </div>
      </div>

      {/* 右侧 */}
      <Space size="middle">
        {/* 语言切换 */}
        <Tooltip title="语言切换">
          <Button
            type="text"
            icon={<GlobalOutlined />}
            style={{ fontSize: '16px' }}
          />
        </Tooltip>

        {/* 帮助 */}
        <Tooltip title="帮助文档">
          <Button
            type="text"
            icon={<QuestionCircleOutlined />}
            style={{ fontSize: '16px' }}
          />
        </Tooltip>

        {/* 通知 */}
        <Dropdown
          menu={{
            items: notificationItems,
            onClick: handleNotificationClick,
          }}
          placement="bottomRight"
          trigger={['click']}
        >
          <Badge count={3} size="small">
            <Button
              type="text"
              icon={<BellOutlined />}
              style={{ fontSize: '16px' }}
            />
          </Badge>
        </Dropdown>

        {/* 用户信息 */}
        <Dropdown
          menu={{
            items: userMenuItems,
            onClick: handleUserMenuClick,
          }}
          placement="bottomRight"
          trigger={['click']}
        >
          <Space style={{ cursor: 'pointer', padding: '4px 8px', borderRadius: '6px' }}>
            <Avatar
              size="small"
              icon={<UserOutlined />}
              style={{ backgroundColor: '#1890ff' }}
            />
            <Typography.Text>{user?.full_name || user?.username || '用户'}</Typography.Text>
          </Space>
        </Dropdown>
      </Space>
    </Header>
  )
}

export default AppHeader