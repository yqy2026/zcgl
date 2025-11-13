import React, { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Popconfirm,
  Tag,
  Tooltip,
  Row,
  Col,
  Statistic,
  Avatar,
  Switch,
  Badge,
  Drawer,
  Descriptions,
  Skeleton
} from 'antd'
import SystemBreadcrumb from '../../components/System/SystemBreadcrumb'
import { userService, type User, type CreateUserData, type UpdateUserData } from '../../services/systemService'
import { useMessage } from '../../hooks/useMessage'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  UserOutlined,
  TeamOutlined,
  SettingOutlined,
  EyeOutlined,
  LockOutlined,
  UnlockOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Option } = Select
const { Search } = Input

// User类型已从systemService导入

interface UserStatistics {
  total: number
  active: number
  inactive: number
  locked: number
  by_role: Record<string, number>
  by_organization: Record<string, number>
}

const UserManagementPage: React.FC = () => {
  const { message } = useMessage()
  const [users, setUsers] = useState<User[]>([])
  const [organizations, setOrganizations] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [roleFilter, setRoleFilter] = useState<string>('')
  const [organizationFilter, setOrganizationFilter] = useState<string>('')

  const [form] = Form.useForm()

  // 状态选项
  const statusOptions = [
    { value: 'active', label: '活跃', color: 'green' },
    { value: 'inactive', label: '停用', color: 'red' },
    { value: 'locked', label: '锁定', color: 'orange' }
  ]

  useEffect(() => {
    loadUsers()
    loadOrganizations()
    loadRoles()
    loadStatistics()
  }, [])

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const data = await userService.getUsers()
      setUsers(data.items || [])
    } catch (error) {
      console.error('加载用户列表失败:', error)
      message.error('加载用户列表失败')
      // 如果API失败，使用模拟数据作为后备
      const mockUsers: User[] = [
        {
          id: '1',
          username: 'admin',
          email: 'admin@example.com',
          full_name: '系统管理员',
          phone: '13800138000',
          status: 'active',
          role: 'admin',
          role_name: '系统管理员',
          organization_id: '1',
          organization_name: '总公司',
          last_login: dayjs().subtract(1, 'hour').toISOString(),
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-10-15T00:00:00Z',
          is_locked: false,
          login_attempts: 0
        }
      ]
      setUsers(mockUsers)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadOrganizations = async () => {
    try {
      // 模拟组织数据
      const mockOrgs = [
        { id: '1', name: '总公司' },
        { id: '2', name: '项目部' },
        { id: '3', name: '财务部' }
      ]
      setOrganizations(mockOrgs)
    } catch (error) {
      message.error('加载组织列表失败')
    }
  }

  const loadRoles = async () => {
    try {
      // 模拟角色数据
      const mockRoles = [
        { id: 'admin', name: '系统管理员' },
        { id: 'manager', name: '项目经理' },
        { id: 'user', name: '普通用户' }
      ]
      setRoles(mockRoles)
    } catch (error) {
      message.error('加载角色列表失败')
    }
  }

  const loadStatistics = async () => {
    try {
      // 模拟统计数据
      const mockStats: UserStatistics = {
        total: users.length,
        active: users.filter(u => u.status === 'active').length,
        inactive: users.filter(u => u.status === 'inactive').length,
        locked: users.filter(u => u.status === 'locked').length,
        by_role: {},
        by_organization: {}
      }
      setStatistics(mockStats)
    } catch (error) {
      message.error('加载统计信息失败')
    }
  }

  const handleSearch = (value: string) => {
    setSearchText(value)
    // 这里可以添加搜索逻辑
  }

  const handleCreate = () => {
    setEditingUser(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (user: User) => {
    setEditingUser(user)
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      full_name: user.full_name,
      phone: user.phone,
      status: user.status,
      role: user.role,
      organization_id: user.organization_id
    })
    setModalVisible(true)
  }

  const handleDelete = async (id: string) => {
    try {
      // 模拟删除API调用
      message.success('删除成功')
      loadUsers()
      loadStatistics()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleToggleStatus = async (user: User, newStatus: string) => {
    try {
      // 模拟状态切换API调用
      message.success('状态已更新')
      loadUsers()
      loadStatistics()
    } catch (error) {
      message.error('状态更新失败')
    }
  }

  const handleToggleLock = async (user: User) => {
    try {
      // 模拟锁定/解锁API调用
      message.success(user.is_locked ? '用户已解锁' : '用户已锁定')
      loadUsers()
      loadStatistics()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleViewDetail = (user: User) => {
    setSelectedUser(user)
    setDetailDrawerVisible(true)
  }

  const handleSubmit = async (values: CreateUserData | UpdateUserData) => {
    try {
      if (editingUser) {
        // 模拟更新API调用
        message.success('更新成功')
      } else {
        // 模拟创建API调用
        message.success('创建成功')
      }
      setModalVisible(false)
      loadUsers()
      loadStatistics()
    } catch (error) {
      message.error(editingUser ? '更新失败' : '创建失败')
    }
  }

  const getStatusTag = (status: string) => {
    const statusConfig = statusOptions.find(s => s.value === status)
    return (
      <Tag color={statusConfig?.color || 'default'}>
        {statusConfig?.label || status}
      </Tag>
    )
  }

  const columns: ColumnsType<User> = [
    {
      title: '用户信息',
      key: 'user_info',
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.full_name}</div>
            <div style={{ fontSize: '12px', color: '#666' }}>
              @{record.username}
            </div>
          </div>
        </Space>
      )
    },
    {
      title: '联系方式',
      key: 'contact',
      render: (_, record) => (
        <div>
          <div>{record.email}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.phone || '未设置'}
          </div>
        </div>
      )
    },
    {
      title: '角色',
      dataIndex: 'role_name',
      key: 'role',
      render: (role) => <Tag color="blue">{role}</Tag>
    },
    {
      title: '组织',
      dataIndex: 'organization_name',
      key: 'organization'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status, record) => (
        <Space>
          {getStatusTag(status)}
          {record.is_locked && (
            <Tooltip title="账户已锁定">
              <LockOutlined style={{ color: '#ff4d4f' }} />
            </Tooltip>
          )}
        </Space>
      )
    },
    {
      title: '最后登录',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '从未登录'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="查看详情">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title={record.is_locked ? '解锁' : '锁定'}>
            <Button
              type="link"
              size="small"
              icon={record.is_locked ? <UnlockOutlined /> : <LockOutlined />}
              onClick={() => handleToggleLock(record)}
              style={{ color: record.is_locked ? '#52c41a' : '#ff4d4f' }}
            />
          </Tooltip>
          <Tooltip title={record.status === 'active' ? '停用' : '启用'}>
            <Switch
              size="small"
              checked={record.status === 'active'}
              onChange={(checked) => handleToggleStatus(record, checked ? 'active' : 'inactive')}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个用户吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            icon={<ExclamationCircleOutlined style={{ color: 'red' }} />}
          >
            <Tooltip title="删除">
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <>
      <SystemBreadcrumb />
      <div style={{ padding: '24px' }}>
        {/* 统计卡片 */}
      {statistics && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总用户数"
                value={statistics.total}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="活跃用户"
                value={statistics.active}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="停用用户"
                value={statistics.inactive}
                prefix={<SettingOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="锁定用户"
                value={statistics.locked}
                prefix={<LockOutlined />}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <div style={{ marginBottom: 16 }}>
          <Row justify="space-between" gutter={16}>
            <Col flex="auto">
              <Space size="middle">
                <Search
                  placeholder="搜索用户名、邮箱或姓名"
                  allowClear
                  style={{ width: 300 }}
                  onSearch={handleSearch}
                />
                <Select
                  placeholder="状态筛选"
                  allowClear
                  style={{ width: 120 }}
                  onChange={setStatusFilter}
                >
                  {statusOptions.map(status => (
                    <Option key={status.value} value={status.value}>
                      {status.label}
                    </Option>
                  ))}
                </Select>
                <Select
                  placeholder="角色筛选"
                  allowClear
                  style={{ width: 120 }}
                  onChange={setRoleFilter}
                >
                  {roles.map(role => (
                    <Option key={role.id} value={role.id}>
                      {role.name}
                    </Option>
                  ))}
                </Select>
                <Select
                  placeholder="组织筛选"
                  allowClear
                  style={{ width: 120 }}
                  onChange={setOrganizationFilter}
                >
                  {organizations.map(org => (
                    <Option key={org.id} value={org.id}>
                      {org.name}
                    </Option>
                  ))}
                </Select>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={loadUsers}
                >
                  刷新
                </Button>
              </Space>
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreate}
              >
                新建用户
              </Button>
            </Col>
          </Row>
        </div>

        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          pagination={{
            total: users.length,
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      </Card>

      {/* 创建/编辑模态框 */}
      <Modal
        title={editingUser ? '编辑用户' : '新建用户'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="username"
                label="用户名"
                rules={[
                  { required: true, message: '请输入用户名' },
                  { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' }
                ]}
              >
                <Input placeholder="请输入用户名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="email"
                label="邮箱"
                rules={[
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '请输入正确的邮箱格式' }
                ]}
              >
                <Input placeholder="请输入邮箱" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="full_name"
                label="姓名"
                rules={[{ required: true, message: '请输入姓名' }]}
              >
                <Input placeholder="请输入姓名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="phone"
                label="手机号"
                rules={[
                  { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号格式' }
                ]}
              >
                <Input placeholder="请输入手机号" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="status"
                label="状态"
                rules={[{ required: true, message: '请选择状态' }]}
              >
                <Select placeholder="请选择状态">
                  {statusOptions.map(status => (
                    <Option key={status.value} value={status.value}>
                      {status.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="role"
                label="角色"
                rules={[{ required: true, message: '请选择角色' }]}
              >
                <Select placeholder="请选择角色">
                  {roles.map(role => (
                    <Option key={role.id} value={role.id}>
                      {role.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="organization_id"
                label="所属组织"
                rules={[{ required: true, message: '请选择所属组织' }]}
              >
                <Select placeholder="请选择所属组织">
                  {organizations.map(org => (
                    <Option key={org.id} value={org.id}>
                      {org.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingUser ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 用户详情抽屉 */}
      <Drawer
        title="用户详情"
        placement="right"
        onClose={() => setDetailDrawerVisible(false)}
        open={detailDrawerVisible}
        width={600}
      >
        {selectedUser && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <Avatar size={80} icon={<UserOutlined />} />
              <h3 style={{ marginTop: 16, marginBottom: 8 }}>
                {selectedUser.full_name}
              </h3>
              <p style={{ color: '#666', margin: 0 }}>
                @{selectedUser.username}
              </p>
            </div>

            <Descriptions column={1} bordered>
              <Descriptions.Item label="用户名">
                {selectedUser.username}
              </Descriptions.Item>
              <Descriptions.Item label="邮箱">
                {selectedUser.email}
              </Descriptions.Item>
              <Descriptions.Item label="手机号">
                {selectedUser.phone || '未设置'}
              </Descriptions.Item>
              <Descriptions.Item label="角色">
                <Tag color="blue">{selectedUser.role_name}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="所属组织">
                {selectedUser.organization_name}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Space>
                  {getStatusTag(selectedUser.status)}
                  {selectedUser.is_locked && (
                    <Tag color="red">已锁定</Tag>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="最后登录">
                {selectedUser.last_login
                  ? dayjs(selectedUser.last_login).format('YYYY-MM-DD HH:mm:ss')
                  : '从未登录'
                }
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedUser.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {dayjs(selectedUser.updated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Space>
                <Button
                  type="primary"
                  icon={<EditOutlined />}
                  onClick={() => {
                    setDetailDrawerVisible(false)
                    handleEdit(selectedUser)
                  }}
                >
                  编辑用户
                </Button>
                <Button
                  icon={selectedUser.is_locked ? <UnlockOutlined /> : <LockOutlined />}
                  onClick={() => {
                    setDetailDrawerVisible(false)
                    handleToggleLock(selectedUser)
                  }}
                >
                  {selectedUser.is_locked ? '解锁账户' : '锁定账户'}
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Drawer>
    </div>
    </>
  )
}

export default UserManagementPage