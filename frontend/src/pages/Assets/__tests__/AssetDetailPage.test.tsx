/**
 * AssetDetailPage 页面级测试
 */

import React from 'react';
import {
  screen,
  waitFor,
  fireEvent,
  renderWithProviders as renderWithAppProviders,
} from '@/test/utils/test-helpers';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import dayjs from 'dayjs';
import AssetDetailPage from '../AssetDetailPage';

vi.mock('antd', async () => {
  const antd = await vi.importActual<typeof import('antd')>('antd');
  const dayjsModule = await vi.importActual<typeof import('dayjs')>('dayjs');
  const mockDayjs = dayjsModule.default;

  return {
    ...antd,
    DatePicker: ({
      value,
      onChange,
      allowClear: _allowClear,
      inputReadOnly: _inputReadOnly,
      ...props
    }: Record<string, unknown>) => (
      <button
        type="button"
        data-testid="month-picker"
        onClick={() => onChange?.(mockDayjs('2026-04-01'))}
        {...props}
      >
        {(value as { format?: (pattern: string) => string } | undefined)?.format?.('YYYY-MM') ??
          'no-month'}
      </button>
    ),
  };
});

// Mock assetService
vi.mock('@/services/assetService', () => ({
  assetService: {
    getAsset: vi.fn(),
    getAssetLeaseSummary: vi.fn(),
  },
}));

// Mock AssetDetailInfo component
vi.mock('@/components/Asset/AssetDetailInfo', () => ({
  default: ({ asset }: { asset: { asset_name: string } }) => (
    <div data-testid="asset-detail-info">Asset Info: {asset.asset_name}</div>
  ),
}));

import { assetService } from '@/services/assetService';

const buildLeaseSummary = (overrides: Record<string, unknown> = {}) => ({
  asset_id: 'asset_123',
  period_start: '2026-03-01',
  period_end: '2026-03-31',
  total_contracts: 3,
  total_rented_area: 1200,
  rentable_area: 1600,
  occupancy_rate: 75,
  by_type: [
    {
      group_relation_type: '上游',
      label: '上游承租',
      contract_count: 1,
      total_area: 0,
      monthly_amount: 18000,
    },
    {
      group_relation_type: '下游',
      label: '下游转租',
      contract_count: 2,
      total_area: 0,
      monthly_amount: 36000,
    },
    {
      group_relation_type: '委托',
      label: '委托协议',
      contract_count: 0,
      total_area: 0,
      monthly_amount: 0,
    },
    {
      group_relation_type: '直租',
      label: '直租合同',
      contract_count: 0,
      total_area: 0,
      monthly_amount: 0,
    },
  ],
  customer_summary: [
    {
      party_id: 'party-1',
      party_name: '租户甲',
      group_relation_type: '下游',
      contract_count: 2,
    },
  ],
  ...overrides,
});

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
const renderAssetDetailPage = (assetId: string) => {
  const queryClient = createTestQueryClient();

  return renderWithAppProviders(
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/assets/:id" element={<AssetDetailPage />} />
        <Route path="/assets" element={<div>Asset List</div>} />
        <Route path="/assets/:id/edit" element={<div>Edit Asset</div>} />
      </Routes>
    </QueryClientProvider>,
    { route: `/assets/${assetId}` }
  );
};

describe('AssetDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assetService.getAssetLeaseSummary).mockResolvedValue(buildLeaseSummary());
  });

  describe('加载状态', () => {
    it('显示加载中状态', async () => {
      vi.mocked(assetService.getAsset).mockImplementation(
        () => new Promise(() => {}) // 永不resolve，模拟加载中
      );

      renderAssetDetailPage('asset_123');

      expect(document.querySelector('.ant-spin-spinning')).toBeInTheDocument();
    });
  });

  describe('成功加载', () => {
    it('显示资产详情', async () => {
      const mockAsset = {
        id: 'asset_123',
        asset_name: '测试资产A栋',
        building_name: 'A栋',
        floor: 5,
        area: 120.5,
        status: 'available',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderAssetDetailPage('asset_123');

      await waitFor(() => {
        expect(screen.getByText('测试资产A栋')).toBeInTheDocument();
      });

      expect(screen.getByTestId('asset-detail-info')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '返回' })).toBeInTheDocument();
      expect(screen.getByText('编辑资产')).toBeInTheDocument();
    });

    it('显示租赁情况和客户摘要', async () => {
      const mockAsset = {
        id: 'asset_123',
        asset_name: '测试资产A栋',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);
      vi.mocked(assetService.getAssetLeaseSummary).mockResolvedValue(buildLeaseSummary());

      renderAssetDetailPage('asset_123');

      const currentMonthStart = dayjs().startOf('month').format('YYYY-MM-DD');
      const currentMonthEnd = dayjs().endOf('month').format('YYYY-MM-DD');

      await waitFor(() => {
        expect(assetService.getAssetLeaseSummary).toHaveBeenCalledWith('asset_123', {
          period_start: currentMonthStart,
          period_end: currentMonthEnd,
        });
      });

      await waitFor(() => {
        expect(screen.getByText('合同角色汇总')).toBeInTheDocument();
      });

      expect(screen.getByText('本月出租率')).toBeInTheDocument();
      expect(screen.getByText('租户甲')).toBeInTheDocument();
      expect(screen.getByText('下游转租')).toBeInTheDocument();
      expect(
        screen.getByText((_, node) => (node?.textContent?.trim() ?? '') === '75.00%')
      ).toBeInTheDocument();
    });

    it('切换月份时重新请求对应月份的租赁汇总', async () => {
      const mockAsset = {
        id: 'asset_123',
        asset_name: '测试资产A栋',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);
      vi.mocked(assetService.getAssetLeaseSummary).mockImplementation(async (_assetId, params) =>
        buildLeaseSummary({
          period_start: params?.period_start,
          period_end: params?.period_end,
        })
      );

      renderAssetDetailPage('asset_123');

      await waitFor(() => {
        expect(assetService.getAssetLeaseSummary).toHaveBeenCalledWith('asset_123', {
          period_start: dayjs().startOf('month').format('YYYY-MM-DD'),
          period_end: dayjs().endOf('month').format('YYYY-MM-DD'),
        });
      });

      await waitFor(() => {
        expect(screen.getByText('合同角色汇总')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('month-picker'));

      await waitFor(() => {
        expect(assetService.getAssetLeaseSummary).toHaveBeenLastCalledWith('asset_123', {
          period_start: '2026-04-01',
          period_end: '2026-04-30',
        });
      });
    });

    it('显示资产名称作为标题', async () => {
      const mockAsset = {
        id: 'asset_456',
        asset_name: '商业中心B座',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderAssetDetailPage('asset_456');

      await waitFor(() => {
        expect(screen.getByText('商业中心B座')).toBeInTheDocument();
      });
    });

    it('资产名称为空时显示默认标题', async () => {
      const mockAsset = {
        id: 'asset_789',
        asset_name: null,
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderAssetDetailPage('asset_789');

      await waitFor(() => {
        expect(screen.getAllByText('资产详情').length).toBeGreaterThan(0);
      });
    });
  });

  describe('错误处理', () => {
    it('显示错误信息', async () => {
      vi.mocked(assetService.getAsset).mockRejectedValue(new Error('网络错误：无法连接到服务器'));

      renderAssetDetailPage('asset_error');

      await waitFor(() => {
        expect(screen.getByText('数据加载失败')).toBeInTheDocument();
        expect(screen.getByText(/网络错误：无法连接到服务器/)).toBeInTheDocument();
      });
    });

    it('资产不存在时显示警告', async () => {
      vi.mocked(assetService.getAsset).mockResolvedValue(null);

      renderAssetDetailPage('asset_not_found');

      await waitFor(() => {
        expect(screen.getByText('资产不存在')).toBeInTheDocument();
        expect(screen.getByText('未找到指定的资产信息')).toBeInTheDocument();
      });
    });

    it('租赁汇总加载失败时显示卡片错误', async () => {
      vi.mocked(assetService.getAsset).mockResolvedValue({
        id: 'asset_lease_error',
        asset_name: '租赁汇总异常资产',
      });
      vi.mocked(assetService.getAssetLeaseSummary).mockRejectedValue(new Error('租赁汇总加载失败'));

      renderAssetDetailPage('asset_lease_error');

      await waitFor(() => {
        expect(screen.getByText('租赁情况加载失败')).toBeInTheDocument();
        expect(screen.getByText(/租赁汇总加载失败/)).toBeInTheDocument();
      });
    });
  });

  describe('导航功能', () => {
    it('点击返回列表按钮导航到资产列表', async () => {
      const mockAsset = {
        id: 'asset_nav',
        asset_name: '导航测试资产',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderAssetDetailPage('asset_nav');

      await waitFor(() => {
        expect(screen.getByText('导航测试资产')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: '返回' }));

      await waitFor(() => {
        expect(screen.getByText('Asset List')).toBeInTheDocument();
      });
    });

    it('点击编辑资产按钮导航到编辑页', async () => {
      const mockAsset = {
        id: 'asset_edit',
        asset_name: '编辑测试资产',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderAssetDetailPage('asset_edit');

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
        asset_name: '特定资产',
      };

      vi.mocked(assetService.getAsset).mockResolvedValue(mockAsset);

      renderAssetDetailPage('specific_asset_id');

      await waitFor(() => {
        expect(assetService.getAsset).toHaveBeenCalledWith('specific_asset_id');
      });
    });
  });
});
