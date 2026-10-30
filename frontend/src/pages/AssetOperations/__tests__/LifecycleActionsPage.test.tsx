import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { TerminalActionsPage, UpstreamActionsPage } from '../LifecycleActionsPage';
import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type { ExitPreview, TerminationPreview } from '@/services/assetOperationsService';

vi.mock(import('@/services/assetOperationsService'), async importOriginal => {
  const actual = await importOriginal<typeof import('@/services/assetOperationsService')>();
  return {
    ...actual,
    assetOperationsService: {
      ...actual.assetOperationsService,
      previewTerminalTermination: vi.fn(),
      commitTerminalTermination: vi.fn(),
      previewUpstreamExit: vi.fn(),
      getUpstreamContract: vi.fn(),
      createIntakeSession: vi.fn(),
      renewTerminal: vi.fn(),
      renewUpstream: vi.fn(),
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
    depositSettlement: {
      entry_id: 'deposit',
      version: 2,
      held_amount: 100,
      candidates: [
        {
          ledger_entry_id: 'rent-one',
          remaining: 100,
          period_start: '2026-01-01',
          period_end: '2026-01-31',
          contract_id: 'terminal-1',
        },
      ],
      offsets: [{ ledger_entry_id: 'rent', amount: 40 }],
      clawback_amount: 0,
      clawback_basis: '',
      refundable_amount: 60,
      additional_due_amount: 20,
      recoverable_amount: 0,
    },
  };
}

function renderActionsPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: 1, retryDelay: 0 },
    },
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

function renderUpstreamActionsPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: 1, retryDelay: 0 },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/asset-operations/contracts/upstream/upstream-1/actions']}>
        <Routes>
          <Route
            path="/asset-operations/contracts/upstream/:contractId/actions"
            element={<UpstreamActionsPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mockedService.previewTerminalTermination.mockReset();
  mockedService.commitTerminalTermination.mockReset();
  mockedService.previewUpstreamExit.mockReset();
  mockedService.createIntakeSession.mockReset();
  mockedService.renewTerminal.mockReset();
  mockedService.renewUpstream.mockReset();
  mockedService.getUpstreamContract.mockResolvedValue({
    rentSchedules: [],
    rentSummary: null,
    id: 'upstream-1',
    contractNumber: 'UP-001',
    contractType: 'lease',
    name: '承租合同',
    ownerPartyId: 'owner-1',
    operatorPartyId: 'operator-1',
    startDate: '2026-01-01',
    endDate: '2026-12-31',
    paymentCycle: 'monthly',
    paymentDay: 15,
    depositAmount: 0,
    renewedFromId: null,
    version: 1,
    status: 'active',
    warnings: [],
    terminalContractIds: [],
    coverages: [],
    lifecycleEvents: [],
    renewalChain: [],
  });
});

afterEach(() => {
  cleanup();
});

it('renews a management agreement with the correct scan type and applicable terms', async () => {
  const lease = await mockedService.getUpstreamContract('upstream-1');
  mockedService.getUpstreamContract.mockResolvedValue({
    ...lease,
    contractType: 'management_agreement',
    paymentCycle: null,
    paymentDay: null,
  });
  mockedService.createIntakeSession.mockResolvedValue({
    id: 'renew-session',
    documentId: 'renew-scan',
    contractType: 'management_agreement',
    status: 'ready_for_review',
    candidateFields: {},
    warnings: [],
    expiresAt: '2026-12-31T00:00:00Z',
  });
  mockedService.renewUpstream.mockResolvedValue({
    id: 'successor',
    contractNumber: 'MG-002',
    idempotent: false,
  });
  const user = userEvent.setup();
  renderUpstreamActionsPage();
  const fee = await screen.findByLabelText('管理费比例（0–1）');
  await user.type(fee, '0.10');
  const file = new File(['pdf'], 'management-renewal.pdf', { type: 'application/pdf' });
  await user.upload(screen.getByLabelText('续签扫描件'), file);
  await user.type(screen.getByLabelText('后继合同编号'), 'MG-002');
  await user.type(screen.getByLabelText('后继合同名称'), '委托管理续签');
  await user.type(screen.getByLabelText('后继起租日'), '2027-01-01');
  await user.type(screen.getByLabelText('后继到期日'), '2027-12-31');
  await user.type(screen.getByLabelText('覆盖资产单元 ID（由原合同带出核对）'), 'unit-1');
  await user.click(screen.getByRole('button', { name: '登记续签' }));
  await waitFor(() => expect(mockedService.renewUpstream).toHaveBeenCalledTimes(1));
  expect(mockedService.createIntakeSession).toHaveBeenCalledWith('management_agreement', file);
  const payload = mockedService.renewUpstream.mock.calls[0]?.[1];
  expect(payload).toMatchObject({ management_fee_rate: '0.1', deposit_amount: '0' });
  expect(payload).not.toHaveProperty('payment_cycle');
  expect(payload).not.toHaveProperty('payment_day');
});

it.each([
  { type: 'terminal', renderPage: renderActionsPage },
  { type: 'upstream_lease', renderPage: renderUpstreamActionsPage },
])('does not retry a rejected $type renewal scan upload', async ({ type, renderPage }) => {
  const uploadError = new AssetOperationsError('扫描件无效', 'VALIDATION_ERROR');
  mockedService.createIntakeSession.mockRejectedValue(uploadError);
  const user = userEvent.setup();
  renderPage();
  const file = new File(['pdf'], 'renewal.pdf', { type: 'application/pdf' });
  await waitFor(() => expect(screen.getByLabelText('续签扫描件')).toBeEnabled());
  await user.upload(screen.getByLabelText('续签扫描件'), file);

  expect(await screen.findByRole('alert')).toHaveTextContent('扫描件无效');
  expect(mockedService.createIntakeSession).toHaveBeenCalledExactlyOnceWith(type, file);
  expect(screen.queryByText('扫描件已上传，可填写后继条款。')).toBeNull();
  expect(screen.getByRole('button', { name: '登记续签' })).toBeDisabled();
  expect(mockedService.renewTerminal).not.toHaveBeenCalled();
  expect(mockedService.renewUpstream).not.toHaveBeenCalled();
});

describe('UpstreamActionsPage', () => {
  it('previews an exit with React Hook Form values', async () => {
    const preview: ExitPreview = {
      contractId: 'upstream-1',
      contractVersion: 3,
      effectiveDate: '2026-07-01',
      lastValidDay: '2026-06-30',
      coverageImpact: [],
      warnings: [],
      previewToken: 'upstream-token-1',
      expiresAt: '2026-10-25T10:00:00',
    };
    mockedService.previewUpstreamExit.mockResolvedValue(preview);
    const user = userEvent.setup();

    renderUpstreamActionsPage();

    await user.type(screen.getByLabelText('退出生效日（该日起合同不再有效）'), '2026-07-01');
    await user.type(screen.getAllByLabelText('原因')[0], '提前退出');
    await user.click(screen.getByRole('button', { name: '预览退出影响' }));

    await waitFor(() => {
      expect(mockedService.previewUpstreamExit).toHaveBeenCalledWith('upstream-1', {
        effective_date: '2026-07-01',
        reason: '提前退出',
      });
    });
    expect(screen.getByText(/最后有效日 2026-06-30/)).toBeTruthy();
  });
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
        deposit_offset_mode: 'auto',
        clawback_amount: '0',
        clawback_basis: '',
        reason: '提前退租',
      });
    });
    expect(screen.getByText(/最后有效日 2026-06-29/)).toBeTruthy();
    expect(screen.getByText(/本次抵扣 40.00 元；待退还 60.00 元/)).toBeTruthy();
    expect(screen.getByText('租户仍需补缴租金 20.00 元。')).toBeTruthy();
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

  it('shows a business error when the termination preview is rejected', async () => {
    mockedService.previewTerminalTermination.mockRejectedValue(
      new AssetOperationsError('补收免租缺少依据', 'CLAWBACK_BASIS_REQUIRED')
    );
    const user = userEvent.setup();

    renderActionsPage();

    await user.type(screen.getByLabelText('终止生效日（该日起合同不再有效）'), '2026-06-30');
    await user.type(screen.getAllByLabelText('原因')[0], '提前退租');
    await user.click(screen.getByRole('button', { name: '预览终止影响' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('补收免租缺少依据');
    expect(screen.queryByText(/最后有效日/)).toBeNull();
  });
});

describe('preview business errors', () => {
  it('shows a business error when the upstream exit preview is rejected', async () => {
    mockedService.previewUpstreamExit.mockRejectedValue(
      new AssetOperationsError('退出生效日无效', 'EXIT_DATE_INVALID')
    );
    const user = userEvent.setup();

    renderUpstreamActionsPage();

    await user.type(screen.getByLabelText('退出生效日（该日起合同不再有效）'), '2027-01-01');
    await user.type(screen.getAllByLabelText('原因')[0], '提前退出');
    await user.click(screen.getByRole('button', { name: '预览退出影响' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('退出生效日无效');
    expect(screen.queryByText(/最后有效日/)).toBeNull();
  });
});

it('re-previews manual offset allocations and hides the previous confirmation', async () => {
  mockedService.previewTerminalTermination.mockResolvedValue(makePreview());
  const user = userEvent.setup();
  renderActionsPage();
  await user.type(screen.getByLabelText('终止生效日（该日起合同不再有效）'), '2026-06-30');
  await user.type(screen.getAllByLabelText('原因')[0], '提前退租');
  await user.click(screen.getByRole('button', { name: '预览终止影响' }));
  await screen.findByRole('button', { name: '确认终止' });
  await user.selectOptions(screen.getByLabelText('押金抵扣'), 'manual');
  expect(screen.queryByRole('button', { name: '确认终止' })).toBeNull();
  const amount = screen.getByLabelText(/2026-01-01 至 2026-01-31/);
  await user.clear(amount);
  await user.type(amount, '30');
  await user.click(screen.getByRole('button', { name: '预览终止影响' }));
  await waitFor(() =>
    expect(mockedService.previewTerminalTermination).toHaveBeenLastCalledWith(
      'terminal-1',
      expect.objectContaining({
        deposit_offset_mode: 'manual',
        deposit_offsets: [{ ledger_entry_id: 'rent-one', amount: '30' }],
      })
    )
  );
});
