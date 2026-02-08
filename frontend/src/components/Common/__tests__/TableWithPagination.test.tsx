import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import { TableWithPagination } from '../TableWithPagination';

vi.mock('antd', () => ({
  Table: ({ dataSource }: { dataSource?: unknown[] }) => (
    <div data-testid="antd-table" data-row-count={dataSource?.length ?? 0}>
      antd-table
    </div>
  ),
  Pagination: ({ current, pageSize, total }: { current: number; pageSize: number; total: number }) => (
    <div
      data-testid="antd-pagination"
      data-current={current}
      data-page-size={pageSize}
      data-total={total}
    >
      antd-pagination
    </div>
  ),
}));

vi.mock('@/components/Common/ResponsiveTable', () => ({
  ResponsiveTable: ({ dataSource }: { dataSource?: unknown[] }) => (
    <div data-testid="responsive-table" data-row-count={dataSource?.length ?? 0}>
      responsive-table
    </div>
  ),
}));

interface TestRecord {
  id: string;
  name: string;
}

const testData: TestRecord[] = [{ id: '1', name: '资产A' }];

const baseProps = {
  dataSource: testData,
  columns: [{ title: '名称', dataIndex: 'name', key: 'name' }],
  rowKey: 'id' as const,
  paginationState: {
    current: 1,
    pageSize: 10,
    total: 1,
  },
  onPageChange: vi.fn(),
};

describe('TableWithPagination', () => {
  it('renders responsive table by default without runtime errors', () => {
    expect(() => {
      renderWithProviders(<TableWithPagination<TestRecord> {...baseProps} />);
    }).not.toThrow();

    expect(screen.getByTestId('responsive-table')).toBeInTheDocument();
    expect(screen.getByTestId('antd-pagination')).toBeInTheDocument();
  });

  it('renders antd table when responsive is false', () => {
    expect(() => {
      renderWithProviders(<TableWithPagination<TestRecord> {...baseProps} responsive={false} />);
    }).not.toThrow();

    expect(screen.getByTestId('antd-table')).toBeInTheDocument();
    expect(screen.getByTestId('antd-pagination')).toBeInTheDocument();
  });
});
