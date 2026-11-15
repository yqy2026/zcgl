import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import HandoverDocumentsPanel from '@/pages/AssetOperations/HandoverDocumentsPanel';
import { handoverArchiveService } from '@/services/handoverArchiveService';
vi.mock('@/services/handoverArchiveService', () => ({ handoverArchiveService: { list: vi.fn() } }));
vi.mock('@/pages/AssetOperations/ArchiveDocumentsPanel', () => ({
  default: ({ targetId, readOnly }: { targetId: string; readOnly: boolean }) => (
    <p>
      {targetId} {readOnly ? '历史只读' : '可写档案'}
    </p>
  ),
}));
beforeEach(() => vi.clearAllMocks());
function show() {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <HandoverDocumentsPanel kind="upstream" contractId="parent" />
    </QueryClientProvider>
  );
}
it('shows an explicit empty state', async () => {
  vi.mocked(handoverArchiveService.list).mockResolvedValue([]);
  show();
  await screen.findByText('暂无终止或退出交接事项。');
  expect(handoverArchiveService.list).toHaveBeenCalledWith('upstream', 'parent');
});
it('uses server write eligibility for reversed history', async () => {
  vi.mocked(handoverArchiveService.list).mockResolvedValue([
    {
      event_id: 'event-secret',
      event_type: 'exited',
      effective_date: '2026-11-01',
      handover_status: 'pending',
      can_write: false,
      unavailable_reason: 'HANDOVER_EVENT_REVERSED',
    },
  ]);
  show();
  await screen.findByText(/已撤销/);
  expect(screen.queryByText('event-secret')).toBeNull();
  await userEvent.click(screen.getByRole('button', { name: '查看档案' }));
  await screen.findByText('event-secret 历史只读');
});

it('does not render cached targets when current scope is forbidden', async () => {
  const { AssetOperationsError } = await import('@/services/assetOperationsService');
  vi.mocked(handoverArchiveService.list).mockRejectedValue(
    new AssetOperationsError('范围变化', 'PARTY_SCOPE_MISSING')
  );
  show();
  await screen.findByText('访问范围或权限已变化，请联系管理员后重新加载。');
  expect(screen.queryByRole('button', { name: '查看档案' })).toBeNull();
});
