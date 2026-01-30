/**
 * AssetDetailPage 页面级测试
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AssetDetailPage from '../AssetDetailPage';

// Mock assetService
vi.mock('@/services/assetService', () => ({
  assetService: {
    getAsset: vi.fn(),
  },
}));

// Mock AssetDetailInfo component
vi.mock('@/components/Asset/AssetDetailInfo', () => ({
  default: ({ asset }: { asset: { property_name: string } }) => (
    <div data-testid="asset-detail-info">
      Asset Info: {asset.property_name}
    </div>
  ),
}));

import { assetService } from '@/services/assetService';

// 创建测试用 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

// 渲染辅助函数
const renderWithProviders = (assetId: string) => {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/assets/${assetId}`]}>
        <Routes>
          <Route path="/assets/:id" element={<AssetDetailPage />} />
          <Route path="/assets" element={<div>Asset List</div>} />
          <Route path="/assets/:id/edit" element={<div>Edit Asset</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('AssetDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('加载状态', () => {
    it('显示加载中状态', async () => {
      vi.mocked(assetService.getAsset).mockImplementation(
        () => new Promise(() => {}) // 永不resolve，模拟加载中
      );

      renderWithProviders('asset_123');

      expect(screen.getByText('加载资产详情中...')).toBeInTheDocument();
    });
  });

  describe('成功加载', () => {
    it('显示资产详情', async () => {
      const mockAsset = {
        id: 'asset_123',
        property_name: '测试资产A栋',
        building_name: 'A栋',
        floor: 5,
        area: 120.5,
        status: 'available',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderWithProviders('asset_123');

      await waitFor(() => {
        expect(screen.getByText('测试资产A栋')).toBeInTheDocument();
      });

      expect(screen.getByTestId('asset-detail-info')).toBeInTheDocument();
      expect(screen.getByText('返回列表')).toBeInTheDocument();
      expect(screen.getByText('编辑资产')).toBeInTheDocument();
    });

    it('显示资产名称作为标题', async () => {
      const mockAsset = {
        id: 'asset_456',
        property_name: '商业中心B座',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderWithProviders('asset_456');

      await waitFor(() => {
        expect(screen.getByText('商业中心B座')).toBeInTheDocument();
      });
    });

    it('资产名称为空时显示默认标题', async () => {
      const mockAsset = {
        id: 'asset_789',
        property_name: null,
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderWithProviders('asset_789');

      await waitFor(() => {
        expect(screen.getByText('资产详情')).toBeInTheDocument();
      });
    });
  });

  describe('错误处理', () => {
    it('显示错误信息', async () => {
      vi.mocked(assetService.getAsset).mockRejectedValue(
        new Error('网络错误：无法连接到服务器')
      );

      renderWithProviders('asset_error');

      await waitFor(() => {
        expect(screen.getByText('数据加载失败')).toBeInTheDocument();
        expect(screen.getByText(/网络错误：无法连接到服务器/)).toBeInTheDocument();
      });
    });

    it('资产不存在时显示警告', async () => {
      vi.mocked(assetService.getAsset).mockResolvedValue(null);

      renderWithProviders('asset_not_found');

      await waitFor(() => {
        expect(screen.getByText('资产不存在')).toBeInTheDocument();
        expect(screen.getByText('未找到指定的资产信息')).toBeInTheDocument();
      });
    });
  });

  describe('导航功能', () => {
    it('点击返回列表按钮导航到资产列表', async () => {
      const mockAsset = {
        id: 'asset_nav',
        property_name: '导航测试资产',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderWithProviders('asset_nav');

      await waitFor(() => {
        expect(screen.getByText('导航测试资产')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('返回列表'));

      await waitFor(() => {
        expect(screen.getByText('Asset List')).toBeInTheDocument();
      });
    });

    it('点击编辑资产按钮导航到编辑页', async () => {
      const mockAsset = {
        id: 'asset_edit',
        property_name: '编辑测试资产',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderWithProviders('asset_edit');

      await waitFor(() => {
        expect(screen.getByText('编辑测试资产')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('编辑资产'));

      await waitFor(() => {
        expect(screen.getByText('Edit Asset')).toBeInTheDocument();
      });
    });
  });

  describe('数据获取', () => {
    it('使用正确的资产ID调用服务', async () => {
      const mockAsset = {
        id: 'specific_asset_id',
        property_name: '特定资产',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderWithProviders('specific_asset_id');

      await waitFor(() => {
        expect(assetService.getAsset).toHaveBeenCalledWith('specific_asset_id');
      });
    });
  });
});
