import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { TerminalActionsPage } from '../LifecycleActionsPage';
import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type { TerminationPreview } from '@/services/assetOperationsService';

vi.mock(import('@/services/assetOperationsService'), async importOriginal => {
  const actual = await importOriginal<typeof import('@/services/assetOperationsService')>();
  return {
    ...actual,
    assetOperationsService: {
      ...actual.assetOperationsService,
      previewTerminalTermination: vi.fn(),
      commitTerminalTermination: vi.fn(),
    },
  };
});

const mockedService = vi.mocked(assetOperationsService);

function makePreview(): TerminationPreview {
  return {
    contractId: 'terminal-1',
    contractVersion: 2,
    effectiveDate: '2026-06-30',
    lastValidDay: '2026-06-29',
    coverageImpact: [
      {
        assetUnitId: 'unit-1',
        effectiveFrom: '2026-01-01',
        currentEffectiveTo: '2026-12-31',
        newEffectiveTo: '2026-06-29',
      },
    ],
    warnings: [],
    previewToken: 'token-1',
    expiresAt: '2026-10-25T10:00:00',
  };
}

function renderActionsPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/asset-operations/contracts/terminal/terminal-1/actions']}>
        <Routes>
          <Route
            path="/asset-operations/contracts/terminal/:contractId/actions"
            element={<TerminalActionsPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mockedService.previewTerminalTermination.mockReset();
  mockedService.commitTerminalTermination.mockReset();
});

afterEach(() => {
  cleanup();
});

describe('TerminalActionsPage', () => {
  it('previews impact then commits with a generated idempotency key', async () => {
    mockedService.previewTerminalTermination.mockResolvedValue(makePreview());
    mockedService.commitTerminalTermination.mockResolvedValue({
      id: 'event-1',
      contractKind: 'terminal',
      contractId: 'terminal-1',
      eventType: 'terminated',
      effectiveDate: '2026-06-30',
      reason: '提前退租',
    });
    const user = userEvent.setup();

    renderActionsPage();

    await user.type(screen.getByLabelText('终止生效日（该日起合同不再有效）'), '2026-06-30');
    await user.type(screen.getAllByLabelText('原因')[0], '提前退租');
    await user.click(screen.getByRole('button', { name: '预览终止影响' }));

    await waitFor(() => {
      expect(mockedService.previewTerminalTermination).toHaveBeenCalledWith('terminal-1', {
        effective_date: '2026-06-30',
        termination_type: 'early',
        handover_status: 'pending',
        deposit_settlement_status: 'pending',
        reason: '提前退租',
      });
    });
    expect(screen.getByText(/最后有效日 2026-06-29/)).toBeTruthy();
    expect(screen.getByText(/2026-12-31 → 2026-06-29/)).toBeTruthy();

    await user.click(screen.getByRole('button', { name: '确认终止' }));

    await waitFor(() => {
      expect(mockedService.commitTerminalTermination).toHaveBeenCalledWith(
        'terminal-1',
        { preview_token: 'token-1', expected_version: 2 },
        expect.stringMatching(/.+/)
      );
    });
    await waitFor(() => {
      expect(screen.getByText(/终止已登记/)).toBeTruthy();
    });
  });

  it('shows the re-preview hint when the preview is stale on commit', async () => {
    mockedService.previewTerminalTermination.mockResolvedValue(makePreview());
    mockedService.commitTerminalTermination.mockRejectedValue(
      new AssetOperationsError('终止提交失败: PREVIEW_STALE', 'PREVIEW_STALE')
    );
    const user = userEvent.setup();

    renderActionsPage();

    await user.type(screen.getByLabelText('终止生效日（该日起合同不再有效）'), '2026-06-30');
    await user.type(screen.getAllByLabelText('原因')[0], '提前退租');
    await user.click(screen.getByRole('button', { name: '预览终止影响' }));
    await user.click(await screen.findByRole('button', { name: '确认终止' }));

    await waitFor(() => {
      expect(screen.getByText('预览已失效或版本已变化，请重新预览后再提交。')).toBeTruthy();
    });
  });
});
