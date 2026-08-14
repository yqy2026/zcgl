import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/utils/test-helpers';
import type { AnalyticsData } from '@/types/analytics';
import AssetDistributionGrid from '../AssetDistributionGrid';

const pieChartMock = vi.fn(() => <div data-testid="pie-chart" />);
const barChartMock = vi.fn(() => <div data-testid="bar-chart" />);

vi.mock('@/components/Analytics/AnalyticsChart', () => ({
  AnalyticsPieChart: (props: unknown) => pieChartMock(props),
  AnalyticsBarChart: (props: unknown) => barChartMock(props),
  chartDataUtils: {
    toPieData: (items: Array<{ name: string; count: number; percentage: number }>) =>
      items.map(item => ({ type: item.name, value: item.count, percentage: item.percentage })),
    toAreaData: (items: Array<{ name: string; total_area: number; area_percentage: number }>) =>
      items.map(item => ({
        type: item.name,
        value: item.total_area,
        percentage: item.area_percentage,
      })),
    toAreaBarData: (items: Array<{ name: string; total_area: number }>) =>
      items.map(item => ({ name: item.name, value: item.total_area })),
    toBusinessCategoryData: (items: Array<{ category: string; count: number }>) =>
      items.map(item => ({ name: item.category, value: item.count })),
    toBusinessCategoryAreaData: (items: Array<{ category: string; total_area: number }>) =>
      items.map(item => ({ name: item.category, value: item.total_area })),
  },
}));

const analyticsData = {
  property_nature_distribution: [{ name: '经营类', count: 3, percentage: 75 }],
  ownership_status_distribution: [{ status: '已确权', count: 2, percentage: 50 }],
  usage_status_distribution: [{ status: '出租', count: 2, percentage: 50 }],
  business_category_distribution: [
    {
      category: '商业',
      count: 2,
      percentage: 50,
    },
  ],
  property_nature_area_distribution: [
    { name: '经营类', count: 3, total_area: 300, area_percentage: 75, average_area: 100 },
  ],
  ownership_status_area_distribution: [
    { status: '已确权', count: 2, total_area: 200, area_percentage: 50, average_area: 100 },
  ],
  usage_status_area_distribution: [
    { status: '出租', count: 2, total_area: 180, area_percentage: 45, average_area: 90 },
  ],
  business_category_area_distribution: [
    {
      category: '商业',
      count: 2,
      total_area: 160,
      area_percentage: 40,
      average_area: 80,
    },
  ],
} as AnalyticsData;

describe('AssetDistributionGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('数量维度将四组非空分布传给图表', () => {
    renderWithProviders(
      <AssetDistributionGrid analyticsData={analyticsData} dimension="count" loading={false} />
    );

    expect(pieChartMock.mock.calls[0]?.[0]).toMatchObject({
      data: [{ type: '经营类', value: 3, percentage: 75 }],
    });
    expect(pieChartMock.mock.calls[1]?.[0]).toMatchObject({
      data: [{ type: '已确权', value: 2, percentage: 50 }],
    });
    expect(barChartMock.mock.calls[0]?.[0]).toMatchObject({
      data: [{ name: '出租', value: 2 }],
    });
    expect(barChartMock.mock.calls[1]?.[0]).toMatchObject({
      data: [{ name: '商业', value: 2 }],
    });
  });

  it('面积维度将四组可出租面积分布传给图表', () => {
    renderWithProviders(
      <AssetDistributionGrid analyticsData={analyticsData} dimension="area" loading={false} />
    );

    expect(pieChartMock.mock.calls[0]?.[0]).toMatchObject({
      data: [{ type: '经营类', value: 300, percentage: 75 }],
    });
    expect(pieChartMock.mock.calls[1]?.[0]).toMatchObject({
      data: [{ type: '已确权', value: 200, percentage: 50 }],
    });
    expect(barChartMock.mock.calls[0]?.[0]).toMatchObject({
      data: [{ name: '出租', value: 180 }],
    });
    expect(barChartMock.mock.calls[1]?.[0]).toMatchObject({
      data: [{ name: '商业', value: 160 }],
    });
  });
});
