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
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { AuthService } from '../../services/authService'
import { NotificationCenter } from '../Notification'

const { Header } = Layout

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

  // 通知菜单已移除，使用 NotificationCenter 组件替代

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
        <NotificationCenter />

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
