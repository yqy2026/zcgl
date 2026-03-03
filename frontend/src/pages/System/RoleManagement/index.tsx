import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, Form, Tag } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { roleService, type Role } from '@/services/systemService';
import { PageContainer } from '@/components/Common';
import { useRoleManagementData } from './hooks/useRoleManagementData';
import RoleStatisticsCards from './components/RoleStatisticsCards';
import RoleFiltersToolbar from './components/RoleFiltersToolbar';
import RoleTable from './components/RoleTable';
import RoleFormModal from './components/RoleFormModal';
import RolePermissionModal from './components/RolePermissionModal';
import { rolePermissionModules, roleStatusOptions } from './constants';
import {
  buildPermissionTransferData,
  buildPermissionTreeData,
  countActiveRoleFilters,
  deriveRoleStatistics,
} from './utils';
import type { RoleFilters, StatusTone, Tone } from './types';
import styles from '../RoleManagementPage.module.css';

const toneClassMap: Record<Tone, string> = {
  primary: styles.tonePrimary,
  success: styles.toneSuccess,
  warning: styles.toneWarning,
  error: styles.toneError,
  neutral: styles.toneNeutral,
};

const resolveErrorMessage = (error: unknown): string | null => {
  if (error != null && typeof error === 'object' && 'message' in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim() !== '') {
      return message;
    }
  }
  return null;
};

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

  const getToneClassName = useCallback((tone: Tone): string => {
    return toneClassMap[tone];
  }, []);

  const getStatusToneClassName = useCallback(
    (tone: StatusTone): string => {
      return getToneClassName(tone);
    },
    [getToneClassName]
  );

  const {
    roles,
    permissions,
    statisticsResponse,
    loading,
    rolesError,
    permissionsError,
    statisticsError,
    tablePagination,
    refetchRoles,
    refetchStatistics,
  } = useRoleManagementData({
    filters,
    pagination: paginationState,
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

  const activeFilterCount = useMemo(() => countActiveRoleFilters(filters), [filters]);

  const permissionTreeData = useMemo(() => {
    return buildPermissionTreeData({
      permissions,
      modules: rolePermissionModules,
      permissionTypeTagClassName: styles.permissionTypeTag,
      resolveToneClassName: getToneClassName,
    });
  }, [getToneClassName, permissions]);

  const statistics = useMemo(
    () => deriveRoleStatistics(roles, statisticsResponse),
    [roles, statisticsResponse]
  );

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

  const handleCreate = useCallback(() => {
    setEditingRole(null);
    form.resetFields();
    setTargetPermissions([]);
    setModalVisible(true);
  }, [form]);

  const handleEdit = useCallback(
    (role: Role) => {
      setEditingRole(role);
      form.setFieldsValue({
        name: role.name,
        code: role.code,
        description: role.description,
        status: role.status,
      });
      setModalVisible(true);
    },
    [form]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await roleService.deleteRole(id);
        MessageManager.success('删除成功');
        refreshRolesAndStatistics();
      } catch {
        MessageManager.error('删除失败');
      }
    },
    [refreshRolesAndStatistics]
  );

  const handleToggleStatus = useCallback(
    async (role: Role, newStatus: string) => {
      try {
        await roleService.updateRole(role.id, {
          is_active: newStatus === 'active',
        });
        MessageManager.success('状态已更新');
        refreshRolesAndStatistics();
      } catch {
        MessageManager.error('状态更新失败');
      }
    },
    [refreshRolesAndStatistics]
  );

  const handleManagePermissions = useCallback((role: Role) => {
    setSelectedRole(role);
    setTargetPermissions(role.permissions);
    setPermissionModalVisible(true);
  }, []);

  const handleSubmit = useCallback(
    async (
      values: {
      name: string;
      code: string;
      description: string;
      status: 'active' | 'inactive';
      },
    ) => {
      try {
        if (editingRole != null) {
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
      } catch (error) {
        const fallback = editingRole != null ? '更新失败' : '创建失败';
        MessageManager.error(resolveErrorMessage(error) ?? fallback);
      }
    },
    [editingRole, refreshRolesAndStatistics, targetPermissions]
  );

  const handleSavePermissions = useCallback(async () => {
    try {
      if (selectedRole != null) {
        await roleService.updateRolePermissions(selectedRole.id, targetPermissions);
      }
      MessageManager.success('权限配置已保存');
      setPermissionModalVisible(false);
      refreshRolesAndStatistics();
    } catch {
      MessageManager.error('保存权限失败');
    }
  }, [refreshRolesAndStatistics, selectedRole, targetPermissions]);

  const getStatusTag = useCallback(
    (status: string) => {
      const statusConfig = roleStatusOptions.find(option => option.value === status);
      const tone = statusConfig?.tone ?? 'neutral';
      return (
        <Tag className={`${styles.statusTag} ${getStatusToneClassName(tone)}`}>
          {statusConfig?.label ?? status}
        </Tag>
      );
    },
    [getStatusToneClassName]
  );

  const transferData = useMemo(() => buildPermissionTransferData(permissions), [permissions]);

  return (
    <PageContainer className={styles.pageShell} title="角色管理" subTitle="管理系统角色和权限配置">
      {statistics != null && <RoleStatisticsCards statistics={statistics} />}

      <Card className={styles.rolesCard}>
        <RoleFiltersToolbar
          filters={filters}
          statusOptions={roleStatusOptions}
          total={tablePagination.total}
          activeFilterCount={activeFilterCount}
          loading={loading}
          onSearch={handleSearch}
          onStatusFilterChange={handleStatusFilterChange}
          onRefresh={refreshRolesAndStatistics}
          onCreate={handleCreate}
        />

        <RoleTable
          roles={roles}
          loading={loading}
          paginationState={tablePagination}
          getStatusTag={getStatusTag}
          onPageChange={handlePageChange}
          onEdit={handleEdit}
          onManagePermissions={handleManagePermissions}
          onToggleStatus={handleToggleStatus}
          onDelete={handleDelete}
        />
      </Card>

      <RoleFormModal
        open={modalVisible}
        editingRole={editingRole}
        form={form}
        statusOptions={roleStatusOptions}
        onCancel={() => setModalVisible(false)}
        onSubmit={handleSubmit}
      />

      <RolePermissionModal
        open={permissionModalVisible}
        roleName={selectedRole?.name}
        transferData={transferData}
        targetPermissions={targetPermissions}
        permissionTreeData={permissionTreeData}
        onTargetPermissionsChange={setTargetPermissions}
        onCancel={() => setPermissionModalVisible(false)}
        onSave={handleSavePermissions}
      />
    </PageContainer>
  );
};

export default RoleManagementPage;
