import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen } from '@/test/utils/test-helpers';
import AssetList from '../AssetList';
import { DataStatus } from '@/types/asset';

const mockUseAuth = vi.hoisted(() => vi.fn());

const formatConsoleMessages = (calls: unknown[][]) =>
  calls
    .flat()
    .map(value => String(value))
    .join(' ');

vi.mock('@/utils/format', () => ({
  formatArea: vi.fn((value: number | undefined) => (value ? `${value} m²` : '-')),
  formatPercentage: vi.fn((value: number) => `${value.toFixed(1)}%`),
  formatDate: vi.fn((date: string) => (date ? new Date(date).toLocaleDateString() : '-')),
  getStatusColor: vi.fn(() => 'default'),
}));

vi.mock('@/hooks/useSystemDictionary', () => ({
  useSystemDictionary: vi.fn(() => ({
    options: [],
    loading: false,
    error: null,
    getLabel: vi.fn(() => '-'),
  })),
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('@/components/Common/TableWithPagination', () => ({
  TableWithPagination: ({
    dataSource,
    columns,
  }: {
    dataSource?: Array<Record<string, unknown>>;
    columns?: Array<{
      key?: string;
      dataIndex?: string;
      render?: (value: unknown, record: Record<string, unknown>, index: number) => ReactNode;
    }>;
  }) => (
    <div data-testid="table">
      {(dataSource ?? []).map((record, rowIndex) => (
        <div key={String(record.id ?? rowIndex)} data-testid={`row-${rowIndex}`}>
          {(columns ?? []).map((column, colIndex) => {
            const value = column.dataIndex ? record[column.dataIndex] : undefined;
            return (
              <div key={column.key ?? `${rowIndex}-${colIndex}`}>
                {column.render ? column.render(value, record, rowIndex) : String(value ?? '')}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  ),
}));

describe('AssetList hard delete modal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      isAdmin: true,
    });
  });

  it('does not emit antd space deprecation warnings when opening hard delete modal', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const onHardDelete = vi.fn();

    try {
      renderWithProviders(
        <AssetList
          data={{
            items: [
              {
                id: 'asset-1',
                asset_name: '测试物业',
                address: '测试地址',
                owner_party_name: '测试权属方',
                ownership_status: '已确权',
                property_nature: '经营性',
                usage_status: '出租',
                include_in_occupancy_rate: true,
                is_sublease: false,
                is_litigated: false,
                data_status: DataStatus.DELETED,
                created_at: '2026-03-01T00:00:00Z',
                updated_at: '2026-03-02T00:00:00Z',
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
            pages: 1,
          }}
          loading={false}
          onEdit={vi.fn()}
          onDelete={vi.fn()}
          onRestore={vi.fn()}
          onHardDelete={onHardDelete}
          onView={vi.fn()}
          onViewHistory={vi.fn()}
          onTableChange={vi.fn()}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: '彻底删除资产: 测试物业' }));

      expect(await screen.findByText('确认彻底删除')).toBeInTheDocument();
      expect(formatConsoleMessages(consoleErrorSpy.mock.calls)).not.toContain('[antd: Space]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });
});
