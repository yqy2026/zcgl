import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  userService,
  roleService,
  type OrganizationOption,
  type RoleOption,
} from '@/services/systemService';
import { organizationService } from '@/services/organizationService';
import type { PaginationState } from '@/components/Common/TableWithPagination';
import type { UserFilters, UserPaginationState, UserStatistics, UsersQueryResult } from '../types';

interface UseUserManagementDataParams {
  filters: UserFilters;
  pagination: UserPaginationState;
}

const normalizeRoleOptions = (data: unknown): RoleOption[] => {
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
};

export const useUserManagementData = ({ filters, pagination }: UseUserManagementDataParams) => {
  const currentPage = pagination.current;
  const pageSize = pagination.pageSize;
  const keyword = filters.keyword;
  const status = filters.status;
  const roleId = filters.roleId;
  const organizationId = filters.organizationId;

  const fetchUsers = useCallback(async (): Promise<UsersQueryResult> => {
    const trimmedKeyword = keyword.trim();
    const response = await userService.getUsers({
      page: currentPage,
      page_size: pageSize,
      search: trimmedKeyword !== '' ? trimmedKeyword : undefined,
      status: status !== '' ? status : undefined,
      role_id: roleId !== '' ? roleId : undefined,
      default_organization_id: organizationId !== '' ? organizationId : undefined,
    });
    return { items: response.items ?? [], total: response.total ?? 0 };
  }, [currentPage, keyword, organizationId, pageSize, roleId, status]);

  const usersQuery = useQuery<UsersQueryResult>({
    queryKey: [
      'user-management-list',
      currentPage,
      pageSize,
      keyword,
      status,
      roleId,
      organizationId,
    ],
    queryFn: fetchUsers,
    retry: 1,
  });

  const organizationsQuery = useQuery<OrganizationOption[]>({
    queryKey: ['user-management-organizations'],
    queryFn: async () => {
      const data = await organizationService.getOrganizations({ page_size: 1000 });
      return data.map(org => ({ id: org.id, name: org.name }));
    },
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const rolesQuery = useQuery<RoleOption[]>({
    queryKey: ['user-management-roles'],
    queryFn: async () => {
      const roleData = await roleService.getRoles({ page_size: 100 });
      return normalizeRoleOptions(roleData);
    },
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const statisticsQuery = useQuery<unknown>({
    queryKey: ['user-management-statistics'],
    queryFn: () => userService.getUserStatistics(),
    staleTime: 60 * 1000,
    retry: 1,
  });

  const users = useMemo(() => usersQuery.data?.items ?? [], [usersQuery.data?.items]);

  const statistics = useMemo<UserStatistics | null>(() => {
    if (statisticsQuery.error != null) {
      return null;
    }
    if (statisticsQuery.isFetched !== true) {
      return null;
    }

    const response = statisticsQuery.data;
    if (
      response != null &&
      typeof response === 'object' &&
      'total' in response &&
      'active' in response &&
      'inactive' in response &&
      'locked' in response
    ) {
      return response as UserStatistics;
    }

    return {
      total: users.length,
      active: users.filter(user => user.status === 'active').length,
      inactive: users.filter(user => user.status === 'inactive').length,
      locked: users.filter(user => user.status === 'locked').length,
      by_role: {},
      by_organization: {},
    };
  }, [statisticsQuery.data, statisticsQuery.error, statisticsQuery.isFetched, users]);

  const tablePagination = useMemo<PaginationState>(
    () => ({
      current: currentPage,
      pageSize,
      total: usersQuery.data?.total ?? 0,
    }),
    [currentPage, pageSize, usersQuery.data?.total]
  );

  return {
    users,
    tablePagination,
    loading: usersQuery.isLoading || usersQuery.isFetching,
    isRefreshing: usersQuery.isFetching === true,
    organizations: organizationsQuery.data ?? [],
    roles: rolesQuery.data ?? [],
    statistics,
    usersError: usersQuery.error,
    organizationsError: organizationsQuery.error,
    rolesError: rolesQuery.error,
    statisticsError: statisticsQuery.error,
    refetchUsers: usersQuery.refetch,
    refetchStatistics: statisticsQuery.refetch,
  };
};
