import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import { ContractIntakePage } from '../ContractIntakePage';
import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type { ContractIntakeSession } from '@/services/assetOperationsService';

vi.mock(import('@/services/assetOperationsService'), async importOriginal => {
  const actual = await importOriginal<typeof import('@/services/assetOperationsService')>();
  return {
    ...actual,
    assetOperationsService: {
      ...actual.assetOperationsService,
      createIntakeSession: vi.fn(),
      getIntakeSession: vi.fn(),
      confirmUpstreamIntake: vi.fn(),
      confirmTerminalIntake: vi.fn(),
      cancelIntakeSession: vi.fn(),
    },
  };
});

const mockedService = vi.mocked(assetOperationsService);

function makeSession(overrides: Partial<ContractIntakeSession> = {}): ContractIntakeSession {
  return {
    id: 'session-1',
    documentId: 'doc-1',
    contractType: 'terminal',
    status: 'ready_for_review',
    candidateFields: {},
    warnings: [],
    expiresAt: '2026-10-25T12:00:00',
    ...overrides,
  };
}

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: 1, retryDelay: 0 },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/asset-operations/contracts/intake']}>
        <ContractIntakePage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mockedService.createIntakeSession.mockReset();
  mockedService.getIntakeSession.mockReset();
  mockedService.confirmTerminalIntake.mockReset();
  mockedService.confirmUpstreamIntake.mockReset();
  mockedService.cancelIntakeSession.mockReset();
});

afterEach(() => {
  cleanup();
});

describe('ContractIntakePage', () => {
  it('confirms management terms without deposit or payment inputs', async () => {
    const session = makeSession({ contractType: 'management_agreement' });
    mockedService.createIntakeSession.mockResolvedValue(session);
    mockedService.getIntakeSession.mockResolvedValue(session);
    mockedService.confirmUpstreamIntake.mockResolvedValue({
      id: 'management-1',
      contractNumber: 'MG-100',
      idempotent: false,
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole('button', { name: '委托管理协议' }));
    await user.upload(
      screen.getByLabelText('已签扫描件（PDF/图片）'),
      new File(['pdf'], 'scan.pdf', { type: 'application/pdf' })
    );
    await user.click(screen.getByRole('button', { name: '上传并创建会话' }));
    await user.type(await screen.findByLabelText('合同编号'), 'MG-100');
    expect(screen.queryByLabelText('押金金额')).toBeNull();
    await user.type(screen.getByLabelText('合同名称'), '委托协议');
    await user.type(screen.getByLabelText('产权方 Party ID'), 'owner-1');
    await user.type(screen.getByLabelText('运营方 Party ID'), 'operator-1');
    await user.type(screen.getByLabelText('起租日'), '2026-01-01');
    await user.type(screen.getByLabelText('到期日'), '2026-12-31');
    await user.type(screen.getByLabelText('覆盖资产单元 ID（逗号分隔）'), 'unit-1');
    await user.type(screen.getByLabelText('管理费比例（0-1）'), '0.1');
    await user.click(screen.getByRole('button', { name: '确认登记' }));
    await waitFor(() => expect(mockedService.confirmUpstreamIntake).toHaveBeenCalledTimes(1));
    const payload = mockedService.confirmUpstreamIntake.mock.calls[0]?.[1];
    expect(payload).toMatchObject({ deposit_amount: '0', management_fee_rate: '0.1' });
    expect(payload).not.toHaveProperty('payment_cycle');
    expect(payload).not.toHaveProperty('payment_day');
  });

  it('does not retry a rejected upload under the production mutation retry default', async () => {
    mockedService.createIntakeSession.mockRejectedValue(
      new AssetOperationsError(
        'upload extension is not allowed for this purpose',
        'VALIDATION_ERROR'
      )
    );
    const user = userEvent.setup();

    renderPage();
    await user.upload(
      screen.getByLabelText('已签扫描件（PDF/图片）'),
      new File(['pdf'], 'scan.pdf', { type: 'application/pdf' })
    );
    const uploadButton = screen.getByRole('button', { name: '上传并创建会话' });
    await user.click(uploadButton);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'upload extension is not allowed for this purpose'
    );
    expect(mockedService.createIntakeSession).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('heading', { name: '第一步 · 选择类型并上传扫描件' })).toBeVisible();
    expect(screen.queryByRole('heading', { name: /第二步/ })).toBeNull();
    expect(uploadButton).toBeEnabled();
  });

  it('uploads a file with the chosen contract type and enters the review step', async () => {
    mockedService.createIntakeSession.mockResolvedValue(
      makeSession({
        warnings: [
          {
            code: 'EXTRACTION_UNAVAILABLE',
            severity: 'warning',
            message: '自动提取不可用',
          },
        ],
      })
    );
    const user = userEvent.setup();
    const file = new File(['pdf'], 'scan.pdf', { type: 'application/pdf' });

    renderPage();

    await user.click(screen.getByRole('button', { name: '终端合同' }));
    const input = screen.getByLabelText('已签扫描件（PDF/图片）');
    await user.upload(input, file);
    await user.click(screen.getByRole('button', { name: '上传并创建会话' }));

    await waitFor(() => {
      expect(mockedService.createIntakeSession).toHaveBeenCalledWith('terminal', file);
    });
    await waitFor(() => {
      expect(screen.getByText(/手工核对/)).toBeTruthy();
    });
  });

  it('confirms a terminal contract with a generated idempotency key', async () => {
    mockedService.createIntakeSession.mockResolvedValue(makeSession());
    mockedService.getIntakeSession.mockResolvedValue(makeSession());
    mockedService.confirmTerminalIntake.mockResolvedValue({
      id: 'terminal-1',
      contractNumber: 'TM-100',
      idempotent: false,
    });
    const user = userEvent.setup();

    renderPage();
    const input = screen.getByLabelText('已签扫描件（PDF/图片）');
    await user.upload(input, new File(['pdf'], 'scan.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: '上传并创建会话' }));

    await user.type(await screen.findByLabelText('合同编号'), 'TM-100');
    await user.type(screen.getByLabelText('租户 Party ID'), 'tenant-1');
    await user.type(screen.getByLabelText('出租方 Party ID'), 'operator-1');
    await user.type(screen.getByLabelText('起租日'), '2026-01-01');
    await user.type(screen.getByLabelText('到期日'), '2026-12-31');
    await user.type(screen.getByLabelText('覆盖资产单元 ID（逗号分隔）'), 'unit-1');
    await user.click(screen.getByRole('button', { name: '确认登记' }));

    await waitFor(() => {
      expect(mockedService.confirmTerminalIntake).toHaveBeenCalledTimes(1);
    });
    expect(mockedService.confirmTerminalIntake).toHaveBeenCalledWith(
      'session-1',
      {
        contract_number: 'TM-100',
        tenant_party_id: 'tenant-1',
        lessor_party_id: 'operator-1',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        deposit_amount: '0',
        asset_unit_ids: ['unit-1'],
        rent_schedules: [],
      },
      expect.stringMatching(/.+/)
    );
    const [, , idempotencyKey] = mockedService.confirmTerminalIntake.mock.calls[0];
    expect(idempotencyKey).toMatch(/.+/);
    await waitFor(() => {
      expect(screen.getByText(/已登记合同 TM-100/)).toBeTruthy();
    });
  });

  it('cancels an unconfirmed session and returns to the upload step', async () => {
    mockedService.createIntakeSession.mockResolvedValue(makeSession());
    mockedService.cancelIntakeSession.mockResolvedValue(undefined);
    const user = userEvent.setup();

    renderPage();
    const input = screen.getByLabelText('已签扫描件（PDF/图片）');
    await user.upload(input, new File(['pdf'], 'scan.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: '上传并创建会话' }));

    await user.click(await screen.findByRole('button', { name: '取消录入' }));

    await waitFor(() => {
      expect(mockedService.cancelIntakeSession).toHaveBeenCalledWith('session-1');
    });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '上传并创建会话' })).toBeTruthy();
    });
  });

  it('surfaces scope 403 as a warning rather than a generic error', async () => {
    mockedService.createIntakeSession.mockRejectedValue(
      new AssetOperationsError('创建录入会话失败', 'ASSET_OPS_PERMISSION_DENIED')
    );
    const user = userEvent.setup();

    renderPage();
    const input = screen.getByLabelText('已签扫描件（PDF/图片）');
    await user.upload(input, new File(['pdf'], 'scan.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: '上传并创建会话' }));

    await waitFor(() => {
      expect(mockedService.createIntakeSession).toHaveBeenCalled();
    });
    expect(screen.queryByText('没有可访问的资产范围，请联系管理员配置数据范围。')).toBeNull();
  });
});
