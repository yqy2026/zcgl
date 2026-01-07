import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Tag,
  Tooltip,
  Row,
  Col,
  Statistic,
  Switch,
  Badge,
  Tree,
  Transfer,
  Divider,
  Typography,
} from 'antd';
import {
  systemService as _systemService,
  roleService as _roleService,
  type Role,
} from '../../services/systemService';
import SystemBreadcrumb from '../../components/System/SystemBreadcrumb';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  TeamOutlined,
  SettingOutlined,
  KeyOutlined,
  SafetyOutlined,
  UserOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { TransferItem } from 'antd/es/transfer';
import type { DataNode } from 'antd/es/tree';
import dayjs from 'dayjs';

const { Option } = Select;
const { Search } = Input;
const { TextArea } = Input;
const { Text } = Typography;

// Role类型已从systemService导入

interface Permission {
  id: string;
  name: string;
  code: string;
  module: string;
  description: string;
  type: 'menu' | 'action' | 'data';
}

interface RoleStatistics {
  total: number;
  active: number;
  inactive: number;
  system: number;
  custom: number;
  avg_permissions: number;
}

const RoleManagementPage: React.FC = () => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [statistics, setStatistics] = useState<RoleStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [permissionModalVisible, setPermissionModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [targetPermissions, setTargetPermissions] = useState<string[]>([]);
  const [_searchText, _setSearchText] = useState('');
  const [_statusFilter, _setStatusFilter] = useState<string>('');
  const [permissionTreeData, setPermissionTreeData] = useState<DataNode[]>([]);

  const [form] = Form.useForm();

  // 状态选项
  const statusOptions = [
    { value: 'active', label: '启用', color: 'green' },
    { value: 'inactive', label: '停用', color: 'red' },
  ];

  // 权限模块选项
  const permissionModules = React.useMemo(
    () => [
      { value: 'dashboard', label: '数据看板', icon: <SettingOutlined /> },
      { value: 'assets', label: '资产管理', icon: <ApartmentOutlined /> },
      { value: 'rental', label: '租赁管理', icon: <UserOutlined /> },
      { value: 'ownership', label: '权属方管理', icon: <KeyOutlined /> },
      { value: 'project', label: '项目管理', icon: <TeamOutlined /> },
      { value: 'system', label: '系统管理', icon: <SettingOutlined /> },
    ],
    []
  );

  const loadRoles = React.useCallback(() => {
    setLoading(true);
    try {
      // 模拟API调用
      const mockRoles: Role[] = [
        {
          id: 'admin',
          name: '系统管理员',
          code: 'admin',
          description: '拥有系统所有权限的超级管理员',
          status: 'active',
          permissions: [
            'dashboard.view',
            'assets.*',
            'rental.*',
            'ownership.*',
            'project.*',
            'system.*',
          ],
          user_count: 1,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-10-15T00:00:00Z',
          is_system: true,
        },
        {
          id: 'manager',
          name: '项目经理',
          code: 'project_manager',
          description: '负责项目管理的高级用户',
          status: 'active',
          permissions: [
            'dashboard.view',
            'assets.view',
            'assets.create',
            'rental.view',
            'ownership.view',
            'project.*',
          ],
          user_count: 5,
          created_at: '2024-01-02T00:00:00Z',
          updated_at: '2024-10-14T00:00:00Z',
          is_system: false,
        },
        {
          id: 'user',
          name: '普通用户',
          code: 'normal_user',
          description: '基础权限的普通用户',
          status: 'active',
          permissions: [
            'dashboard.view',
            'assets.view',
            'rental.view',
            'ownership.view',
            'project.view',
          ],
          user_count: 20,
          created_at: '2024-01-03T00:00:00Z',
          updated_at: '2024-10-13T00:00:00Z',
          is_system: false,
        },
      ];
      setRoles(mockRoles);
    } catch {
      message.error('加载角色列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const buildPermissionTree = React.useCallback(
    (permissionList: Permission[]): DataNode[] => {
      const moduleMap: Record<string, DataNode> = {};

      // 按模块分组
      permissionList.forEach(permission => {
        if (moduleMap[permission.module] === undefined) {
          const module = permissionModules.find(m => m.value === permission.module);
          moduleMap[permission.module] = {
            key: permission.module,
            title: (
              <Space>
                {module?.icon ?? <SettingOutlined />}
                {module?.label ?? permission.module}
              </Space>
            ),
            children: [],
          };
        }

        moduleMap[permission.module].children!.push({
          key: permission.id,
          title: (
            <Space>
              <span>{permission.name}</span>
              <Tag
                color={
                  permission.type === 'menu'
                    ? 'blue'
                    : permission.type === 'action'
                      ? 'green'
                      : 'orange'
                }
              >
                {permission.type === 'menu'
                  ? '菜单'
                  : permission.type === 'action'
                    ? '操作'
                    : '数据'}
              </Tag>
            </Space>
          ),
        });
      });

      return Object.values(moduleMap);
    },
    [permissionModules]
  );

  const loadPermissions = React.useCallback(() => {
    try {
      // 模拟权限数据
      const mockPermissions: Permission[] = [
        {
          id: 'dashboard.view',
          name: '查看看板',
          code: 'dashboard.view',
          module: 'dashboard',
          description: '查看数据看板',
          type: 'menu',
        },
        {
          id: 'assets.view',
          name: '查看资产',
          code: 'assets.view',
          module: 'assets',
          description: '查看资产列表',
          type: 'menu',
        },
        {
          id: 'assets.create',
          name: '创建资产',
          code: 'assets.create',
          module: 'assets',
          description: '创建新资产',
          type: 'action',
        },
        {
          id: 'assets.edit',
          name: '编辑资产',
          code: 'assets.edit',
          module: 'assets',
          description: '编辑资产信息',
          type: 'action',
        },
        {
          id: 'assets.delete',
          name: '删除资产',
          code: 'assets.delete',
          module: 'assets',
          description: '删除资产',
          type: 'action',
        },
        {
          id: 'rental.view',
          name: '查看租赁',
          code: 'rental.view',
          module: 'rental',
          description: '查看租赁合同',
          type: 'menu',
        },
        {
          id: 'rental.create',
          name: '创建合同',
          code: 'rental.create',
          module: 'rental',
          description: '创建租赁合同',
          type: 'action',
        },
        {
          id: 'ownership.view',
          name: '查看权属方',
          code: 'ownership.view',
          module: 'ownership',
          description: '查看权属方信息',
          type: 'menu',
        },
        {
          id: 'project.view',
          name: '查看项目',
          code: 'project.view',
          module: 'project',
          description: '查看项目信息',
          type: 'menu',
        },
        {
          id: 'project.create',
          name: '创建项目',
          code: 'project.create',
          module: 'project',
          description: '创建新项目',
          type: 'action',
        },
        {
          id: 'system.user.view',
          name: '查看用户',
          code: 'system.user.view',
          module: 'system',
          description: '查看用户管理',
          type: 'menu',
        },
        {
          id: 'system.user.create',
          name: '创建用户',
          code: 'system.user.create',
          module: 'system',
          description: '创建新用户',
          type: 'action',
        },
        {
          id: 'system.role.view',
          name: '查看角色',
          code: 'system.role.view',
          module: 'system',
          description: '查看角色管理',
          type: 'menu',
        },
        {
          id: 'system.role.create',
          name: '创建角色',
          code: 'system.role.create',
          module: 'system',
          description: '创建新角色',
          type: 'action',
        },
      ];
      setPermissions(mockPermissions);
      const treeData = buildPermissionTree(mockPermissions);
      setPermissionTreeData(treeData);
    } catch {
      message.error('加载权限列表失败');
    }
  }, [buildPermissionTree]);

  const loadStatistics = React.useCallback(() => {
    try {
      // 模拟统计数据
      const mockStats: RoleStatistics = {
        total: roles.length,
        active: roles.filter(r => r.status === 'active').length,
        inactive: roles.filter(r => r.status === 'inactive').length,
        system: roles.filter(r => r.is_system).length,
        custom: roles.filter(r => !r.is_system).length,
        avg_permissions:
          roles.length > 0
            ? Math.round(roles.reduce((sum, r) => sum + r.permissions.length, 0) / roles.length)
            : 0,
      };
      setStatistics(mockStats);
    } catch {
      message.error('加载统计信息失败');
    }
  }, [roles]);

  useEffect(() => {
    void loadRoles();
    void loadPermissions();
  }, [loadRoles, loadPermissions]);

  useEffect(() => {
    void loadStatistics();
  }, [loadStatistics]);

  const handleSearch = (value: string) => {
    _setSearchText(value);
    // 这里可以添加搜索逻辑
  };

  const handleCreate = () => {
    setEditingRole(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    form.setFieldsValue({
      name: role.name,
      code: role.code,
      description: role.description,
      status: role.status,
    });
    setModalVisible(true);
  };

  const handleDelete = (_id: string) => {
    try {
      // 模拟删除API调用
      message.success('删除成功');
      void loadRoles();
    } catch {
      message.error('删除失败');
    }
  };

  const handleToggleStatus = (_role: Role, _newStatus: string) => {
    try {
      // 模拟状态切换API调用
      message.success('状态已更新');
      void loadRoles();
    } catch {
      message.error('状态更新失败');
    }
  };

  const handleManagePermissions = (role: Role) => {
    setSelectedRole(role);
    setTargetPermissions(role.permissions);
    setPermissionModalVisible(true);
  };

  const handleSubmit = (_values: {
    name: string;
    description?: string;
    permissions?: string[];
    isActive?: boolean;
  }) => {
    try {
      if (editingRole) {
        // 模拟更新API调用
        message.success('更新成功');
      } else {
        // 模拟创建API调用
        message.success('创建成功');
      }
      setModalVisible(false);
      void loadRoles();
    } catch {
      message.error(editingRole ? '更新失败' : '创建失败');
    }
  };

  const handleSavePermissions = () => {
    try {
      // 模拟保存权限API调用
      message.success('权限配置已保存');
      setPermissionModalVisible(false);
      void loadRoles();
    } catch {
      message.error('保存权限失败');
    }
  };

  const getStatusTag = (status: string) => {
    const statusConfig = statusOptions.find(s => s.value === status);
    return <Tag color={statusConfig?.color ?? 'default'}>{statusConfig?.label ?? status}</Tag>;
  };

  const columns: ColumnsType<Role> = [
    {
      title: '角色信息',
      key: 'role_info',
      render: (_, record) => (
        <Space>
          <TeamOutlined style={{ color: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.name}</div>
            <div style={{ fontSize: '12px', color: '#666' }}>
              {record.code}
              {record.is_system && (
                <Tag color="purple" style={{ marginLeft: 8 }}>
                  系统角色
                </Tag>
              )}
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '权限数量',
      dataIndex: 'permissions',
      key: 'permissions',
      render: (perms: string[]) => <Badge count={perms.length} showZero color="#1890ff" />,
    },
    {
      title: '用户数量',
      dataIndex: 'user_count',
      key: 'user_count',
      render: (count: number) => <Badge count={count} showZero color="#52c41a" />,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              disabled={record.is_system}
            />
          </Tooltip>
          <Tooltip title="权限配置">
            <Button
              type="link"
              size="small"
              icon={<KeyOutlined />}
              onClick={() => handleManagePermissions(record)}
            />
          </Tooltip>
          <Tooltip title={record.status === 'active' ? '停用' : '启用'}>
            <Switch
              size="small"
              checked={record.status === 'active'}
              onChange={checked => handleToggleStatus(record, checked ? 'active' : 'inactive')}
              disabled={record.is_system}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个角色吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={record.is_system}
          >
            <Tooltip title="删除">
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
                disabled={record.is_system}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Transfer组件的数据转换
  const transferData: TransferItem[] = permissions.map(permission => ({
    key: permission.id,
    title: permission.name,
    description: `${permission.code} - ${permission.description}`,
  }));

  return (
    <>
      <SystemBreadcrumb />
      <div style={{ padding: '24px' }}>
        {statistics && (
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic title="总角色数" value={statistics.total} prefix={<TeamOutlined />} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="启用角色"
                  value={statistics.active}
                  prefix={<SafetyOutlined />}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="系统角色"
                  value={statistics.system}
                  prefix={<SettingOutlined />}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="平均权限数"
                  value={statistics.avg_permissions}
                  prefix={<KeyOutlined />}
                  suffix="个"
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
                    placeholder="搜索角色名称或编码"
                    allowClear
                    style={{ width: 300 }}
                    onSearch={handleSearch}
                  />
                  <Select
                    placeholder="状态筛选"
                    allowClear
                    style={{ width: 120 }}
                    onChange={_setStatusFilter}
                  >
                    {statusOptions.map(status => (
                      <Option key={status.value} value={status.value}>
                        {status.label}
                      </Option>
                    ))}
                  </Select>
                  <Button icon={<ReloadOutlined />} onClick={loadRoles}>
                    刷新
                  </Button>
                </Space>
              </Col>
              <Col>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  新建角色
                </Button>
              </Col>
            </Row>
          </div>

          <Table
            columns={columns}
            dataSource={roles}
            rowKey="id"
            loading={loading}
            pagination={{
              total: roles.length,
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: total => `共 ${total} 条记录`,
            }}
          />
        </Card>

        {/* 创建/编辑模态框 */}
        <Modal
          title={editingRole ? '编辑角色' : '新建角色'}
          open={modalVisible}
          onCancel={() => setModalVisible(false)}
          footer={null}
          width={600}
        >
          <Form form={form} layout="vertical" onFinish={handleSubmit}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="name"
                  label="角色名称"
                  rules={[{ required: true, message: '请输入角色名称' }]}
                >
                  <Input placeholder="请输入角色名称" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="code"
                  label="角色编码"
                  rules={[
                    { required: true, message: '请输入角色编码' },
                    {
                      pattern: /^[a-z_][a-z0-9_]*$/,
                      message: '编码只能包含小写字母、数字和下划线，且不能以数字开头',
                    },
                  ]}
                >
                  <Input placeholder="请输入角色编码" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="description"
              label="角色描述"
              rules={[{ required: true, message: '请输入角色描述' }]}
            >
              <TextArea rows={3} placeholder="请输入角色描述" />
            </Form.Item>

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

            <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
              <Space>
                <Button onClick={() => setModalVisible(false)}>取消</Button>
                <Button type="primary" htmlType="submit">
                  {editingRole ? '更新' : '创建'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>

        {/* 权限配置模态框 */}
        <Modal
          title={`权限配置 - ${selectedRole?.name}`}
          open={permissionModalVisible}
          onCancel={() => setPermissionModalVisible(false)}
          onOk={handleSavePermissions}
          width={1000}
          okText="保存权限"
          cancelText="取消"
        >
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary">
              为角色 <strong>{selectedRole?.name}</strong> 配置系统权限
            </Text>
          </div>

          <Transfer
            dataSource={transferData}
            targetKeys={targetPermissions}
            onChange={keys => setTargetPermissions(keys as string[])}
            render={item => (
              <div>
                <div style={{ fontWeight: 500 }}>{item.title}</div>
                <div style={{ fontSize: '12px', color: '#666' }}>{item.description}</div>
              </div>
            )}
            listStyle={{
              width: 400,
              height: 400,
            }}
            titles={['可选权限', '已选权限']}
            showSearch
            locale={{ searchPlaceholder: '搜索权限' }}
          />

          <Divider />

          <div>
            <Text strong>权限预览：</Text>
            <div style={{ marginTop: 8, maxHeight: 200, overflow: 'auto' }}>
              <Tree
                treeData={permissionTreeData}
                checkable
                checkedKeys={targetPermissions}
                style={{ background: '#fafafa', padding: 16 }}
              />
            </div>
          </div>
        </Modal>
      </div>
    </>
  );
};

export default RoleManagementPage;
