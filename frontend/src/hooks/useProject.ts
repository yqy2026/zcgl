/**
 * 项目数据管理Hook
 * 基于React Query优化，避免重复请求
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectService } from '@/services/projectService';
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectStatisticsResponse,
  ProjectDropdownOption,
  ProjectListResponse,
} from '@/types/project';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';

const projectLogger = createLogger('useProject');

// API错误类型
interface ApiErrorResponse {
  response?: {
    data?: {
      detail?: string;
    };
  };
}

// 项目查询参数接口
interface ProjectQueryParams {
  keyword?: string;
  is_active?: boolean;
  ownership_id?: string;
  page?: number;
  page_size?: number;
}

interface UseProjectOptionsResult {
  projects: ProjectDropdownOption[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * 获取项目选项列表
 */
export const useProjectOptions = (isActive: boolean = true): UseProjectOptionsResult => {
  const queryKey = ['project-options', isActive];

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: async () => {
      try {
        const response = await projectService.getProjectOptions(isActive);
        return response;
      } catch (error) {
        projectLogger.error('Error fetching projects:', error as Error);
        throw error;
      }
    },
    staleTime: 10 * 60 * 1000, // 10分钟缓存
    gcTime: 30 * 60 * 1000, // 30分钟保留缓存
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: 1,
  });

  return {
    projects: data ?? [],
    loading: isLoading,
    error: error?.message ?? null,
    refresh: refetch,
  };
};

interface UseProjectDetailResult {
  project: Project | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * 获取单个项目详情
 */
export const useProjectDetail = (id?: string): UseProjectDetailResult => {
  const queryKey = ['project-detail', id];

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: async () => {
      if (id == null) return null;
      try {
        const response = await projectService.getProject(id);
        return response;
      } catch (error) {
        projectLogger.error('Error fetching project:', error as Error);
        throw error;
      }
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    gcTime: 15 * 60 * 1000, // 15分钟保留缓存
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: 1,
    enabled: id != null,
  });

  return {
    project: data ?? null,
    loading: isLoading,
    error: error?.message ?? null,
    refresh: refetch,
  };
};

interface UseProjectListResult {
  projects: Project[];
  loading: boolean;
  error: string | null;
  pagination: {
    current: number;
    pageSize: number;
    total: number;
    onChange: (page: number, size: number) => void;
  };
  refresh: () => void;
}

/**
 * 获取项目列表
 */
export const useProjectList = (params: ProjectQueryParams = {}): UseProjectListResult => {
  const queryKey = ['project-list', params];

  const { data, isLoading, error, refetch } = useQuery<ProjectListResponse>({
    queryKey,
    queryFn: async () => {
      try {
        const response = await projectService.getProjects(params);
        return response;
      } catch (error) {
        projectLogger.error('Error searching projects:', error as Error);
        throw error;
      }
    },
    staleTime: 2 * 60 * 1000, // 2分钟缓存
    gcTime: 10 * 60 * 1000, // 10分钟保留缓存
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    retry: 1,
  });

  const pagination = {
    current: data?.page ?? 1,
    pageSize: data?.page_size ?? 10,
    total: data?.total ?? 0,
    onChange: (_page: number, _size: number) => {
      // 这里可以触发重新查询
      refetch();
    },
  };

  return {
    projects: data?.items ?? [],
    loading: isLoading,
    error: error?.message ?? null,
    pagination,
    refresh: refetch,
  };
};

interface UseProjectStatisticsResult {
  statistics: ProjectStatisticsResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * 获取项目统计信息
 */
export const useProjectStatistics = (): UseProjectStatisticsResult => {
  const queryKey = ['project-statistics'];

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: async () => {
      try {
        const response = await projectService.getProjectStatistics();
        return response;
      } catch (error) {
        projectLogger.error('Error fetching project options:', error as Error);
        throw error;
      }
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    gcTime: 15 * 60 * 1000, // 15分钟保留缓存
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    retry: 1,
  });

  return {
    statistics: data ?? null,
    loading: isLoading,
    error: error?.message ?? null,
    refresh: refetch,
  };
};

/**
 * 创建项目
 */
export const useCreateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ProjectCreate) => {
      return await projectService.createProject(data);
    },
    onSuccess: () => {
      // 使相关缓存失效
      queryClient.invalidateQueries({ queryKey: ['project-list'] });
      queryClient.invalidateQueries({ queryKey: ['project-options'] });
      queryClient.invalidateQueries({ queryKey: ['project-statistics'] });
      MessageManager.success('项目创建成功');
    },
    onError: (error: unknown) => {
      projectLogger.error('创建项目失败:', error as Error);
      const err = error as ApiErrorResponse;
      MessageManager.error(err.response?.data?.detail ?? '创建项目失败');
    },
  });
};

/**
 * 更新项目
 */
export const useUpdateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: ProjectUpdate }) => {
      return await projectService.updateProject(id, data);
    },
    onSuccess: data => {
      // 使相关缓存失效
      queryClient.invalidateQueries({ queryKey: ['project-list'] });
      queryClient.invalidateQueries({ queryKey: ['project-options'] });
      queryClient.invalidateQueries({ queryKey: ['project-statistics'] });
      queryClient.invalidateQueries({ queryKey: ['project-detail', data.id] });
      MessageManager.success('项目更新成功');
    },
    onError: (error: unknown) => {
      projectLogger.error('更新项目失败:', error as Error);
      const err = error as ApiErrorResponse;
      MessageManager.error(err.response?.data?.detail ?? '更新项目失败');
    },
  });
};

/**
 * 删除项目
 */
export const useDeleteProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return await projectService.deleteProject(id);
    },
    onSuccess: () => {
      // 使相关缓存失效
      queryClient.invalidateQueries({ queryKey: ['project-list'] });
      queryClient.invalidateQueries({ queryKey: ['project-options'] });
      queryClient.invalidateQueries({ queryKey: ['project-statistics'] });
      MessageManager.success('项目删除成功');
    },
    onError: (error: unknown) => {
      projectLogger.error('删除项目失败:', error as Error);
      const err = error as ApiErrorResponse;
      MessageManager.error(err.response?.data?.detail ?? '删除项目失败');
    },
  });
};

/**
 * 切换项目状态
 */
export const useToggleProjectStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return await projectService.toggleProjectStatus(id);
    },
    onSuccess: data => {
      // 使相关缓存失效
      queryClient.invalidateQueries({ queryKey: ['project-list'] });
      queryClient.invalidateQueries({ queryKey: ['project-options'] });
      queryClient.invalidateQueries({ queryKey: ['project-statistics'] });
      queryClient.invalidateQueries({ queryKey: ['project-detail', data.id] });
      MessageManager.success('项目状态切换成功');
    },
    onError: (error: unknown) => {
      projectLogger.error('切换项目状态失败:', error as Error);
      const err = error as ApiErrorResponse;
      MessageManager.error(err.response?.data?.detail ?? '切换项目状态失败');
    },
  });
};

/**
 * 验证项目编码唯一性
 */
export const useValidateProjectCode = () => {
  return useMutation({
    mutationFn: async ({ code, excludeId }: { code: string; excludeId?: string }) => {
      return await projectService.validateProjectCode(code, excludeId);
    },
  });
};

/**
 * 验证项目名称唯一性
 */
export const useValidateProjectName = () => {
  return useMutation({
    mutationFn: async ({ name, excludeId }: { name: string; excludeId?: string }) => {
      return await projectService.validateProjectName(name, excludeId);
    },
  });
};
