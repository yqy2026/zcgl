/**
 * AssetListPage 页面测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AssetListPage from '../AssetListPage';

// Mock services
vi.mock('../../../services/assetService', () => ({
  assetService: {
    deleteAsset: vi.fn(),
    exportAssets: vi.fn(),
    exportSelectedAssets: vi.fn(),
  },
}));

vi.mock('../../../services/analyticsService', () => ({
  analyticsService: {
    getComprehensiveAnalytics: vi.fn(),
  },
}));

// Mock hooks
vi.mock('../../../hooks/useAssets', () => ({
  useAssets: vi.fn(),
}));

// Mock components
vi.mock('../../../components/Asset/AssetList', () => ({
  default: ({ data: _data, onEdit, onDelete, onView }: { data: unknown; onEdit: (asset: { id: string }) => void; onDelete: (id: string) => void; onView: (asset: { id: string }) => void }) => (
    <div data-testid="asset-list">
      Asset List Component
      <button onClick={() => onEdit({ id: 'asset_1' })}>Edit</button>
      <button onClick={() => onDelete('asset_1')}>Delete</button>
      <button onClick={() => onView({ id: 'asset_1' })}>View</button>
    </div>
  ),
}));

vi.mock('../../../components/Asset/AssetSearch', () => ({
  default: ({ onSearch, onReset }: { onSearch: (params: unknown) => void; onReset: () => void }) => (
    <div data-testid="asset-search">
      <button onClick={() => onSearch({ keyword: 'test' })}>Search</button>
      <button onClick={onReset}>Reset</button>
    </div>
  ),
}));

vi.mock('../../../components/Asset/AssetAreaSummary', () => ({
  default: () => <div data-testid="asset-area-summary">Area Summary</div>,
}));

vi.mock('../../../components/Common/StateContainer', () => ({
  PageContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="page-container">{children}</div>,
  ContentSection: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LoadingContainer: ({ text }: { text: string }) => <div data-testid="loading">{text}</div>,
}));

vi.mock('../../../utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
  }),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

import { useAssets } from '../../../hooks/useAssets';
import { assetService } from '../../../services/assetService';
import { MessageManager } from '@/utils/messageManager';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

const renderWithProviders = () => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AssetListPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('AssetListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useAssets).mockReturnValue({
      data: {
        items: [
          { id: 'asset_1', property_name: '资产A' },
          { id: 'asset_2', property_name: '资产B' },
        ],
        total: 2,
        page: 1,
        page_size: 20,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useAssets>);
  });

  describe('渲染', () => {
    it('渲染页面标题', () => {
      renderWithProviders();

      expect(screen.getByText('资产列表')).toBeInTheDocument();
    });

    it('渲染操作按钮', () => {
      renderWithProviders();

      expect(screen.getByText('新增资产')).toBeInTheDocument();
      expect(screen.getByText('导入资产')).toBeInTheDocument();
      expect(screen.getByText('导出全部')).toBeInTheDocument();
    });

    it('渲染搜索组件', () => {
      renderWithProviders();

      expect(screen.getByTestId('asset-search')).toBeInTheDocument();
    });

    it('渲染面积汇总组件', () => {
      renderWithProviders();

      expect(screen.getByTestId('asset-area-summary')).toBeInTheDocument();
    });

    it('渲染资产列表组件', () => {
      renderWithProviders();

      expect(screen.getByTestId('asset-list')).toBeInTheDocument();
    });
  });

  describe('加载状态', () => {
    it('加载中显示加载状态', () => {
      vi.mocked(useAssets).mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useAssets>);

      renderWithProviders();

      expect(screen.getByTestId('loading')).toBeInTheDocument();
      expect(screen.getByText('加载资产数据中...')).toBeInTheDocument();
    });
  });

  describe('错误处理', () => {
    it('显示错误信息', () => {
      vi.mocked(useAssets).mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('服务器错误'),
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useAssets>);

      renderWithProviders();

      expect(screen.getByText('数据加载失败')).toBeInTheDocument();
      expect(screen.getByText('重新加载')).toBeInTheDocument();
    });
  });

  describe('导航功能', () => {
    it('点击新增资产导航到创建页', () => {
      renderWithProviders();

      fireEvent.click(screen.getByText('新增资产'));

      expect(mockNavigate).toHaveBeenCalledWith('/assets/new');
    });

    it('点击导入资产导航到导入页', () => {
      renderWithProviders();

      fireEvent.click(screen.getByText('导入资产'));

      expect(mockNavigate).toHaveBeenCalledWith('/assets/import');
    });

    it('点击编辑导航到编辑页', () => {
      renderWithProviders();

      fireEvent.click(screen.getByText('Edit'));

      expect(mockNavigate).toHaveBeenCalledWith('/assets/asset_1/edit');
    });

    it('点击查看导航到详情页', () => {
      renderWithProviders();

      fireEvent.click(screen.getByText('View'));

      expect(mockNavigate).toHaveBeenCalledWith('/assets/asset_1');
    });
  });

  describe('删除功能', () => {
    it('删除成功显示成功消息', async () => {
      vi.mocked(assetService.deleteAsset).mockResolvedValue(undefined);

      renderWithProviders();

      fireEvent.click(screen.getByText('Delete'));

      await waitFor(() => {
        expect(assetService.deleteAsset).toHaveBeenCalledWith('asset_1');
        expect(MessageManager.success).toHaveBeenCalledWith('删除成功');
      });
    });

    it('删除失败显示错误消息', async () => {
      vi.mocked(assetService.deleteAsset).mockRejectedValue(new Error('删除失败'));

      renderWithProviders();

      fireEvent.click(screen.getByText('Delete'));

      await waitFor(() => {
        expect(MessageManager.error).toHaveBeenCalledWith('删除失败');
      });
    });
  });

  describe('搜索功能', () => {
    it('点击搜索触发搜索', () => {
      renderWithProviders();

      fireEvent.click(screen.getByText('Search'));

      // 搜索后 useAssets 应该被调用
      expect(useAssets).toHaveBeenCalled();
    });

    it('点击重置清空搜索条件', () => {
      renderWithProviders();

      fireEvent.click(screen.getByText('Reset'));

      expect(useAssets).toHaveBeenCalled();
    });
  });

  describe('导出功能', () => {
    it('点击导出全部触发导出', async () => {
      const mockBlob = new Blob(['test'], { type: 'application/xlsx' });
      vi.mocked(assetService.exportAssets).mockResolvedValue(mockBlob);

      // Mock URL.createObjectURL
      global.URL.createObjectURL = vi.fn(() => 'blob:test');
      global.URL.revokeObjectURL = vi.fn();

      renderWithProviders();

      fireEvent.click(screen.getByText('导出全部'));

      await waitFor(() => {
        expect(assetService.exportAssets).toHaveBeenCalled();
        expect(MessageManager.success).toHaveBeenCalledWith('资产数据导出成功');
      });
    });
  });
});
