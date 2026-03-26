import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import { Route, Routes } from 'react-router-dom';

vi.mock('@/services/partyService', () => ({
  partyService: {
    getParties: vi.fn(),
    getPartyById: vi.fn(),
    createParty: vi.fn(),
    updateParty: vi.fn(),
    submitReview: vi.fn(),
    approveReview: vi.fn(),
    rejectReview: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

import PartyDetailPage from '../PartyDetailPage';
import PartyListPage from '../PartyListPage';
import { partyService } from '@/services/partyService';

const formatConsoleMessages = (calls: unknown[][]) =>
  calls
    .flat()
    .map(value => String(value))
    .join(' ');

const draftParty = {
  id: 'party-1',
  party_type: 'organization' as const,
  name: '测试主体',
  code: 'PTY-001',
  external_ref: 'EXT-1',
  status: 'active',
  review_status: 'draft' as const,
  review_by: null,
  reviewed_at: null,
  review_reason: null,
  metadata: { source: 'test' },
  created_at: '2026-03-12T08:00:00Z',
  updated_at: '2026-03-12T08:00:00Z',
};

const pendingParty = {
  ...draftParty,
  id: 'party-2',
  code: 'PTY-002',
  name: '待审核主体',
  review_status: 'pending' as const,
};

describe('Party system pages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(partyService.getParties).mockResolvedValue({
      items: [draftParty],
      total: 1,
      skip: 0,
      limit: 200,
      isTruncated: false,
    });
    vi.mocked(partyService.getPartyById).mockResolvedValue(draftParty);
    vi.mocked(partyService.createParty).mockResolvedValue(draftParty);
    vi.mocked(partyService.updateParty).mockResolvedValue({
      ...draftParty,
      name: '测试主体-更新',
    });
    vi.mocked(partyService.submitReview).mockResolvedValue({
      ...draftParty,
      review_status: 'pending',
    });
    vi.mocked(partyService.approveReview).mockResolvedValue({
      ...pendingParty,
      review_status: 'approved',
    });
    vi.mocked(partyService.rejectReview).mockResolvedValue({
      ...pendingParty,
      review_status: 'draft',
      review_reason: '资料不完整',
    });
  });

  it('renders party list and navigates to detail route', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/system/parties" element={<PartyListPage />} />
        <Route path="/system/parties/:id" element={<div>主体详情路由已命中</div>} />
      </Routes>,
      { route: '/system/parties' }
    );

    expect(await screen.findByText('主体主档管理')).toBeInTheDocument();
    expect(await screen.findByText('测试主体')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '查看主体测试主体详情' }));

    await waitFor(() => {
      expect(screen.getByText('主体详情路由已命中')).toBeInTheDocument();
    });
  });

  it('does not emit antd deprecation warnings while rendering the party list page', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      renderWithProviders(
        <Routes>
          <Route path="/system/parties" element={<PartyListPage />} />
        </Routes>,
        { route: '/system/parties' }
      );

      expect(await screen.findByText('主体主档管理')).toBeInTheDocument();
      expect(await screen.findByText('测试主体')).toBeInTheDocument();

      const messages = formatConsoleMessages(consoleErrorSpy.mock.calls);
      expect(messages).not.toContain('[antd: Space]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  it('updates and submits a draft party from detail page', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/system/parties/:id" element={<PartyDetailPage />} />
      </Routes>,
      { route: '/system/parties/party-1' }
    );

    expect(await screen.findByDisplayValue('测试主体')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('主体名称'), {
      target: { value: '测试主体-更新' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存变更' }));

    await waitFor(() => {
      expect(partyService.updateParty).toHaveBeenCalledWith(
        'party-1',
        expect.objectContaining({ name: '测试主体-更新' })
      );
    });

    fireEvent.click(screen.getByRole('button', { name: '提交审核' }));

    await waitFor(() => {
      expect(partyService.submitReview).toHaveBeenCalledWith('party-1');
    });
  });

  it('approves a pending party from detail page', async () => {
    vi.mocked(partyService.getPartyById).mockResolvedValue(pendingParty);

    renderWithProviders(
      <Routes>
        <Route path="/system/parties/:id" element={<PartyDetailPage />} />
      </Routes>,
      { route: '/system/parties/party-2' }
    );

    expect(await screen.findByText('待审核主体')).toBeInTheDocument();
    expect(screen.getByText('待审核主体不可编辑业务字段')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '审核通过' }));

    await waitFor(() => {
      expect(partyService.approveReview).toHaveBeenCalledWith('party-2');
    });
  });

  it('rejects a pending party from detail page', async () => {
    vi.mocked(partyService.getPartyById).mockResolvedValue(pendingParty);

    renderWithProviders(
      <Routes>
        <Route path="/system/parties/:id" element={<PartyDetailPage />} />
      </Routes>,
      { route: '/system/parties/party-2' }
    );

    expect(await screen.findByText('待审核主体')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '驳回审核' }));
    fireEvent.change(screen.getByLabelText('驳回原因'), {
      target: { value: '资料不完整' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认驳回' }));

    await waitFor(() => {
      expect(partyService.rejectReview).toHaveBeenCalledWith('party-2', {
        reason: '资料不完整',
      });
    });
  });

  it('does not emit antd deprecation warnings while rendering the party detail page', async () => {
    vi.mocked(partyService.getPartyById).mockResolvedValue(pendingParty);
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      renderWithProviders(
        <Routes>
          <Route path="/system/parties/:id" element={<PartyDetailPage />} />
        </Routes>,
        { route: '/system/parties/party-2' }
      );

      expect(await screen.findByText('待审核主体')).toBeInTheDocument();
      expect(screen.getByText('待审核主体不可编辑业务字段')).toBeInTheDocument();

      const messages = formatConsoleMessages(consoleErrorSpy.mock.calls);
      expect(messages).not.toContain('[antd: Space]');
      expect(messages).not.toContain('[antd: Alert]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });
});
