import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import ChangeTimelinePanel from '../ChangeTimelinePanel';
import {
  businessChangeService,
  type BusinessChangeEvent,
} from '@/services/businessChangeService';
import { AssetOperationsError } from '@/services/assetOperationsService';

vi.mock('@/services/businessChangeService', () => ({
  businessChangeService: { list: vi.fn() },
}));

const mocked = vi.mocked(businessChangeService.list);

function event(overrides: Partial<BusinessChangeEvent>): BusinessChangeEvent {
  return {
    id: 'event-1',
    target_type: 'upstream_contract',
    target_id: 'contract-1',
    action: 'updated',
    before: { deposit_amount: '***' },
    after: { deposit_amount: '***' },
    reason: '补录押金',
    actor_id: 'user-1',
    occurred_at: '2026-11-01T08:00:00Z',
    correlation_id: 'corr-1',
    summary: '修改押金金额',
    related_objects: [],
    ...overrides,
  };
}

function show(): void {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <ChangeTimelinePanel targetType="upstream_contract" targetId="contract-1" />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mocked.mockReset();
});

afterEach(() => {
  cleanup();
});

describe('ChangeTimelinePanel', () => {
  it('renders events with action label, time, summary and reason', async () => {
    mocked.mockResolvedValue({
      items: [event({ action: 'renewed', summary: '续签为 HT-2026-002' })],
      total: 1,
      page: 1,
      page_size: 50,
    });
    show();
    expect(await screen.findByText('续签为 HT-2026-002')).toBeInTheDocument();
    expect(screen.getByText('续签')).toBeInTheDocument();
    expect(screen.getByText(/原因：补录押金/)).toBeInTheDocument();
    expect(mocked).toHaveBeenCalledWith('upstream_contract', 'contract-1');
  });

  it('falls back to the raw action code when unmapped', async () => {
    mocked.mockResolvedValue({
      items: [event({ action: 'brand_new_action' })],
      total: 1,
      page: 1,
      page_size: 50,
    });
    show();
    expect(await screen.findByText('brand_new_action')).toBeInTheDocument();
  });

  it('shows the empty state when no events exist', async () => {
    mocked.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
    show();
    expect(await screen.findByText('暂无变更记录。')).toBeInTheDocument();
  });

  it('renders a scope warning instead of a hard error on PARTY_SCOPE failures', async () => {
    mocked.mockRejectedValue(
      new AssetOperationsError('无有效业务范围', 'PARTY_SCOPE_MISSING')
    );
    show();
    await waitFor(() =>
      expect(
        screen.getByText('没有可访问的数据范围，请联系管理员配置数据范围。')
      ).toBeInTheDocument()
    );
  });

  it('notes truncation when total exceeds the page size', async () => {
    mocked.mockResolvedValue({
      items: [event({})],
      total: 51,
      page: 1,
      page_size: 50,
    });
    show();
    expect(await screen.findByText(/仅展示最近 50 条/)).toBeInTheDocument();
  });
});
