import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Card,
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
  Tree,
  Transfer,
  Divider,
  Typography,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { roleService, type Role } from '@/services/systemService';
import { useQuery } from '@tanstack/react-query';
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
import { TableWithPagination, ListToolbar, PageContainer } from '@/components/Common';
import styles from './RoleManagementPage.module.css';

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

interface RoleApiPermission {
  id: string;
}

interface RoleApiItem {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  is_active?: boolean;
  permissions?: RoleApiPermission[];
  user_count?: number;
  created_at: string;
  updated_at: string;
  is_system_role?: boolean;
}

type RoleListResponse = { items?: RoleApiItem[]; total?: number } | RoleApiItem[];

interface PermissionApiItem {
  id: string;
  name?: string;
  display_name?: string;
  resource?: string;
  action?: string;
  description?: string;
}

interface PermissionListResponse {
  data?: Record<string, PermissionApiItem[]>;
}

interface RoleStatisticsApiResponse {
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
}

interface RoleStatistics {
  total: number;
  active: number;
  inactive: number;
  system: number;
  custom: number;
  avg_permissions: number;
}

interface RoleFilters {
  keyword: string;
  status: string;
}

interface RoleListQueryResult {
  items: Role[];
  total: number;
}

type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';
type PermissionTagTone = 'primary' | 'success' | 'warning';
type StatusTone = 'success' | 'error' | 'neutral';

const RoleManagementPage: React.FC = () => {
  const [filters, setFilters] = useState<RoleFilters>({
    keyword: '',
    status: '',
  });
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 10,
  });
  const [modalVisible, setModalVisible] = useState(false);
  const [permissionModalVisible, setPermissionModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [targetPermissions, setTargetPermissions] = useState<string[]>([]);

  const [form] = Form.useForm();
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
    neutral: styles.toneNeutral,
  };

  // 状态选项
  const statusOptions = [
    { value: 'active', label: '启用', tone: 'success' as const },
    { value: 'inactive', label: '停用', tone: 'error' as const },
  ];

  const getToneClassName = useCallback(
    (tone: Tone): string => {
      return toneClassMap[tone];
    },
    [toneClassMap]
  );

  // 权限模块选项
  const permissionModules = useMemo(
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

  const fetchRoleList = useCallback(async (): Promise<RoleListQueryResult> => {
    const isActive =
      filters.status === 'active' ? true : filters.status === 'inactive' ? false : undefined;
    const trimmedKeyword = filters.keyword.trim();
    const data = (await roleService.getRoles({
      page: paginationState.current,
      page_size: paginationState.pageSize,
      search: trimmedKeyword !== '' ? trimmedKeyword : undefined,
      is_active: isActive,
    })) as RoleListResponse;
    const items = Array.isArray(data) ? data : (data.items ?? []);
    const mapped: Role[] = items.map(roleItem => ({
      id: roleItem.id,
      name: roleItem.display_name ?? roleItem.name,
      code: roleItem.name,
      description: roleItem.description ?? '',
      status: roleItem.is_active === true ? 'active' : 'inactive',
      permissions: Array.isArray(roleItem.permissions)
        ? roleItem.permissions.map(permission => permission.id)
        : [],
      user_count: roleItem.user_count ?? 0,
      created_at: roleItem.created_at,
      updated_at: roleItem.updated_at,
      is_system: roleItem.is_system_role === true,
    }));
    const total = Array.isArray(data) ? mapped.length : (data.total ?? mapped.length);
    return { items: mapped, total };
  }, [filters.keyword, filters.status, paginationState.current, paginationState.pageSize]);

  const {
    data: rolesResponse,
    error: rolesError,
    isLoading: isRolesLoading,
    isFetching: isRolesFetching,
    refetch: refetchRoles,
  } = useQuery<RoleListQueryResult>({
    queryKey: ['role-management-list', paginationState.current, paginationState.pageSize, filters],
    queryFn: fetchRoleList,
    retry: false,
  });

  const getPermissionTypeTone = useCallback((type: Permission['type']): PermissionTagTone => {
    switch (type) {
      case 'menu':
        return 'primary';
      case 'action':
        return 'success';
      default:
        return 'warning';
    }
  }, []);

  const getPermissionTypeLabel = useCallback((type: Permission['type']): string => {
    switch (type) {
      case 'menu':
        return '菜单';
      case 'action':
        return '操作';
      default:
        return '数据';
    }
  }, []);

  const getPermissionTypeToneClassName = useCallback(
    (type: Permission['type']): string => {
      const tone = getPermissionTypeTone(type);
      return getToneClassName(tone);
    },
    [getPermissionTypeTone, getToneClassName]
  );

  const getStatusToneClassName = useCallback((tone: StatusTone): string => {
    return getToneClassName(tone);
  }, [getToneClassName]);

  const buildPermissionTree = useCallback(
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
                className={`${styles.permissionTypeTag} ${getPermissionTypeToneClassName(permission.type)}`}
              >
                {getPermissionTypeLabel(permission.type)}
              </Tag>
            </Space>
          ),
        });
      });

      return Object.values(moduleMap);
    },
    [getPermissionTypeLabel, getPermissionTypeToneClassName, permissionModules]
  );

  const {
    data: permissions = [],
    error: permissionsError,
  } = useQuery<Permission[]>({
    queryKey: ['role-management-permissions'],
    queryFn: async () => {
      const resp = (await roleService.getPermissions()) as PermissionListResponse;
      const grouped = resp.data ?? {};
      return Object.keys(grouped).flatMap(resource =>
        (grouped[resource] ?? []).map(p => {
          const action = p.action ?? 'action';
          const resourceKey = p.resource ?? resource;
          return {
            id: p.id,
            name: p.display_name ?? `${resourceKey}:${action}`,
            code: `${resourceKey}.${action}`,
            module: resourceKey,
            description: p.description ?? '',
            type: action === 'view' || action === 'read' ? 'menu' : 'action',
          };
        })
      );
    },
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  const {
    data: statisticsResponse,
    error: statisticsError,
    refetch: refetchStatistics,
  } = useQuery<RoleStatisticsApiResponse>({
    queryKey: ['role-management-statistics'],
    queryFn: async () => (await roleService.getRoleStatistics()) as RoleStatisticsApiResponse,
    staleTime: 60 * 1000,
    retry: false,
  });

  useEffect(() => {
    if (rolesError != null) {
      MessageManager.error('加载角色列表失败');
    }
  }, [rolesError]);

  useEffect(() => {
    if (permissionsError != null) {
      MessageManager.error('加载权限列表失败');
    }
  }, [permissionsError]);

  useEffect(() => {
    if (statisticsError != null) {
      MessageManager.error('加载统计信息失败');
    }
  }, [statisticsError]);

  const roles = rolesResponse?.items ?? [];
  const loading = isRolesLoading || isRolesFetching;
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: rolesResponse?.total ?? 0,
    }),
    [paginationState.current, paginationState.pageSize, rolesResponse?.total]
  );
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.keyword.trim() !== '') {
      count += 1;
    }
    if (filters.status !== '') {
      count += 1;
    }
    return count;
  }, [filters.keyword, filters.status]);

  const permissionTreeData = useMemo(() => buildPermissionTree(permissions), [
    buildPermissionTree,
    permissions,
  ]);

  const statistics = useMemo<RoleStatistics>(() => {
    const fallbackStats: RoleStatistics = {
      total: roles.length,
      active: roles.filter(role => role.status === 'active').length,
      inactive: roles.filter(role => role.status === 'inactive').length,
      system: roles.filter(role => role.is_system).length,
      custom: roles.filter(role => !role.is_system).length,
      avg_permissions:
        roles.length > 0
          ? Math.round(
              roles.reduce((sum, role) => sum + role.permissions.length, 0) / roles.length
            )
          : 0,
    };

    const stats = statisticsResponse?.data ?? statisticsResponse;
    if (stats != null && typeof stats.total_roles === 'number') {
      const total = stats.total_roles;
      const active = stats.active_roles ?? 0;
      const system = stats.system_roles ?? 0;
      const custom = stats.custom_roles ?? Math.max(total - system, 0);
      return {
        total,
        active,
        inactive: Math.max(total - active, 0),
        system,
        custom,
        avg_permissions: fallbackStats.avg_permissions,
      };
    }

    return fallbackStats;
  }, [roles, statisticsResponse]);

  const refreshRolesAndStatistics = useCallback(() => {
    void refetchRoles();
    void refetchStatistics();
  }, [refetchRoles, refetchStatistics]);

  const updateFilters = useCallback((nextFilters: Partial<RoleFilters>) => {
    setFilters(prev => ({ ...prev, ...nextFilters }));
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handleSearch = useCallback(
    (value: string) => {
      updateFilters({ keyword: value });
    },
    [updateFilters]
  );

  const handleStatusFilterChange = useCallback(
    (value?: string) => {
      updateFilters({ status: value ?? '' });
    },
    [updateFilters]
  );

  const handlePageChange = useCallback((next: { current?: number; pageSize?: number }) => {
    setPaginationState(prev => ({
      current: next.current ?? prev.current,
      pageSize: next.pageSize ?? prev.pageSize,
    }));
  }, []);

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
      refreshRolesAndStatistics();
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
      refreshRolesAndStatistics();
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
      refreshRolesAndStatistics();
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
      refreshRolesAndStatistics();
    } catch {
      MessageManager.error('保存权限失败');
    }
  };

  const getStatusTag = (status: string) => {
    const statusConfig = statusOptions.find(s => s.value === status);
    const tone = statusConfig?.tone ?? 'neutral';
    return (
      <Tag className={`${styles.statusTag} ${getStatusToneClassName(tone)}`}>
        {statusConfig?.label ?? status}
      </Tag>
    );
  };

  const columns: ColumnsType<Role> = [
    {
      title: '角色信息',
      key: 'role_info',
      render: (_, record) => (
        <Space size={10} className={styles.roleInfoCell}>
          <TeamOutlined className={styles.roleInfoIcon} />
          <div className={styles.roleMeta}>
            <div className={styles.roleName}>{record.name}</div>
            <div className={styles.roleCodeRow}>
              {record.code}
              {record.is_system && (
                <Tag className={`${styles.statusTag} ${styles.systemTag} ${styles.toneWarning}`}>
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
      render: (perms: string[]) => (
        <span className={`${styles.countPill} ${styles.tonePrimary}`}>{`${perms.length} 项`}</span>
      ),
    },
    {
      title: '用户数量',
      dataIndex: 'user_count',
      key: 'user_count',
      render: (count: number) => (
        <span className={`${styles.countPill} ${styles.toneSuccess}`}>{`${count} 人`}</span>
      ),
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
        <Space size={4} className={styles.tableActionGroup}>
          <Tooltip title="编辑">
            <Button
              type="text"
              className={styles.tableActionButton}
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              disabled={record.is_system}
              aria-label="编辑"
            />
          </Tooltip>
          <Tooltip title="权限配置">
            <Button
              type="text"
              className={styles.tableActionButton}
              icon={<KeyOutlined />}
              onClick={() => handleManagePermissions(record)}
              aria-label="权限配置"
            />
          </Tooltip>
          <Tooltip title={record.status === 'active' ? '停用' : '启用'}>
            <Switch
              checked={record.status === 'active'}
              onChange={checked => handleToggleStatus(record, checked ? 'active' : 'inactive')}
              disabled={record.is_system}
              checkedChildren="启"
              unCheckedChildren="停"
              className={styles.statusSwitch}
              aria-label={record.status === 'active' ? '停用' : '启用'}
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
                type="text"
                danger
                className={styles.tableActionButton}
                icon={<DeleteOutlined />}
                disabled={record.is_system}
                aria-label="删除"
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
    <PageContainer title="角色管理" subTitle="管理系统角色和权限配置">
      {statistics != null && (
        <Row gutter={[16, 16]} className={styles.statsRow}>
          <Col xs={24} sm={12} xl={6}>
            <Card className={styles.statsCard}>
              <Statistic title="总角色数" value={statistics.total} prefix={<TeamOutlined />} />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card className={`${styles.statsCard} ${styles.toneSuccess}`}>
              <Statistic
                title="启用角色"
                value={statistics.active}
                prefix={<SafetyOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card className={`${styles.statsCard} ${styles.tonePrimary}`}>
              <Statistic
                title="系统角色"
                value={statistics.system}
                prefix={<SettingOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card className={styles.statsCard}>
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

      <Card className={styles.rolesCard}>
        <div className={styles.filtersSection}>
          <div className={styles.filterSummary} aria-live="polite">
            <Text type="secondary">共 {pagination.total} 条角色记录</Text>
            <Text type="secondary">
              {activeFilterCount > 0 ? `已启用 ${activeFilterCount} 项筛选` : '未启用筛选条件'}
            </Text>
          </div>
          <ListToolbar
            variant="plain"
            items={[
              {
                key: 'search',
                col: { xs: 24, sm: 12, md: 10, lg: 8 },
                content: (
                  <Search
                    placeholder="搜索角色名称或编码"
                    allowClear
                    className={styles.fullWidthControl}
                    value={filters.keyword}
                    onSearch={handleSearch}
                    onChange={event => handleSearch(event.target.value)}
                  />
                ),
              },
              {
                key: 'status',
                col: { xs: 24, sm: 12, md: 6, lg: 4 },
                content: (
                  <Select
                    placeholder="状态筛选"
                    allowClear
                    className={styles.fullWidthControl}
                    value={filters.status !== '' ? filters.status : undefined}
                    onChange={handleStatusFilterChange}
                  >
                    {statusOptions.map(status => (
                      <Option key={status.value} value={status.value}>
                        {status.label}
                      </Option>
                    ))}
                  </Select>
                ),
              },
              {
                key: 'refresh',
                col: { xs: 24, sm: 12, md: 4, lg: 3 },
                content: (
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={refreshRolesAndStatistics}
                    loading={loading}
                    disabled={loading}
                    className={styles.toolbarButton}
                    aria-label="刷新角色列表"
                  >
                    刷新
                  </Button>
                ),
              },
              {
                key: 'create',
                col: { xs: 24, sm: 12, md: 4, lg: 3 },
                content: (
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={handleCreate}
                    className={styles.toolbarButton}
                    aria-label="新建角色"
                  >
                    新建角色
                  </Button>
                ),
              },
            ]}
          />
        </div>

        <TableWithPagination
          columns={columns}
          dataSource={roles}
          rowKey="id"
          loading={loading}
          paginationState={pagination}
          onPageChange={handlePageChange}
          scroll={{ x: 1100 }}
          paginationProps={{
            pageSizeOptions: ['10', '20', '50', '100'],
            showTotal: (total: number) => `共 ${total} 条记录`,
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
            <Col xs={24} sm={12}>
              <Form.Item
                name="name"
                label="角色名称"
                rules={[{ required: true, message: '请输入角色名称' }]}
              >
                <Input placeholder="请输入角色名称" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
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

          <Form.Item className={styles.modalFooter}>
            <Space size={8} className={styles.modalFooterActions}>
              <Button className={styles.modalActionButton} onClick={() => setModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" className={styles.modalActionButton}>
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
        okButtonProps={{
          className: styles.permissionModalActionButton,
        }}
        cancelButtonProps={{
          className: styles.permissionModalActionButton,
        }}
      >
        <div className={styles.permissionDesc}>
          <Text type="secondary">
            为角色 <strong>{selectedRole?.name}</strong> 配置系统权限
          </Text>
        </div>

        <Transfer
          dataSource={transferData}
          targetKeys={targetPermissions}
          onChange={keys => setTargetPermissions(keys as string[])}
          className={styles.permissionTransfer}
          render={item => (
            <div>
              <div className={styles.transferTitle}>{item.title}</div>
              <div className={styles.transferDesc}>{item.description}</div>
            </div>
          )}
          titles={['可选权限', '已选权限']}
          showSearch
          locale={{ searchPlaceholder: '搜索权限' }}
        />

        <Divider />

        <div>
          <Text strong>权限预览：</Text>
          <div className={styles.treePreview}>
            <Tree
              treeData={permissionTreeData}
              checkable
              checkedKeys={targetPermissions}
              className={styles.permissionTree}
            />
          </div>
        </div>
      </Modal>
    </PageContainer>
  );
};

export default RoleManagementPage;
