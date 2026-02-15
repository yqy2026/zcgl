import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { roleService, type Role } from '@/services/systemService';
import type { PaginationState } from '@/components/Common/TableWithPagination';
import type {
  Permission,
  PermissionListResponse,
  RoleFilters,
  RoleListQueryResult,
  RoleListResponse,
  RolePaginationState,
  RoleStatisticsApiResponse,
} from '../types';

interface UseRoleManagementDataParams {
  filters: RoleFilters;
  pagination: RolePaginationState;
}

const mapRoleList = (data: RoleListResponse): RoleListQueryResult => {
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
};

export const useRoleManagementData = ({ filters, pagination }: UseRoleManagementDataParams) => {
  const currentPage = pagination.current;
  const pageSize = pagination.pageSize;
  const keyword = filters.keyword;
  const status = filters.status;

  const fetchRoleList = useCallback(async (): Promise<RoleListQueryResult> => {
    const isActive = status === 'active' ? true : status === 'inactive' ? false : undefined;
    const trimmedKeyword = keyword.trim();
    const data = (await roleService.getRoles({
      page: currentPage,
      page_size: pageSize,
      search: trimmedKeyword !== '' ? trimmedKeyword : undefined,
      is_active: isActive,
    })) as RoleListResponse;
    return mapRoleList(data);
  }, [currentPage, keyword, pageSize, status]);

  const rolesQuery = useQuery<RoleListQueryResult>({
    queryKey: ['role-management-list', currentPage, pageSize, keyword, status],
    queryFn: fetchRoleList,
    retry: false,
  });

  const permissionsQuery = useQuery<Permission[]>({
    queryKey: ['role-management-permissions'],
    queryFn: async () => {
      const response = (await roleService.getPermissions()) as PermissionListResponse;
      const grouped = response.data ?? {};
      return Object.keys(grouped).flatMap(resource =>
        (grouped[resource] ?? []).map(permissionItem => {
          const action = permissionItem.action ?? 'action';
          const resourceKey = permissionItem.resource ?? resource;
          return {
            id: permissionItem.id,
            name: permissionItem.display_name ?? `${resourceKey}:${action}`,
            code: `${resourceKey}.${action}`,
            module: resourceKey,
            description: permissionItem.description ?? '',
            type: action === 'view' || action === 'read' ? 'menu' : 'action',
          };
        })
      );
    },
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  const statisticsQuery = useQuery<RoleStatisticsApiResponse>({
    queryKey: ['role-management-statistics'],
    queryFn: async () => {
      return (await roleService.getRoleStatistics()) as RoleStatisticsApiResponse;
    },
    staleTime: 60 * 1000,
    retry: false,
  });

  const tablePagination = useMemo<PaginationState>(
    () => ({
      current: currentPage,
      pageSize,
      total: rolesQuery.data?.total ?? 0,
    }),
    [currentPage, pageSize, rolesQuery.data?.total]
  );

  return {
    roles: rolesQuery.data?.items ?? [],
    permissions: permissionsQuery.data ?? [],
    statisticsResponse: statisticsQuery.data,
    loading: rolesQuery.isLoading || rolesQuery.isFetching,
    rolesError: rolesQuery.error,
    permissionsError: permissionsQuery.error,
    statisticsError: statisticsQuery.error,
    tablePagination,
    refetchRoles: rolesQuery.refetch,
    refetchStatistics: statisticsQuery.refetch,
  };
};
