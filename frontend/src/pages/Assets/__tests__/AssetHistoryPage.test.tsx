/**
 * AssetHistoryPage 页面级测试
 * 验证：资产名标题 / 默认标题回退 / AssetHistory 组件接线（assetId 传递）
 */

import React from 'react';
import { screen, renderWithProviders as renderWithAppProviders } from '@/test/utils/test-helpers';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AssetHistoryPage from '../AssetHistoryPage';
import { assetService } from '@/services/assetService';

const mockBuildQueryScopeKey = vi.fn(() => 'user:user-1|scope:owner,manager');

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: (value: unknown) => mockBuildQueryScopeKey(value),
}));

vi.mock('@/services/assetService', () => ({
  assetService: {
    getAsset: vi.fn(),
  },
}));

// 桩 AssetHistory：聚焦页面接线，避免其内部网络请求
vi.mock('@/components/Asset/AssetHistory', () => ({
  default: ({ assetId }: { assetId: string }) => (
    <div data-testid="asset-history">history:{assetId}</div>
  ),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

const renderPage = (assetId: string) => {
  const queryClient = createTestQueryClient();

  const renderResult = renderWithAppProviders(
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/assets/:id/history" element={<AssetHistoryPage />} />
        <Route path="/assets/list" element={<div>Asset List</div>} />
        <Route path="/assets/:id" element={<div>Asset Detail</div>} />
      </Routes>
    </QueryClientProvider>,
    { route: `/assets/${assetId}/history` }
  );

  return {
    ...renderResult,
    queryClient,
  };
};

describe('AssetHistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('资产加载成功后标题展示资产名，并将 assetId 传给 AssetHistory', async () => {
    vi.mocked(assetService.getAsset).mockResolvedValue({
      id: 'asset_123',
      asset_name: '越华路穗南大厦',
    } as never);

    renderPage('asset_123');

    expect(await screen.findByText('越华路穗南大厦 - 变更历史')).toBeInTheDocument();
    expect(screen.getByTestId('asset-history')).toHaveTextContent('history:asset_123');
    expect(screen.getByRole('button', { name: '返回资产详情' })).toBeInTheDocument();
  });

  it('资产未加载时回退默认标题，历史视图仍正常渲染', async () => {
    vi.mocked(assetService.getAsset).mockRejectedValue(new Error('asset not found'));

    renderPage('asset_123');

    expect(await screen.findByText('资产变更历史')).toBeInTheDocument();
    expect(screen.getByTestId('asset-history')).toHaveTextContent('history:asset_123');
    expect(screen.queryByRole('button', { name: '返回资产详情' })).not.toBeInTheDocument();
  });
});
