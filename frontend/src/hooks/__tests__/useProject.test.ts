/**
 * useProject Hook 测试
 * 测试项目管理相关的自定义Hooks（简化版本）
 */

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook, waitFor } from '@/test/utils/test-helpers';
import { projectService } from '@/services/projectService';
import {
  useProjectOptions,
  useProjectDetail,
  useProjectList,
  useProjectStatistics,
  useToggleProjectStatus,
  useUpdateProject,
} from '../useProject';

const mockUseView = vi.fn(() => ({
  currentView: {
    key: 'manager:party-1',
    perspective: 'manager',
    partyId: 'party-1',
    partyName: '运营主体A',
    label: '运营方 · 运营主体A',
  },
}));

vi.mock('@/contexts/ViewContext', () => ({
  useView: () => mockUseView(),
}));

vi.mock('@/routes/perspective', () => ({
  useRoutePerspective: () => ({
    perspective: 'manager',
    isPerspectiveRoute: true,
  }),
}));

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|perspective:manager',
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// =============================================================================
// Mock projectService
// =============================================================================

vi.mock('@/services/projectService', () => ({
  projectService: {
    getProjectOptions: vi.fn(() =>
      Promise.resolve([
        { id: '1', project_name: '项目1', project_code: 'PRJ-TEST01-000001', status: 'active' },
        { id: '2', project_name: '项目2', project_code: 'PRJ-TEST02-000001', status: 'active' },
      ])
    ),
    getProject: vi.fn(() =>
      Promise.resolve({
        id: '1',
        project_name: '项目1',
        project_code: 'PRJ-TEST01-000001',
        status: 'active',
        data_status: '正常',
        review_status: 'draft',
        created_at: '2026-03-05T00:00:00Z',
        updated_at: '2026-03-05T00:00:00Z',
      })
    ),
    getProjects: vi.fn(() =>
      Promise.resolve({
        items: [],
        page: 1,
        page_size: 10,
        pages: 0,
        total: 0,
      })
    ),
    getProjectStatistics: vi.fn(() =>
      Promise.resolve({
        total_projects: 10,
        active_projects: 8,
      })
    ),
    createProject: vi.fn(() =>
      Promise.resolve({
        id: 'new-1',
        project_name: '新项目',
        project_code: 'PRJ-NEW01-000001',
        status: 'planning',
        data_status: '正常',
        review_status: 'draft',
        created_at: '2026-03-05T00:00:00Z',
        updated_at: '2026-03-05T00:00:00Z',
      })
    ),
    updateProject: vi.fn(() =>
      Promise.resolve({
        id: '1',
        project_name: '更新项目',
        project_code: 'PRJ-TEST01-000001',
        status: 'active',
        data_status: '正常',
        review_status: 'draft',
        created_at: '2026-03-05T00:00:00Z',
        updated_at: '2026-03-05T00:00:00Z',
      })
    ),
    deleteProject: vi.fn(() => Promise.resolve({ message: '项目删除成功', deleted_id: '1' })),
    toggleProjectStatus: vi.fn(() =>
      Promise.resolve({
        id: '1',
        project_name: '项目1',
        project_code: 'PRJ-TEST01-000001',
        status: 'paused',
        data_status: '正常',
        review_status: 'draft',
        created_at: '2026-03-05T00:00:00Z',
        updated_at: '2026-03-05T00:00:00Z',
      })
    ),
    validateProjectCode: vi.fn(() => Promise.resolve(true)),
    validateProjectName: vi.fn(() => Promise.resolve(true)),
  },
}));

// =============================================================================
// Mock antd message
// =============================================================================

vi.mock('antd', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

// =============================================================================
// useProject Hook 测试
// =============================================================================

const createQueryWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  const QueryWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  QueryWrapper.displayName = 'QueryWrapper';
  return QueryWrapper;
};

const createQueryHarness = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  wrapper.displayName = 'QueryHarness';

  return { queryClient, wrapper };
};

describe('useProject - Hook验证', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该导出useProjectOptions hook', async () => {
    const { useProjectOptions } = await import('../useProject');
    expect(typeof useProjectOptions).toBe('function');
  });

  it('应该导出useProjectDetail hook', async () => {
    const { useProjectDetail } = await import('../useProject');
    expect(typeof useProjectDetail).toBe('function');
  });

  it('应该导出useProjectList hook', async () => {
    const { useProjectList } = await import('../useProject');
    expect(typeof useProjectList).toBe('function');
  });

  it('应该导出useProjectStatistics hook', async () => {
    const { useProjectStatistics } = await import('../useProject');
    expect(typeof useProjectStatistics).toBe('function');
  });

  it('应该导出useCreateProject hook', async () => {
    const { useCreateProject } = await import('../useProject');
    expect(typeof useCreateProject).toBe('function');
  });

  it('应该导出useUpdateProject hook', async () => {
    const { useUpdateProject } = await import('../useProject');
    expect(typeof useUpdateProject).toBe('function');
  });

  it('应该导出useDeleteProject hook', async () => {
    const { useDeleteProject } = await import('../useProject');
    expect(typeof useDeleteProject).toBe('function');
  });

  it('应该导出useToggleProjectStatus hook', async () => {
    const { useToggleProjectStatus } = await import('../useProject');
    expect(typeof useToggleProjectStatus).toBe('function');
  });

  it('应该导出useValidateProjectCode hook', async () => {
    const { useValidateProjectCode } = await import('../useProject');
    expect(typeof useValidateProjectCode).toBe('function');
  });

  it('应该导出useValidateProjectName hook', async () => {
    const { useValidateProjectName } = await import('../useProject');
    expect(typeof useValidateProjectName).toBe('function');
  });

  it('useProjectStatistics 应返回新统计契约字段', async () => {
    const { result } = renderHook(() => useProjectStatistics(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.statistics).not.toBeNull();
    });

    expect(projectService.getProjectStatistics).toHaveBeenCalledTimes(1);
    expect(result.current.statistics?.total_projects).toBe(10);
    expect(result.current.statistics?.active_projects).toBe(8);
    expect((result.current.statistics as Record<string, unknown>)?.total).toBeUndefined();
    expect((result.current.statistics as Record<string, unknown>)?.active).toBeUndefined();
  });

  it('useProjectList 应使用 page_size 分页字段', async () => {
    vi.mocked(projectService.getProjects).mockResolvedValueOnce({
      items: [
        {
          id: 'p-2',
          project_name: '项目二',
          project_code: 'PRJ-TEST02-000001',
          status: 'active',
          data_status: '正常',
          review_status: 'draft',
          created_at: '2026-03-05T00:00:00Z',
          updated_at: '2026-03-05T00:00:00Z',
        },
      ],
      page: 2,
      page_size: 20,
      pages: 3,
      total: 41,
    });

    const { result } = renderHook(() => useProjectList({ page: 2, page_size: 20 }), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.projects.length).toBe(1);
    });

    expect(projectService.getProjects).toHaveBeenCalledWith(
      expect.objectContaining({ page: 2, page_size: 20 })
    );
    expect(result.current.pagination.current).toBe(2);
    expect(result.current.pagination.pageSize).toBe(20);
    expect(result.current.pagination.total).toBe(41);
    expect(result.current.projects[0]?.project_name).toBe('项目二');
  });

  it('useProjectOptions 应把当前视角纳入选项 queryKey', async () => {
    const { queryClient, wrapper } = createQueryHarness();

    renderHook(() => useProjectOptions('active'), { wrapper });

    await waitFor(() => {
      expect(projectService.getProjectOptions).toHaveBeenCalledWith('active');
    });

    const queryKeys = queryClient
      .getQueryCache()
      .getAll()
      .map(query => query.queryKey);

    expect(queryKeys).toContainEqual([
      'project-options',
      'user:user-1|perspective:manager',
      'active',
    ]);
    expect(mockUseView).not.toHaveBeenCalled();
  });

  it('useProjectDetail 应把当前视角纳入详情 queryKey', async () => {
    const { queryClient, wrapper } = createQueryHarness();

    renderHook(() => useProjectDetail('1'), { wrapper });

    await waitFor(() => {
      expect(projectService.getProject).toHaveBeenCalledWith('1');
    });

    const queryKeys = queryClient
      .getQueryCache()
      .getAll()
      .map(query => query.queryKey);

    expect(queryKeys).toContainEqual(['project', 'user:user-1|perspective:manager', '1']);
    expect(mockUseView).not.toHaveBeenCalled();
  });

  it('useUpdateProject 成功后应失效 scoped 项目详情查询前缀', async () => {
    const { queryClient, wrapper } = createQueryHarness();
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useUpdateProject(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        id: '1',
        data: { project_name: '更新项目' } as never,
      });
    });

    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['project'] });
  });

  it('useToggleProjectStatus 成功后应失效 scoped 项目详情查询前缀', async () => {
    const { queryClient, wrapper } = createQueryHarness();
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useToggleProjectStatus(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync('1');
    });

    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['project'] });
  });
});
