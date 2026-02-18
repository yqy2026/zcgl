import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import RentStatisticsPage from '../RentStatisticsPage';
import { rentContractService } from '@/services/rentContractService';

const plotMocks = vi.hoisted(() => ({
  pieSpy: vi.fn(),
  columnSpy: vi.fn(),
  lineSpy: vi.fn(),
}));

vi.mock('@ant-design/plots', () => ({
  Pie: (props: Record<string, unknown>) => {
    plotMocks.pieSpy(props);
    return <div data-testid="pie-chart" />;
  },
  Column: (props: Record<string, unknown>) => {
    plotMocks.columnSpy(props);
    return <div data-testid="column-chart" />;
  },
  Line: (props: Record<string, unknown>) => {
    plotMocks.lineSpy(props);
    return <div data-testid="line-chart" />;
  },
}));

vi.mock('@/components/Analytics', () => ({
  ChartErrorBoundary: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="chart-error-boundary">{children}</div>
  ),
}));

vi.mock('@/services/rentContractService', () => ({
  rentContractService: {
    getStatisticsOverview: vi.fn(),
    getOwnershipStatistics: vi.fn(),
    getAssetStatistics: vi.fn(),
    getMonthlyStatistics: vi.fn(),
    exportStatistics: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

const overview = {
  total_due: 1000,
  total_paid: 800,
  total_overdue: 200,
  total_records: 1,
  payment_rate: 80,
  status_breakdown: [],
  monthly_breakdown: [],
  average_unit_price: 10,
  renewal_rate: 90,
};

const ownershipStats = [
  {
    ownership_id: 'ownership-1',
    ownership_name: '权属A',
    ownership_short_name: 'A',
    contract_count: 1,
    total_due_amount: 1000,
    total_paid_amount: 800,
    total_overdue_amount: 200,
    payment_rate: 80,
  },
];

const assetStats = [
  {
    asset_id: 'asset-1',
    asset_name: '资产A',
    asset_address: '地址',
    contract_count: 1,
    total_due_amount: 1000,
    total_paid_amount: 800,
    total_overdue_amount: 200,
    payment_rate: 80,
  },
];

const monthlyStats = [
  {
    year_month: '2025-01',
    total_contracts: 1,
    total_due_amount: 1000,
    total_paid_amount: 800,
    total_overdue_amount: 200,
    payment_rate: 80,
  },
];

describe('RentStatisticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    plotMocks.pieSpy.mockClear();
    plotMocks.columnSpy.mockClear();
    plotMocks.lineSpy.mockClear();

    vi.mocked(rentContractService.getStatisticsOverview).mockResolvedValue(overview);
    vi.mocked(rentContractService.getOwnershipStatistics).mockResolvedValue(ownershipStats);
    vi.mocked(rentContractService.getAssetStatistics).mockResolvedValue(assetStats);
    vi.mocked(rentContractService.getMonthlyStatistics).mockResolvedValue(monthlyStats);
  });

  it(
    'wraps charts with error boundary and uses functional label',
    async () => {
      renderWithProviders(<RentStatisticsPage />);

      await waitFor(
        () => {
          expect(plotMocks.pieSpy).toHaveBeenCalled();
        },
        { timeout: 15_000 }
      );

      const pieProps = plotMocks.pieSpy.mock.calls[0]?.[0] as {
        label?: { content?: unknown };
      };
      const labelContent = pieProps.label?.content;
      expect(typeof labelContent).toBe('function');

      const boundaries = screen.getAllByTestId('chart-error-boundary');
      expect(boundaries.length).toBeGreaterThanOrEqual(1);
    },
    20_000
  );
});
