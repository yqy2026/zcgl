import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { AnalyticsFiltersProvider, useAnalyticsFiltersContext } from '../Filters/FiltersContext';
import BasicFiltersSection from '../Filters/BasicFiltersSection';

vi.mock('@/hooks/useSearchHistory', () => ({
  useSearchHistory: vi.fn(() => ({
    searchHistory: [],
    addSearchHistory: vi.fn(),
    removeSearchHistory: vi.fn(),
    clearSearchHistory: vi.fn(),
  })),
}));

const MonthRangeProbe: React.FC = () => {
  const { handleDateRangeChange } = useAnalyticsFiltersContext();
  return (
    <button type="button" onClick={() => handleDateRangeChange(null, ['2026-08', '2026-10'])}>
      选择账期
    </button>
  );
};

const renderWithProvider = (onFiltersChange = vi.fn()) =>
  render(
    <AnalyticsFiltersProvider filters={{}} onFiltersChange={onFiltersChange} realTimeUpdate={false}>
      <BasicFiltersSection />
      <MonthRangeProbe />
    </AnalyticsFiltersProvider>
  );

describe('BasicFiltersSection - 账期范围（S3）', () => {
  it('筛选器标注「账期范围」并提示按租金账期归属', () => {
    renderWithProvider();

    expect(screen.getByText('账期范围:')).toBeInTheDocument();
    expect(screen.getByText('按租金账期归属')).toBeInTheDocument();
    expect(screen.queryByText('时间范围:')).not.toBeInTheDocument();
  });

  it('账期选择器为月粒度（不再使用日粒度选择器）', () => {
    renderWithProvider();

    expect(screen.getByPlaceholderText('开始月份')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('结束月份')).toBeInTheDocument();
  });

  it('选择账期月份后以 date_from/date_to（月边界日期）提交，不再使用 start_date/end_date', async () => {
    const onFiltersChange = vi.fn();
    renderWithProvider(onFiltersChange);

    fireEvent.click(screen.getByText('选择账期'));

    await waitFor(() => {
      expect(onFiltersChange).toHaveBeenCalledWith({
        date_from: '2026-08-01',
        date_to: '2026-10-31',
      });
    });
    expect(onFiltersChange.mock.calls[0][0].start_date).toBeUndefined();
    expect(onFiltersChange.mock.calls[0][0].end_date).toBeUndefined();
  });
});
