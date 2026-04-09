import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { pinyin } from 'pinyin-pro';
import { Card, Form, Tag } from 'antd';
import { PageContainer } from '@/components/Common';
import {
  type CreateUserData,
  type UpdateUserData,
  type User,
  userService,
} from '@/services/systemService';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';
import { resolveStatusMeta, USER_STATUS_FILTER_OPTIONS, USER_STATUS_FORM_OPTIONS } from './status';
import { useUserManagementData } from './hooks/useUserManagementData';
import type { Tone, UserFilters, UserPaginationState, UserStatus } from './types';
import UserStatisticsCards from './components/UserStatisticsCards';
import UserFiltersToolbar from './components/UserFiltersToolbar';
import UserTable from './components/UserTable';
import UserFormModal from './components/UserFormModal';
import UserDetailDrawer from './components/UserDetailDrawer';
import UserPartyBindingModal from './components/UserPartyBindingModal';
import styles from '../UserManagementPage.module.css';

const pageLogger = createLogger('UserManagement');

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

const UserManagementPage: React.FC = () => {
  const [filters, setFilters] = useState<UserFilters>({
    keyword: '',
    status: '',
    roleId: '',
    organizationId: '',
  });
  const [paginationState, setPaginationState] = useState<UserPaginationState>({
    current: 1,
    pageSize: 10,
  });
  const [modalVisible, setModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [bindingModalVisible, setBindingModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [bindingUser, setBindingUser] = useState<User | null>(null);

  const [form] = Form.useForm();

  const {
    users,
    tablePagination,
    loading,
    isRefreshing,
    organizations,
    roles,
    statistics,
    usersError,
    organizationsError,
    rolesError,
    statisticsError,
    refetchUsers,
    refetchStatistics,
  } = useUserManagementData({
    filters,
    pagination: paginationState,
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

  const refreshUsersAndStatistics = useCallback(() => {
    void refetchUsers();
    void refetchStatistics();
  }, [refetchStatistics, refetchUsers]);

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

  const handleCreate = useCallback(() => {
    setEditingUser(null);
    form.resetFields();
    form.setFieldsValue({ status: 'active' });
    setModalVisible(true);
  }, [form]);

  const handleEdit = useCallback(
    (user: User) => {
      setEditingUser(user);
      form.setFieldsValue({
        username: user.username,
        email: user.email,
        full_name: user.full_name,
        phone: user.phone,
        status: user.status,
        role_ids: user.role_ids ?? (user.role_id != null ? [user.role_id] : []),
        default_organization_id: user.default_organization_id,
      });
      setModalVisible(true);
    },
    [form]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await userService.deleteUser(id);
        MessageManager.success('删除成功');
        refreshUsersAndStatistics();
      } catch (error) {
        pageLogger.error('删除用户失败:', error as Error);
        MessageManager.error('删除失败');
      }
    },
    [refreshUsersAndStatistics]
  );

  const handleToggleStatus = useCallback(
    async (user: User, newStatus: 'active' | 'inactive') => {
      try {
        await userService.updateUser(user.id, { status: newStatus });
        MessageManager.success('状态已更新');
        refreshUsersAndStatistics();
      } catch (error) {
        pageLogger.error('更新用户状态失败:', error as Error);
        MessageManager.error('状态更新失败');
      }
    },
    [refreshUsersAndStatistics]
  );

  const handleToggleLock = useCallback(
    async (user: User) => {
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
    },
    [refreshUsersAndStatistics]
  );

  const handleViewDetail = useCallback((user: User) => {
    setSelectedUser(user);
    setDetailDrawerVisible(true);
  }, []);

  const handleManagePartyBindings = useCallback((user: User) => {
    setBindingUser(user);
    setBindingModalVisible(true);
  }, []);

  const handleSubmit = useCallback(
    async (values: CreateUserData | UpdateUserData) => {
      try {
        if (editingUser != null) {
          await userService.updateUser(editingUser.id, values as UpdateUserData);
          MessageManager.success('更新成功');
        } else {
          await userService.createUser(values as CreateUserData);
          MessageManager.success('创建成功');
        }
        setModalVisible(false);
        refreshUsersAndStatistics();
      } catch (error) {
        pageLogger.error('保存用户失败:', error as Error);
        MessageManager.error(editingUser != null ? '更新失败' : '创建失败');
      }
    },
    [editingUser, refreshUsersAndStatistics]
  );

  const handleFullNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const name = e.target.value;
      if (editingUser == null && name.trim() !== '') {
        const pinyinName = pinyin(name, { toneType: 'none', type: 'array' }).join('');
        form.setFieldsValue({ username: pinyinName.toLowerCase() });
      }
    },
    [editingUser, form]
  );

  const handleEditFromDrawer = useCallback(
    (user: User) => {
      setDetailDrawerVisible(false);
      handleEdit(user);
    },
    [handleEdit]
  );

  const handleToggleLockFromDrawer = useCallback(
    (user: User) => {
      setDetailDrawerVisible(false);
      void handleToggleLock(user);
    },
    [handleToggleLock]
  );

  const getStatusTag = useCallback((status: UserStatus | string | null | undefined) => {
    const statusMeta = resolveStatusMeta(status);
    return (
      <Tag
        className={`${styles.semanticTag} ${styles.statusTag} ${getToneClassName(statusMeta.tone)}`}
      >
        {statusMeta.label}
        <span className={styles.statusHint}>{statusMeta.hint}</span>
      </Tag>
    );
  }, []);

  const enabledFilterCount = useMemo(() => {
    return [filters.keyword, filters.status, filters.roleId, filters.organizationId].filter(
      value => {
        return value.trim() !== '';
      }
    ).length;
  }, [filters.keyword, filters.organizationId, filters.roleId, filters.status]);

  return (
    <PageContainer className={styles.pageShell} title="用户管理" subTitle="管理系统用户账户和权限">
      {statistics != null && <UserStatisticsCards statistics={statistics} />}

      <Card>
        <UserFiltersToolbar
          filters={filters}
          roles={roles}
          organizations={organizations}
          statusOptions={USER_STATUS_FILTER_OPTIONS}
          isRefreshing={isRefreshing}
          total={tablePagination.total}
          enabledFilterCount={enabledFilterCount}
          onSearch={handleSearch}
          onStatusFilterChange={handleStatusFilterChange}
          onRoleFilterChange={handleRoleFilterChange}
          onOrganizationFilterChange={handleOrganizationFilterChange}
          onRefresh={refreshUsersAndStatistics}
          onCreate={handleCreate}
        />

        <UserTable
          users={users}
          roleOptions={roles}
          loading={loading}
          paginationState={tablePagination}
          onPageChange={handlePageChange}
          onViewDetail={handleViewDetail}
          onManagePartyBindings={handleManagePartyBindings}
          onEdit={handleEdit}
          onToggleLock={handleToggleLock}
          onToggleStatus={handleToggleStatus}
          onDelete={handleDelete}
          getStatusTag={getStatusTag}
        />
      </Card>

      <UserFormModal
        open={modalVisible}
        editingUser={editingUser}
        form={form}
        organizations={organizations}
        roles={roles}
        statusOptions={USER_STATUS_FORM_OPTIONS}
        onCancel={() => setModalVisible(false)}
        onSubmit={handleSubmit}
        onFullNameChange={handleFullNameChange}
      />

      <UserDetailDrawer
        open={detailDrawerVisible}
        user={selectedUser}
        roleOptions={roles}
        onClose={() => setDetailDrawerVisible(false)}
        onEdit={handleEditFromDrawer}
        onToggleLock={handleToggleLockFromDrawer}
        getStatusTag={getStatusTag}
      />

      <UserPartyBindingModal
        open={bindingModalVisible}
        user={bindingUser}
        onClose={() => setBindingModalVisible(false)}
        onChanged={refreshUsersAndStatistics}
      />
    </PageContainer>
  );
};

export default UserManagementPage;
