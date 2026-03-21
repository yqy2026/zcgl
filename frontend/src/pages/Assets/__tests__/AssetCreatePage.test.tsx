import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { QueryClient } from '@tanstack/react-query';
import { renderWithProviders, waitFor } from '@/test/test-utils';
import AssetCreatePage from '../AssetCreatePage';

const mockNavigate = vi.fn();
const mockInvalidateQueries = vi.fn();

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|view:owner:party-1',
}));

const mockUseView = vi.fn(() => ({
  currentView: {
    key: 'owner:party-1',
    perspective: 'owner',
    partyId: 'party-1',
    partyName: '主体A',
    label: '产权方 · 主体A',
  },
  selectionRequired: false,
  isViewReady: true,
}));

vi.mock('@/contexts/ViewContext', () => ({
  useView: () => mockUseView(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: 'asset-1' }),
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
    mockUseView.mockReturnValue({
      currentView: {
        key: 'owner:party-1',
        perspective: 'owner',
        partyId: 'party-1',
        partyName: '主体A',
        label: '产权方 · 主体A',
      },
      selectionRequired: false,
      isViewReady: true,
    });
  });

  it('编辑态资产详情查询应把当前视角纳入 queryKey', async () => {
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
          queryKey[1] === 'user:user-1|view:owner:party-1' &&
          queryKey[2] === 'asset-1'
      )
    ).toBe(true);
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

  it('视角未就绪时编辑态不应渲染表单或请求资产详情', async () => {
    mockUseView.mockReturnValue({
      currentView: null,
      selectionRequired: true,
      isViewReady: false,
    });

    renderWithProviders(<AssetCreatePage />, { route: '/assets/asset-1/edit' });

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'submit' })).not.toBeInTheDocument();
    });

    expect(assetService.getAsset).not.toHaveBeenCalled();
  });
});
