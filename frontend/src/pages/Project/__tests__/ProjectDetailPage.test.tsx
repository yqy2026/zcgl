import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import { useQuery } from '@tanstack/react-query';

import ProjectDetailPage from '../ProjectDetailPage';

const mockBuildQueryScopeKey = vi.fn(() => 'user:user-1|perspective:manager');
const mockUseRoutePerspective = vi.fn(() => ({
  perspective: 'manager',
  isPerspectiveRoute: true,
}));

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: (value: unknown) => mockBuildQueryScopeKey(value),
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
}));

vi.mock('@/routes/perspective', () => ({
  useRoutePerspective: () => mockUseRoutePerspective(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'project-1' }),
    useNavigate: () => vi.fn(),
  };
});

vi.mock('@/hooks/useArrayListData', () => ({
  useArrayListData: () => ({
    data: [],
    loading: false,
    pagination: { current: 1, pageSize: 10, total: 0 },
    loadList: vi.fn(),
    updatePagination: vi.fn(),
  }),
}));

describe('ProjectDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRoutePerspective.mockReturnValue({
      perspective: 'manager',
      isPerspectiveRoute: true,
    });
    vi.mocked(useQuery).mockImplementation(options => {
      const [scope] = options.queryKey as [string, ...unknown[]];
      if (scope === 'project') {
        return {
          data: {
            id: 'project-1',
            project_name: '项目A',
            project_code: 'PRJ-TEST-000001',
            status: 'active',
            data_status: '正常',
            created_at: '2026-03-01T00:00:00Z',
            updated_at: '2026-03-02T00:00:00Z',
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-assets') {
        return {
          data: {
            items: [
              {
                id: 'asset-1',
                asset_name: '资产A',
              },
            ],
            total: 1,
            summary: {
              total_assets: 1,
              total_rentable_area: 0,
              total_rented_area: 0,
              occupancy_rate: 0,
            },
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'asset-lease-summary') {
        return {
          data: {
            total_contracts: 0,
            occupancy_rate: 0,
            customer_summary: [],
            by_type: [],
          },
          isLoading: false,
          error: null,
        };
      }
      return {
        data: undefined,
        isLoading: false,
        error: null,
      };
    });
  });

  it('renders current view label', () => {
    renderWithProviders(<ProjectDetailPage />, { route: '/manager/projects/project-1' });

    expect(screen.getByText('当前视角')).toBeInTheDocument();
    expect(screen.getByText('经营视角')).toBeInTheDocument();
  });

  it('project detail queries should include current view in queryKey', () => {
    renderWithProviders(<ProjectDetailPage />);

    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project', 'user:user-1|perspective:manager', 'project-1'],
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project-assets', 'user:user-1|perspective:manager', 'project-1'],
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: [
          'asset-lease-summary',
          'user:user-1|perspective:manager',
          'asset-1',
          expect.any(String),
          expect.any(String),
        ],
      })
    );
    expect(mockBuildQueryScopeKey).toHaveBeenCalledWith('manager');
  });

  it('legacy 路径不显示视角标签，但仍继续执行详情查询', () => {
    mockUseRoutePerspective.mockReturnValue({
      perspective: null,
      isPerspectiveRoute: false,
    });

    renderWithProviders(<ProjectDetailPage />, { route: '/project/project-1' });

    expect(screen.queryByText('当前视角')).not.toBeInTheDocument();
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project', 'user:user-1|perspective:manager', 'project-1'],
        enabled: true,
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project-assets', 'user:user-1|perspective:manager', 'project-1'],
        enabled: true,
      })
    );
  });
});
