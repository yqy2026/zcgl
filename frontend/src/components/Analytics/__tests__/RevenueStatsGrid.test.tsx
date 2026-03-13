import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RevenueStatsGrid } from '../AnalyticsStatsCard';

describe('RevenueStatsGrid (ANA-001)', () => {
  const baseData = {
    total_income: 150000,
    self_operated_rent_income: 100000,
    agency_service_income: 50000,
    customer_entity_count: 12,
    customer_contract_count: 18,
    metrics_version: 'req-ana-001-v1',
  };

  it('should render all 5 ANA-001 stat cards', () => {
    render(<RevenueStatsGrid data={baseData} />);

    expect(screen.getByText('总收入（经营口径）')).toBeInTheDocument();
    expect(screen.getByText('自营租金收入')).toBeInTheDocument();
    expect(screen.getByText('代理服务费收入')).toBeInTheDocument();
    expect(screen.getByText('客户主体数')).toBeInTheDocument();
    expect(screen.getByText('客户合同数')).toBeInTheDocument();
  });

  it('should display metrics_version tag', () => {
    render(<RevenueStatsGrid data={baseData} />);

    expect(screen.getByText('口径版本: req-ana-001-v1')).toBeInTheDocument();
  });

  it('should hide metrics_version tag when empty', () => {
    render(<RevenueStatsGrid data={{ ...baseData, metrics_version: '' }} />);

    expect(screen.queryByText(/口径版本/)).not.toBeInTheDocument();
  });

  it('should hide metrics_version tag when undefined', () => {
    const { metrics_version: _, ...dataWithoutVersion } = baseData;
    render(<RevenueStatsGrid data={dataWithoutVersion} />);

    expect(screen.queryByText(/口径版本/)).not.toBeInTheDocument();
  });

  it('should render zero values correctly (no data scenario)', () => {
    const zeroData = {
      total_income: 0,
      self_operated_rent_income: 0,
      agency_service_income: 0,
      customer_entity_count: 0,
      customer_contract_count: 0,
      metrics_version: 'req-ana-001-v1',
    };
    render(<RevenueStatsGrid data={zeroData} />);

    // All cards should still render with zero values
    expect(screen.getByText('总收入（经营口径）')).toBeInTheDocument();
    expect(screen.getByText('客户主体数')).toBeInTheDocument();
  });
});
