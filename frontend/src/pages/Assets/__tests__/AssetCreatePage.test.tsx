import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { QueryClient } from '@tanstack/react-query';
import { renderWithProviders, waitFor } from '@/test/test-utils';
import AssetCreatePage from '../AssetCreatePage';

const mockNavigate = vi.fn();
const mockInvalidateQueries = vi.fn();
const mockUseParams = vi.fn(() => ({ id: 'asset-1' }));

const mockBuildQueryScopeKey = vi.fn(() => 'user:user-1|scope:owner,manager');

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: (value: unknown) => mockBuildQueryScopeKey(value),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockUseParams(),
  };
});

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');
  return {
    ...actual,
    Form: {
      ...actual.Form,
      useForm: () => [{}],
    },
  };
});

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@/components/Common', () => ({
  PageContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('@/components/Forms', () => ({
  AssetForm: ({ onSubmit }: { onSubmit?: (data: Record<string, unknown>) => void }) => (
    <button type="button" onClick={() => onSubmit?.({ asset_name: '更新后的资产' })}>
      submit
    </button>
  ),
}));

vi.mock('@/services/assetService', () => ({
  assetService: {
    getAsset: vi.fn(() => Promise.resolve({ id: 'asset-1', asset_name: '资产A' })),
    createAsset: vi.fn(() => Promise.resolve({ id: 'asset-2' })),
    updateAsset: vi.fn(() => Promise.resolve({ id: 'asset-1' })),
  },
}));

vi.mock('@tanstack/react-query', async () => {
  const actual =
    await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');

  return {
    ...actual,
    useQueryClient: () => ({
      invalidateQueries: mockInvalidateQueries,
    }),
    useMutation: ({ mutationFn, onSuccess, onError }: Record<string, unknown>) => ({
      mutate: async (data: unknown) => {
        try {
          const result = await (mutationFn as (payload: unknown) => Promise<unknown>)(data);
          await (onSuccess as ((value: unknown) => Promise<void> | void) | undefined)?.(result);
        } catch (error) {
          await (onError as ((value: unknown) => Promise<void> | void) | undefined)?.(error);
        }
      },
      isPending: false,
    }),
  };
});

import { assetService } from '@/services/assetService';

describe('AssetCreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ id: 'asset-1' });
  });

  it('编辑态资产详情查询应把当前数据范围纳入 queryKey', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: Infinity,
        },
      },
    });

    renderWithProviders(<AssetCreatePage />, { queryClient, route: '/assets/asset-1/edit' });

    await waitFor(() => {
      expect(assetService.getAsset).toHaveBeenCalledWith('asset-1');
    });

    const queryKeys = queryClient
      .getQueryCache()
      .getAll()
      .map(query => query.queryKey);

    expect(
      queryKeys.some(
        queryKey =>
          Array.isArray(queryKey) &&
          queryKey[0] === 'asset' &&
          queryKey[1] === 'user:user-1|scope:owner,manager' &&
          queryKey[2] === 'asset-1'
      )
    ).toBe(true);
    expect(mockBuildQueryScopeKey).toHaveBeenCalledWith(undefined);
  });

  it('编辑成功后应失效 scoped 资产列表与详情查询前缀', async () => {
    const { getByRole } = renderWithProviders(<AssetCreatePage />, {
      route: '/assets/asset-1/edit',
    });

    await waitFor(() => {
      expect(assetService.getAsset).toHaveBeenCalledWith('asset-1');
    });

    getByRole('button', { name: 'submit' }).click();

    await waitFor(() => {
      expect(assetService.updateAsset).toHaveBeenCalledWith('asset-1', {
        asset_name: '更新后的资产',
      });
    });

    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['assets-list'] });
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['asset'] });
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['analytics'] });
  });

  it('编辑态不再依赖视角就绪门闸才请求资产详情', async () => {
    renderWithProviders(<AssetCreatePage />, { route: '/assets/asset-1/edit' });

    await waitFor(() => {
      expect(assetService.getAsset).toHaveBeenCalledWith('asset-1');
    });

    expect(screen.getByRole('button', { name: 'submit' })).toBeInTheDocument();
  });

  it('创建成功后应返回 canonical 资产列表', async () => {
    mockUseParams.mockReturnValue({});

    const { getByRole } = renderWithProviders(<AssetCreatePage />, {
      route: '/assets/new',
    });

    getByRole('button', { name: 'submit' }).click();

    await waitFor(() => {
      expect(assetService.createAsset).toHaveBeenCalledWith({
        asset_name: '更新后的资产',
      });
    });

    expect(mockNavigate).toHaveBeenCalledWith('/assets/list');
  });
});
