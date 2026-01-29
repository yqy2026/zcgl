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
import { MessageManager } from '@/utils/messageManager';
import { roleService, type Role } from '../../services/systemService';
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
import { COLORS } from '@/styles/colorMap';

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
  const [rolePage, setRolePage] = useState(1);
  const [rolePageSize, setRolePageSize] = useState(10);
  const [roleTotal, setRoleTotal] = useState(0);

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

  const loadRoles = React.useCallback(async () => {
    setLoading(true);
    try {
      const isActive =
        _statusFilter === 'active' ? true : _statusFilter === 'inactive' ? false : undefined;
      const data = (await roleService.getRoles({
        page: rolePage,
        page_size: rolePageSize,
        search: _searchText || undefined,
        is_active: isActive,
      })) as { items?: any[]; total?: number } | any[];
      const items = Array.isArray(data) ? data : (data.items ?? []);
      const mapped: Role[] = items.map(r => ({
        id: r.id,
        name: r.display_name ?? r.name,
        code: r.name,
        description: r.description ?? '',
        status: r.is_active ? 'active' : 'inactive',
        permissions: Array.isArray(r.permissions) ? r.permissions.map((p: any) => p.id) : [],
        user_count: r.user_count ?? 0,
        created_at: r.created_at,
        updated_at: r.updated_at,
        is_system: !!r.is_system_role,
      }));
      setRoles(mapped);
      const total = Array.isArray(data) ? mapped.length : (data.total ?? mapped.length);
      setRoleTotal(total);
    } catch {
      MessageManager.error('加载角色列表失败');
    } finally {
      setLoading(false);
    }
  }, [_searchText, _statusFilter, rolePage, rolePageSize]);

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

  const loadPermissions = React.useCallback(async () => {
    try {
      const resp = (await roleService.getPermissions()) as {
        data?: Record<string, any[]>;
      };
      const grouped = resp.data ?? {};
      const list: Permission[] = Object.keys(grouped).flatMap(resource =>
        (grouped[resource] ?? []).map((p: any) => ({
          id: p.id,
          name: p.display_name ?? p.name ?? `${p.resource}:${p.action}`,
          code: `${p.resource}.${p.action}`,
          module: p.resource,
          description: p.description ?? '',
          type: p.action === 'view' || p.action === 'read' ? 'menu' : 'action',
        })),
      );
      setPermissions(list);
      const treeData = buildPermissionTree(list);
      setPermissionTreeData(treeData);
    } catch {
      MessageManager.error('加载权限列表失败');
    }
  }, [buildPermissionTree]);

  const loadStatistics = React.useCallback(async () => {
    const fallbackStats: RoleStatistics = {
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
    try {
      const resp = (await roleService.getRoleStatistics()) as {
        data?: {
          total_roles?: number;
          active_roles?: number;
          system_roles?: number;
          custom_roles?: number;
        };
        total_roles?: number;
        active_roles?: number;
        system_roles?: number;
        custom_roles?: number;
      };
      const stats = resp.data ?? resp;
      if (stats && typeof stats.total_roles === 'number') {
        const total = stats.total_roles;
        const active = stats.active_roles ?? 0;
        const system = stats.system_roles ?? 0;
        const custom = stats.custom_roles ?? Math.max(total - system, 0);
        setStatistics({
          total,
          active,
          inactive: Math.max(total - active, 0),
          system,
          custom,
          avg_permissions: fallbackStats.avg_permissions,
        });
        return;
      }
    } catch {
      MessageManager.error('加载统计信息失败');
    }
    setStatistics(fallbackStats);
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
    setRolePage(1);
  };

  const handleStatusFilterChange = (value?: string) => {
    _setStatusFilter(value ?? '');
    setRolePage(1);
  };

  const handleCreate = () => {
    setEditingRole(null);
    form.resetFields();
    setTargetPermissions([]);
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

  const handleDelete = async (id: string) => {
    try {
      await roleService.deleteRole(id);
      MessageManager.success('删除成功');
      void loadRoles();
    } catch {
      MessageManager.error('删除失败');
    }
  };

  const handleToggleStatus = async (role: Role, newStatus: string) => {
    try {
      await roleService.updateRole(role.id, {
        is_active: newStatus === 'active',
      });
      MessageManager.success('状态已更新');
      void loadRoles();
    } catch {
      MessageManager.error('状态更新失败');
    }
  };

  const handleManagePermissions = (role: Role) => {
    setSelectedRole(role);
    setTargetPermissions(role.permissions);
    setPermissionModalVisible(true);
  };

  const handleSubmit = async (values: {
    name: string;
    code: string;
    description: string;
    status: 'active' | 'inactive';
  }) => {
    try {
      if (editingRole) {
        await roleService.updateRole(editingRole.id, {
          display_name: values.name,
          description: values.description,
          is_active: values.status === 'active',
        });
        MessageManager.success('更新成功');
      } else {
        await roleService.createRole({
          name: values.code,
          display_name: values.name,
          description: values.description,
          is_active: values.status === 'active',
          permission_ids: targetPermissions,
        });
        MessageManager.success('创建成功');
      }
      setModalVisible(false);
      void loadRoles();
    } catch {
      MessageManager.error(editingRole ? '更新失败' : '创建失败');
    }
  };

  const handleSavePermissions = async () => {
    try {
      if (selectedRole) {
        await roleService.updateRolePermissions(selectedRole.id, targetPermissions);
      }
      MessageManager.success('权限配置已保存');
      setPermissionModalVisible(false);
      void loadRoles();
    } catch {
      MessageManager.error('保存权限失败');
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
          <TeamOutlined style={{ color: COLORS.primary }} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.name}</div>
            <div style={{ fontSize: '12px', color: COLORS.textSecondary }}>
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
      render: (perms: string[]) => <Badge count={perms.length} showZero color={COLORS.primary} />,
    },
    {
      title: '用户数量',
      dataIndex: 'user_count',
      key: 'user_count',
      render: (count: number) => <Badge count={count} showZero color={COLORS.success} />,
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
                  valueStyle={{ color: COLORS.success }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="系统角色"
                  value={statistics.system}
                  prefix={<SettingOutlined />}
                  valueStyle={{ color: COLORS.primary }}
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
                    onChange={handleStatusFilterChange}
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
              current: rolePage,
              total: roleTotal,
              pageSize: rolePageSize,
              pageSizeOptions: ['10', '20', '50', '100'],
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: total => `共 ${total} 条记录`,
              onChange: (page, pageSize) => {
                setRolePage(page);
                setRolePageSize(pageSize);
              },
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
                  <Input placeholder="请输入角色编码" disabled={editingRole !== null} />
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
                <div style={{ fontSize: '12px', color: COLORS.textSecondary }}>
                  {item.description}
                </div>
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
                style={{ background: COLORS.bgSecondary, padding: 16 }}
              />
            </div>
          </div>
        </Modal>
      </div>
    </>
  );
};

export default RoleManagementPage;
