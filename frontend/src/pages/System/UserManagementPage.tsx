import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { pinyin } from 'pinyin-pro';
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
  Avatar,
  Switch,
  Drawer,
  Descriptions,
} from 'antd';
import {
  userService,
  roleService,
  type User,
  type CreateUserData,
  type UpdateUserData,
  type OrganizationOption,
  type RoleOption,
} from '@/services/systemService';
import { organizationService } from '@/services/organizationService';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import { useQuery } from '@tanstack/react-query';
import { TableWithPagination, ListToolbar, PageContainer } from '@/components/Common';
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
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import styles from './UserManagementPage.module.css';

const pageLogger = createLogger('UserManagement');

const { Option } = Select;
const { Search } = Input;

// User类型已从systemService导入

type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';
type UserStatus = User['status'];

interface StatusMeta {
  label: string;
  hint: string;
  tone: Tone;
}

const STATUS_META_MAP: Record<UserStatus, StatusMeta> = {
  active: { label: '活跃', hint: '可登录', tone: 'success' },
  inactive: { label: '停用', hint: '已禁用', tone: 'error' },
  locked: { label: '锁定', hint: '异常冻结', tone: 'warning' },
};

const USER_STATUS_FILTER_OPTIONS: Array<{ value: UserStatus; label: string }> = [
  { value: 'active', label: STATUS_META_MAP.active.label },
  { value: 'inactive', label: STATUS_META_MAP.inactive.label },
  { value: 'locked', label: STATUS_META_MAP.locked.label },
];

const USER_STATUS_FORM_OPTIONS: Array<{ value: 'active' | 'inactive'; label: string }> = [
  { value: 'active', label: STATUS_META_MAP.active.label },
  { value: 'inactive', label: STATUS_META_MAP.inactive.label },
];

const getToneClassName = (tone: Tone): string => {
  if (tone === 'primary') {
    return styles.tonePrimary;
  }
  if (tone === 'success') {
    return styles.toneSuccess;
  }
  if (tone === 'warning') {
    return styles.toneWarning;
  }
  if (tone === 'error') {
    return styles.toneError;
  }
  return styles.toneNeutral;
};

interface UserStatistics {
  total: number;
  active: number;
  inactive: number;
  locked: number;
  by_role: Record<string, number>;
  by_organization: Record<string, number>;
}

interface UserFilters {
  keyword: string;
  status: string;
  roleId: string;
  organizationId: string;
}

interface UsersQueryResult {
  items: User[];
  total: number;
}

const UserManagementPage: React.FC = () => {
  const [filters, setFilters] = useState<UserFilters>({
    keyword: '',
    status: '',
    roleId: '',
    organizationId: '',
  });
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 10,
  });
  const [modalVisible, setModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const [form] = Form.useForm();

  const fetchUsers = useCallback(async (): Promise<UsersQueryResult> => {
    const trimmedKeyword = filters.keyword.trim();
    const response = await userService.getUsers({
      page: paginationState.current,
      page_size: paginationState.pageSize,
      search: trimmedKeyword !== '' ? trimmedKeyword : undefined,
      status: filters.status !== '' ? filters.status : undefined,
      role_id: filters.roleId !== '' ? filters.roleId : undefined,
      default_organization_id: filters.organizationId !== '' ? filters.organizationId : undefined,
    });
    return { items: response.items ?? [], total: response.total ?? 0 };
  }, [
    filters.keyword,
    filters.organizationId,
    filters.roleId,
    filters.status,
    paginationState.current,
    paginationState.pageSize,
  ]);

  const {
    data: usersResponse,
    error: usersError,
    isLoading: isUsersLoading,
    isFetching: isUsersFetching,
    refetch: refetchUsers,
  } = useQuery<UsersQueryResult>({
    queryKey: ['user-management-list', paginationState.current, paginationState.pageSize, filters],
    queryFn: fetchUsers,
    retry: 1,
  });

  const { data: organizations = [], error: organizationsError } = useQuery<OrganizationOption[]>({
    queryKey: ['user-management-organizations'],
    queryFn: async () => {
      const data = await organizationService.getOrganizations({ page_size: 1000 });
      return data.map(org => ({ id: org.id, name: org.name }));
    },
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const { data: roles = [], error: rolesError } = useQuery<RoleOption[]>({
    queryKey: ['user-management-roles'],
    queryFn: async () => {
      const data = await roleService.getRoles({ page_size: 100 });
      const roleItems = Array.isArray(data)
        ? data
        : Array.isArray((data as { items?: unknown[] }).items)
          ? (data as { items: unknown[] }).items
          : Array.isArray((data as { data?: unknown[] }).data)
            ? (data as { data: unknown[] }).data
            : [];

      return roleItems
        .map(role => {
          const roleRecord = role as { id?: string; code?: string; name?: string };
          return {
            id: roleRecord.id ?? roleRecord.code ?? '',
            name: roleRecord.name ?? roleRecord.code ?? '',
          };
        })
        .filter(role => role.id.length > 0);
    },
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const {
    data: statisticsResponse,
    error: statisticsError,
    refetch: refetchStatistics,
    isFetched: isStatisticsFetched,
  } = useQuery<unknown>({
    queryKey: ['user-management-statistics'],
    queryFn: () => userService.getUserStatistics(),
    staleTime: 60 * 1000,
    retry: 1,
  });

  useEffect(() => {
    if (usersError != null) {
      pageLogger.error('加载用户列表失败:', usersError);
      MessageManager.error('加载用户列表失败');
    }
  }, [usersError]);

  useEffect(() => {
    if (organizationsError != null) {
      pageLogger.error('加载组织列表失败:', organizationsError);
      MessageManager.error('加载组织列表失败');
    }
  }, [organizationsError]);

  useEffect(() => {
    if (rolesError != null) {
      pageLogger.error('加载角色列表失败:', rolesError);
      MessageManager.error('加载角色列表失败');
    }
  }, [rolesError]);

  useEffect(() => {
    if (statisticsError != null) {
      pageLogger.error('加载统计信息失败:', statisticsError);
      MessageManager.error('加载统计信息失败');
    }
  }, [statisticsError]);

  const users = usersResponse?.items ?? [];
  const loading = isUsersLoading || isUsersFetching;
  const isRefreshing = isUsersFetching === true;
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: usersResponse?.total ?? 0,
    }),
    [paginationState.current, paginationState.pageSize, usersResponse?.total]
  );
  const enabledFilterCount = [filters.keyword, filters.status, filters.roleId, filters.organizationId].filter(
    value => value.trim() !== ''
  ).length;

  const statistics = useMemo<UserStatistics | null>(() => {
    if (statisticsError != null) {
      return null;
    }
    if (!isStatisticsFetched) {
      return null;
    }
    if (
      statisticsResponse != null &&
      typeof statisticsResponse === 'object' &&
      'total' in statisticsResponse &&
      'active' in statisticsResponse &&
      'inactive' in statisticsResponse &&
      'locked' in statisticsResponse
    ) {
      return statisticsResponse as UserStatistics;
    }
    return {
      total: users.length,
      active: users.filter(user => user.status === 'active').length,
      inactive: users.filter(user => user.status === 'inactive').length,
      locked: users.filter(user => user.status === 'locked').length,
      by_role: {},
      by_organization: {},
    };
  }, [isStatisticsFetched, statisticsError, statisticsResponse, users]);

  const refreshUsersAndStatistics = useCallback(() => {
    void refetchUsers();
    void refetchStatistics();
  }, [refetchUsers, refetchStatistics]);

  const updateFilters = useCallback((nextFilters: Partial<UserFilters>) => {
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

  const handleRoleFilterChange = useCallback(
    (value?: string) => {
      updateFilters({ roleId: value ?? '' });
    },
    [updateFilters]
  );

  const handleOrganizationFilterChange = useCallback(
    (value?: string) => {
      updateFilters({ organizationId: value ?? '' });
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
    setEditingUser(null);
    form.resetFields();
    // 设置新建用户的默认值
    form.setFieldsValue({ status: 'active' });
    setModalVisible(true);
  };

  // 姓名变化时自动填充用户名（仅新建时）
  const handleFullNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value;
    if (editingUser == null && name.trim() !== '') {
      // 仅新建时自动填充，编辑时不覆盖
      const pinyinName = pinyin(name, { toneType: 'none', type: 'array' }).join('');
      form.setFieldsValue({ username: pinyinName.toLowerCase() });
    }
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      full_name: user.full_name,
      phone: user.phone,
      status: user.status,
      role_id: user.role_id,
      default_organization_id: user.default_organization_id,
    });
    setModalVisible(true);
  };

  const handleDelete = async (_id: string) => {
    try {
      await userService.deleteUser(_id);
      MessageManager.success('删除成功');
      refreshUsersAndStatistics();
    } catch (error) {
      pageLogger.error('删除用户失败:', error as Error);
      MessageManager.error('删除失败');
    }
  };

  const handleToggleStatus = async (_user: User, _newStatus: string) => {
    try {
      await userService.updateUser(_user.id, { status: _newStatus as 'active' | 'inactive' });
      MessageManager.success('状态已更新');
      refreshUsersAndStatistics();
    } catch (error) {
      pageLogger.error('更新用户状态失败:', error as Error);
      MessageManager.error('状态更新失败');
    }
  };

  const handleToggleLock = async (user: User) => {
    try {
      if (user.is_locked) {
        await userService.unlockUser(user.id);
      } else {
        await userService.lockUser(user.id);
      }
      MessageManager.success(user.is_locked ? '用户已解锁' : '用户已锁定');
      refreshUsersAndStatistics();
    } catch (error) {
      pageLogger.error('更新用户锁定状态失败:', error as Error);
      MessageManager.error('操作失败');
    }
  };

  const handleViewDetail = (user: User) => {
    setSelectedUser(user);
    setDetailDrawerVisible(true);
  };

  const handleSubmit = async (_values: CreateUserData | UpdateUserData) => {
    try {
      if (editingUser) {
        await userService.updateUser(editingUser.id, _values as UpdateUserData);
        MessageManager.success('更新成功');
      } else {
        await userService.createUser(_values as CreateUserData);
        MessageManager.success('创建成功');
      }
      setModalVisible(false);
      refreshUsersAndStatistics();
    } catch (error) {
      pageLogger.error('保存用户失败:', error as Error);
      MessageManager.error(editingUser ? '更新失败' : '创建失败');
    }
  };

  const getStatusTag = (status: UserStatus) => {
    const statusMeta = STATUS_META_MAP[status];
    return (
      <Tag className={`${styles.semanticTag} ${styles.statusTag} ${getToneClassName(statusMeta.tone)}`}>
        {statusMeta.label}
        <span className={styles.statusHint}>{statusMeta.hint}</span>
      </Tag>
    );
  };

  const columns: ColumnsType<User> = [
    {
      title: '用户信息',
      key: 'user_info',
      render: (_, record) => (
        <Space className={styles.userCell}>
          <Avatar icon={<UserOutlined />} />
          <div className={styles.userTextGroup}>
            <div className={styles.userNameText}>{record.full_name}</div>
            <div className={styles.secondaryText}>@{record.username}</div>
          </div>
        </Space>
      ),
    },
    {
      title: '联系方式',
      key: 'contact',
      render: (_, record) => (
        <div className={styles.contactCell}>
          <div>{record.email}</div>
          <div className={styles.secondaryText}>{record.phone ?? '未设置'}</div>
        </div>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role_name',
      key: 'role',
      render: (role?: string) => {
        const roleLabel = role ?? '未分配';
        return (
          <Tag className={`${styles.semanticTag} ${styles.roleTag} ${styles.tonePrimary}`}>
            {roleLabel}
          </Tag>
        );
      },
    },
    {
      title: '组织',
      dataIndex: 'organization_name',
      key: 'organization',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: UserStatus, record: User) => (
        <Space size={[8, 6]} wrap>
          {getStatusTag(status)}
          {record.is_locked && (
            <Tag className={`${styles.semanticTag} ${styles.lockStateTag} ${styles.toneError}`}>
              已锁定
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login',
      key: 'last_login',
      render: date =>
        date !== null && date !== undefined ? dayjs(date).format('YYYY-MM-DD HH:mm') : '从未登录',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size={4} className={styles.actionGroup}>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              className={styles.tableActionButton}
              onClick={() => handleViewDetail(record)}
              aria-label={`查看用户${record.username}详情`}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              className={styles.tableActionButton}
              onClick={() => handleEdit(record)}
              aria-label={`编辑用户${record.username}`}
            />
          </Tooltip>
          <Tooltip title={record.is_locked ? '解锁' : '锁定'}>
            <Button
              type="text"
              icon={record.is_locked ? <UnlockOutlined /> : <LockOutlined />}
              onClick={() => handleToggleLock(record)}
              className={`${styles.tableActionButton} ${
                record.is_locked ? styles.unlockActionButton : styles.lockActionButton
              }`}
              aria-label={record.is_locked ? `解锁用户${record.username}` : `锁定用户${record.username}`}
            />
          </Tooltip>
          <Tooltip title={record.status === 'active' ? '停用' : '启用'}>
            <Switch
              size="small"
              checked={record.status === 'active'}
              onChange={checked => handleToggleStatus(record, checked ? 'active' : 'inactive')}
              checkedChildren="启"
              unCheckedChildren="停"
              className={styles.statusSwitch}
              aria-label={record.status === 'active' ? `停用用户${record.username}` : `启用用户${record.username}`}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个用户吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            icon={<ExclamationCircleOutlined className={styles.dangerIcon} />}
          >
            <Tooltip title="删除">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                className={styles.tableActionButton}
                aria-label={`删除用户${record.username}`}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer title="用户管理" subTitle="管理系统用户账户和权限">
      {/* 统计卡片 */}
      {statistics != null && (
        <Row gutter={[16, 16]} className={styles.statsRow}>
          <Col xs={24} sm={12} md={6}>
            <Card className={`${styles.statsCard} ${styles.tonePrimary}`}>
              <Statistic title="总用户数" value={statistics.total} prefix={<UserOutlined />} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={`${styles.statsCard} ${styles.activeStatsCard}`}>
              <Statistic
                title="活跃用户"
                value={statistics.active}
                prefix={<TeamOutlined />}
                suffix={<span className={styles.totalSuffix}>/ {statistics.total}</span>}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={`${styles.statsCard} ${styles.inactiveStatsCard}`}>
              <Statistic title="停用用户" value={statistics.inactive} prefix={<SettingOutlined />} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={`${styles.statsCard} ${styles.lockedStatsCard}`}>
              <Statistic title="锁定用户" value={statistics.locked} prefix={<LockOutlined />} />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <div className={styles.toolbarSection}>
          <ListToolbar
            variant="plain"
            items={[
              {
                key: 'search',
                col: { xs: 24, sm: 12, md: 10, lg: 8 },
                content: (
                  <Search
                    placeholder="搜索用户名、邮箱或姓名"
                    allowClear
                    className={styles.fullWidthControl}
                    onSearch={handleSearch}
                    aria-label="搜索用户"
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
                    aria-label="按状态筛选用户"
                  >
                    {USER_STATUS_FILTER_OPTIONS.map(status => (
                      <Option key={status.value} value={status.value}>
                        {status.label}
                      </Option>
                    ))}
                  </Select>
                ),
              },
              {
                key: 'role',
                col: { xs: 24, sm: 12, md: 6, lg: 4 },
                content: (
                  <Select
                    placeholder="角色筛选"
                    allowClear
                    className={styles.fullWidthControl}
                    value={filters.roleId !== '' ? filters.roleId : undefined}
                    onChange={handleRoleFilterChange}
                    aria-label="按角色筛选用户"
                  >
                    {roles.map(role => (
                      <Option key={role.id} value={role.id}>
                        {role.name}
                      </Option>
                    ))}
                  </Select>
                ),
              },
              {
                key: 'organization',
                col: { xs: 24, sm: 12, md: 6, lg: 4 },
                content: (
                  <Select
                    placeholder="组织筛选"
                    allowClear
                    className={styles.fullWidthControl}
                    value={filters.organizationId !== '' ? filters.organizationId : undefined}
                    onChange={handleOrganizationFilterChange}
                    aria-label="按组织筛选用户"
                  >
                    {organizations.map(org => (
                      <Option key={org.id} value={org.id}>
                        {org.name}
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
                    onClick={refreshUsersAndStatistics}
                    className={styles.actionButton}
                    loading={isRefreshing}
                    aria-label="刷新用户列表"
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
                    className={styles.actionButton}
                    aria-label="新建系统用户"
                  >
                    新建用户
                  </Button>
                ),
              },
            ]}
          />
        </div>
        <div className={styles.filterSummary}>
          <span className={styles.summaryText}>总记录：{pagination.total}</span>
          <span className={styles.summaryText}>启用筛选：{enabledFilterCount}</span>
        </div>

        <TableWithPagination
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          paginationState={pagination}
          onPageChange={handlePageChange}
          paginationProps={{
            showTotal: (total: number) => `共 ${total} 条记录`,
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
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          {/* 第1行：所属组织（全宽） */}
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="default_organization_id"
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

          {/* 第2行：姓名 + 手机号 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="full_name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
                <Input placeholder="请输入姓名" onChange={handleFullNameChange} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="phone"
                label="手机号"
                rules={[
                  { required: true, message: '请输入手机号' },
                  { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号格式' },
                ]}
              >
                <Input placeholder="请输入手机号" />
              </Form.Item>
            </Col>
          </Row>

          {/* 第3行：用户名 + 邮箱 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="username"
                label="用户名"
                rules={[
                  { required: true, message: '请输入用户名' },
                  { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' },
                ]}
              >
                <Input placeholder="请输入用户名（输入姓名后自动生成拼音）" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="email"
                label="邮箱"
                rules={[{ type: 'email', message: '请输入正确的邮箱格式' }]}
              >
                <Input placeholder="请输入邮箱（选填）" />
              </Form.Item>
            </Col>
          </Row>

          {/* 第4行：密码（仅新建时显示） */}
          {editingUser == null && (
            <Row gutter={16}>
              <Col span={24}>
                <Form.Item
                  name="password"
                  label="密码"
                  rules={[
                    { required: true, message: '请输入密码' },
                    { min: 8, message: '密码至少8位' },
                    {
                      pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$/,
                      message: '密码需包含大小写字母、数字和特殊字符',
                    },
                  ]}
                >
                  <Input.Password placeholder="请输入密码（至少8位，需包含大小写字母、数字和特殊字符）" />
                </Form.Item>
              </Col>
            </Row>
          )}

          {/* 第5行：状态 + 角色 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="status" label="状态">
                <Select placeholder="请选择状态（默认活跃）">
                  {USER_STATUS_FORM_OPTIONS.map(status => (
                    <Option key={status.value} value={status.value}>
                      {status.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="role_id" label="角色">
                <Select placeholder="请选择角色（选填）">
                  {roles.map(role => (
                    <Option key={role.id} value={role.id}>
                      {role.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item className={styles.formActions}>
            <Space>
              <Button onClick={() => setModalVisible(false)} className={styles.actionButton}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" className={styles.actionButton}>
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
        size={600}
      >
        {selectedUser != null && (
          <div>
            <div className={styles.userProfileHeader}>
              <Avatar size={80} icon={<UserOutlined />} />
              <h3 className={styles.userProfileName}>{selectedUser.full_name}</h3>
              <p className={styles.userProfileAccount}>@{selectedUser.username}</p>
            </div>

            <Descriptions column={1} bordered>
              <Descriptions.Item label="用户名">{selectedUser.username}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{selectedUser.email}</Descriptions.Item>
              <Descriptions.Item label="手机号">{selectedUser.phone ?? '未设置'}</Descriptions.Item>
              <Descriptions.Item label="角色">
                <Tag className={`${styles.semanticTag} ${styles.roleTag} ${styles.tonePrimary}`}>
                  {selectedUser.role_name ?? '未分配'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="所属组织">{selectedUser.organization_name}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Space size={[8, 6]} wrap>
                  {getStatusTag(selectedUser.status)}
                  {selectedUser.is_locked && (
                    <Tag className={`${styles.semanticTag} ${styles.lockStateTag} ${styles.toneError}`}>
                      已锁定
                    </Tag>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="最后登录">
                {(selectedUser.last_login !== null && selectedUser.last_login !== undefined) || false
                  ? dayjs(selectedUser.last_login).format('YYYY-MM-DD HH:mm:ss')
                  : '从未登录'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(selectedUser.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {dayjs(selectedUser.updated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            <div className={styles.drawerActions}>
              <Space className={styles.drawerActionsGroup} wrap>
                <Button
                  type="primary"
                  icon={<EditOutlined />}
                  className={styles.actionButton}
                  onClick={() => {
                    setDetailDrawerVisible(false);
                    handleEdit(selectedUser);
                  }}
                >
                  编辑用户
                </Button>
                <Button
                  icon={selectedUser.is_locked ? <UnlockOutlined /> : <LockOutlined />}
                  className={styles.actionButton}
                  onClick={() => {
                    setDetailDrawerVisible(false);
                    handleToggleLock(selectedUser);
                  }}
                >
                  {selectedUser.is_locked ? '解锁账户' : '锁定账户'}
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default UserManagementPage;
