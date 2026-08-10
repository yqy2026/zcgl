import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { OperationalGroupsGrid } from '../AnalyticsStatsCard';

vi.setConfig({
  testTimeout: 20000,
  hookTimeout: 20000,
});

describe('OperationalGroupsGrid (ANA-001 四分组渲染)', () => {
  const groups = {
    terminal_collection: {
      label: '终端租户收缴',
      amount_due: 10000,
      paid_amount: 8500,
      outstanding_amount: 1500,
      collection_rate: 85,
    },
    operator_income: {
      label: '运营方收入',
      amount_due: 12000,
      paid_amount: 10000,
      outstanding_amount: 2000,
      collection_rate: 83.33,
    },
    operator_cost: {
      label: '运营方成本',
      amount_due: 6000,
      paid_amount: 4000,
      outstanding_amount: 2000,
      payment_rate: 66.67,
    },
    operating_result: {
      label: '经营结果',
      accrual_net_amount: 6000,
      cash_net_amount: 6000,
    },
  };

  it('应渲染四分组：终端租户收缴/运营方收入/运营方成本/经营结果', () => {
    render(<OperationalGroupsGrid groups={groups} />);

    expect(screen.getByText('终端租户收缴')).toBeInTheDocument();
    expect(screen.getByText('运营方收入')).toBeInTheDocument();
    expect(screen.getByText('运营方成本')).toBeInTheDocument();
    expect(screen.getByText('经营结果')).toBeInTheDocument();
  });

  it('经营结果卡以「经营净流入（已登记实收实付）」与「账面经营差额（应收应付）」双口径展示（M2）', () => {
    render(<OperationalGroupsGrid groups={groups} />);

    expect(screen.getByText('经营净流入（已登记实收实付）')).toBeInTheDocument();
    expect(screen.getByText(/账面经营差额（应收应付）/)).toBeInTheDocument();
  });

  it('终端租户收缴卡展示应收/未收明细', () => {
    render(<OperationalGroupsGrid groups={groups} />);

    expect(screen.getByText(/应收 ¥10,000/)).toBeInTheDocument();
    expect(screen.getByText(/未收 ¥1,500/)).toBeInTheDocument();
  });

  it('运营方成本卡展示应付/未付明细', () => {
    render(<OperationalGroupsGrid groups={groups} />);

    expect(screen.getByText(/应付 ¥6,000/)).toBeInTheDocument();
    expect(screen.getByText(/未付 ¥2,000/)).toBeInTheDocument();
  });

  it('groups 为空时不渲染任何内容', () => {
    const { container } = render(<OperationalGroupsGrid groups={undefined} />);

    expect(container.firstChild).toBeNull();
  });

  it('不出现「净收益」等会计式口径名（M3）', () => {
    render(<OperationalGroupsGrid groups={groups} />);

    expect(screen.queryByText('净收益')).not.toBeInTheDocument();
  });
});
