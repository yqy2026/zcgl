import React from 'react';
import { Space, Tag } from 'antd';
import type { DataNode } from 'antd/es/tree';
import type { TransferItem } from 'antd/es/transfer';
import type { Role } from '@/services/systemService';
import type {
  Permission,
  PermissionTagTone,
  RoleFilters,
  RoleStatistics,
  RoleStatisticsApiResponse,
} from './types';

const getPermissionTypeTone = (type: Permission['type']): PermissionTagTone => {
  if (type === 'menu') {
    return 'primary';
  }
  if (type === 'action') {
    return 'success';
  }
  return 'warning';
};

const getPermissionTypeLabel = (type: Permission['type']): string => {
  if (type === 'menu') {
    return '菜单';
  }
  if (type === 'action') {
    return '操作';
  }
  return '数据';
};

export const countActiveRoleFilters = (filters: RoleFilters): number => {
  let count = 0;
  if (filters.keyword.trim() !== '') {
    count += 1;
  }
  if (filters.status !== '') {
    count += 1;
  }
  return count;
};

export const deriveRoleStatistics = (
  roles: Role[],
  statisticsResponse: RoleStatisticsApiResponse | undefined
): RoleStatistics => {
  const fallbackStats: RoleStatistics = {
    total: roles.length,
    active: roles.filter(role => role.status === 'active').length,
    inactive: roles.filter(role => role.status === 'inactive').length,
    system: roles.filter(role => role.is_system).length,
    custom: roles.filter(role => !role.is_system).length,
    avg_permissions:
      roles.length > 0
        ? Math.round(roles.reduce((sum, role) => sum + role.permissions.length, 0) / roles.length)
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
};

interface PermissionModuleItem {
  value: string;
  label: string;
  icon: React.ReactNode;
}

interface BuildPermissionTreeDataParams {
  permissions: Permission[];
  modules: readonly PermissionModuleItem[];
  permissionTypeTagClassName: string;
  resolveToneClassName: (tone: PermissionTagTone) => string;
}

export const buildPermissionTreeData = ({
  permissions,
  modules,
  permissionTypeTagClassName,
  resolveToneClassName,
}: BuildPermissionTreeDataParams): DataNode[] => {
  const moduleMap: Record<string, DataNode> = {};

  permissions.forEach(permission => {
    if (moduleMap[permission.module] === undefined) {
      const module = modules.find(item => item.value === permission.module);
      moduleMap[permission.module] = {
        key: permission.module,
        title: (
          <Space>
            {module?.icon}
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
            className={`${permissionTypeTagClassName} ${resolveToneClassName(
              getPermissionTypeTone(permission.type)
            )}`}
          >
            {getPermissionTypeLabel(permission.type)}
          </Tag>
        </Space>
      ),
    });
  });

  return Object.values(moduleMap);
};

export const buildPermissionTransferData = (permissions: Permission[]): TransferItem[] => {
  return permissions.map(permission => ({
    key: permission.id,
    title: permission.name,
    description: `${permission.code} - ${permission.description}`,
  }));
};
