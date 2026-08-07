import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import { Route, Routes } from 'react-router-dom';
import type { Party } from '@/types/party';

vi.mock('@/services/partyService', () => ({
  partyService: {
    getParties: vi.fn(),
    getPartyById: vi.fn(),
    getCustomerProfile: vi.fn(),
    getReviewLogs: vi.fn(),
    getRepresentingOrganizations: vi.fn(),
    importParties: vi.fn(),
    createParty: vi.fn(),
    updateParty: vi.fn(),
    submitReview: vi.fn(),
    approveReview: vi.fn(),
    rejectReview: vi.fn(),
    previewLifecycle: vi.fn(),
    deactivate: vi.fn(),
    reactivate: vi.fn(),
  },
}));

vi.mock('../partyImport', () => ({
  parsePartyImportWorkbook: vi.fn(() =>
    Promise.resolve([
      {
        party_type: 'legal_entity',
        name: '导入主体',
        identifier_type: 'unified_social_credit_code',
        identifier_value: '91440101231229726P',
      },
    ])
  ),
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

const draftParty: Party = {
  id: 'party-1',
  business_roles: ['owner', 'terminal_tenant'],
  party_type: 'legal_entity' as const,
  name: '测试主体',
  code: 'LE-000001',
  identifier_type: 'unified_social_credit_code',
  identifier_display: '91440101231229726P',
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

const approvedParty = {
  ...draftParty,
  id: 'party-3',
  code: 'PTY-003',
  name: '已审核主体',
  review_status: 'approved' as const,
};

const lifecyclePreview = {
  party_id: 'party-3',
  operation: 'deactivate' as const,
  before_state: {
    party_id: 'party-3',
    status: 'active',
    review_status: 'approved',
    available_for_new_references: true,
  },
  after_state: {
    party_id: 'party-3',
    status: 'inactive',
    review_status: 'approved',
    available_for_new_references: false,
  },
  impact: {
    represented_organization_count: 1,
    potentially_affected_organization_count: 1,
    current_user_binding_count: 1,
    affected_user_count: 1,
    user_scope_change_count: 1,
    asset_reference_count: 0,
    project_reference_count: 0,
    contract_group_reference_count: 0,
    contract_reference_count: 0,
  },
  preview_token: 'preview-token-1',
  expires_at: '2026-08-06T01:10:00Z',
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
    vi.mocked(partyService.importParties).mockResolvedValue({
      created_count: 1,
      error_count: 0,
      items: [{ index: 0, status: 'created', party_id: 'party-import-1', message: null }],
    });
    vi.mocked(partyService.getReviewLogs).mockResolvedValue([
      {
        id: 'log-1',
        party_id: 'party-1',
        action: 'update',
        from_status: 'draft',
        to_status: 'draft',
        operator: 'tester',
        reason: 'fields:name',
        created_at: '2026-03-29T08:00:00Z',
      },
    ]);
    vi.mocked(partyService.getRepresentingOrganizations).mockResolvedValue([]);
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
      review_status: 'rejected',
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

  it('shows a blocking error state when the party list request fails', async () => {
    vi.mocked(partyService.getParties).mockRejectedValue(new Error('响应字段校验失败'));

    renderWithProviders(
      <Routes>
        <Route path="/system/parties" element={<PartyListPage />} />
      </Routes>,
      { route: '/system/parties' }
    );

    expect(await screen.findByText('主体列表加载失败')).toBeInTheDocument();
    expect(screen.getByText('响应字段校验失败')).toBeInTheDocument();
    expect(screen.queryByText('共 0 条主体记录')).not.toBeInTheDocument();
  });

  it('creates a party without accepting a client-owned code', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/system/parties" element={<PartyListPage />} />
      </Routes>,
      { route: '/system/parties' }
    );

    fireEvent.click(await screen.findByRole('button', { name: '新建主体' }));

    expect(screen.queryByLabelText('主体编码')).not.toBeInTheDocument();
    expect(screen.getByLabelText('统一标识类型')).toBeInTheDocument();
    expect(screen.getByLabelText('统一标识值')).toBeInTheDocument();
    expect(screen.queryByLabelText('状态')).not.toBeInTheDocument();
  });

  it('requests the selected business role slice from the server', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/system/parties" element={<PartyListPage />} />
      </Routes>,
      { route: '/system/parties' }
    );

    fireEvent.click(await screen.findByRole('tab', { name: '运营方' }));

    await waitFor(() => {
      expect(partyService.getParties).toHaveBeenLastCalledWith(
        expect.objectContaining({ business_role: 'operator' })
      );
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

  it('imports parties from workbook data on list page', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/system/parties" element={<PartyListPage />} />
      </Routes>,
      { route: '/system/parties' }
    );

    expect(await screen.findByText('主体主档管理')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '批量导入' }));
    fireEvent.change(screen.getByLabelText('主体导入文件'), {
      target: {
        files: [new File(['fake'], 'party-import.xlsx')],
      },
    });
    await screen.findByText('已选择文件：party-import.xlsx，已识别 1 条主体数据');
    fireEvent.click(screen.getByRole('button', { name: '开始导入' }));

    await waitFor(() => {
      expect(partyService.importParties).toHaveBeenCalledWith({
        items: [
          expect.objectContaining({
            name: '导入主体',
            identifier_type: 'unified_social_credit_code',
            identifier_value: '91440101231229726P',
          }),
        ],
      });
    });
  });

  it('updates and submits a draft party from detail page', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/system/parties/:id" element={<PartyDetailPage />} />
      </Routes>,
      { route: '/system/parties/party-1' }
    );

    expect(await screen.findByDisplayValue('测试主体')).toBeInTheDocument();
    expect(screen.getByText('91440101231229726P')).toBeInTheDocument();
    expect(screen.queryByLabelText('主体编码')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('业务状态')).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('主体名称'), {
      target: { value: '测试主体-更新' },
    });
    fireEvent.mouseDown(screen.getByLabelText('客户类型'));
    fireEvent.click(await screen.findByText('外部'));
    fireEvent.change(screen.getByLabelText('风险标签'), {
      target: { value: '手工关注,高频签约' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存变更' }));

    await waitFor(() => {
      expect(partyService.updateParty).toHaveBeenCalledWith(
        'party-1',
        expect.objectContaining({
          name: '测试主体-更新',
          metadata: expect.objectContaining({
            customer_type: 'external',
            risk_tags: ['手工关注', '高频签约'],
          }),
        })
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

  it('previews lifecycle impact and requires a reason before deactivating an approved party', async () => {
    vi.mocked(partyService.getPartyById).mockResolvedValue(approvedParty);
    vi.mocked(partyService.previewLifecycle).mockResolvedValue(lifecyclePreview);
    vi.mocked(partyService.deactivate).mockResolvedValue({
      ...lifecyclePreview,
      party: { ...approvedParty, status: 'inactive' },
      committed_at: '2026-08-06T01:01:00Z',
      idempotent: false,
    });

    renderWithProviders(
      <Routes>
        <Route path="/system/parties/:id" element={<PartyDetailPage />} />
      </Routes>,
      { route: '/system/parties/party-3' }
    );

    fireEvent.click(await screen.findByRole('button', { name: '停用主体' }));

    await waitFor(() => {
      expect(partyService.previewLifecycle).toHaveBeenCalledWith('party-3', {
        operation: 'deactivate',
      });
    });
    expect(partyService.deactivate).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText('停用原因'), {
      target: { value: '停止主体的新增引用和有效范围。' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认停用' }));

    await waitFor(() => {
      expect(partyService.deactivate).toHaveBeenCalledWith(
        'party-3',
        expect.objectContaining({
          preview_token: 'preview-token-1',
          reason: '停止主体的新增引用和有效范围。',
          idempotency_key: expect.any(String),
        })
      );
    });
  });
  it('previews and confirms reactivation for an inactive approved party', async () => {
    const inactiveApprovedParty = { ...approvedParty, status: 'inactive' };
    const reactivationPreview = {
      ...lifecyclePreview,
      operation: 'reactivate' as const,
      before_state: lifecyclePreview.after_state,
      after_state: lifecyclePreview.before_state,
      preview_token: 'preview-token-2',
    };
    vi.mocked(partyService.getPartyById).mockResolvedValue(inactiveApprovedParty);
    vi.mocked(partyService.previewLifecycle).mockResolvedValue(reactivationPreview);
    vi.mocked(partyService.reactivate).mockResolvedValue({
      ...reactivationPreview,
      party: { ...inactiveApprovedParty, status: 'active' },
      committed_at: '2026-08-06T01:02:00Z',
      idempotent: false,
    });

    renderWithProviders(
      <Routes>
        <Route path="/system/parties/:id" element={<PartyDetailPage />} />
      </Routes>,
      { route: '/system/parties/party-3' }
    );

    fireEvent.click(await screen.findByRole('button', { name: '重新启用主体' }));

    await waitFor(() => {
      expect(partyService.previewLifecycle).toHaveBeenCalledWith('party-3', {
        operation: 'reactivate',
      });
    });

    fireEvent.change(screen.getByLabelText('重新启用原因'), {
      target: { value: '关联组织已恢复有效配置。' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认启用' }));

    await waitFor(() => {
      expect(partyService.reactivate).toHaveBeenCalledWith(
        'party-3',
        expect.objectContaining({
          preview_token: 'preview-token-2',
          reason: '关联组织已恢复有效配置。',
          idempotency_key: expect.any(String),
        })
      );
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

  it('renders review log entries on detail page', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/system/parties/:id" element={<PartyDetailPage />} />
      </Routes>,
      { route: '/system/parties/party-1' }
    );

    expect(await screen.findByText('测试主体')).toBeInTheDocument();
    expect(await screen.findByText('fields:name')).toBeInTheDocument();
    expect(screen.getByText('update')).toBeInTheDocument();
  });

  it('renders the read-only representing organizations card with data', async () => {
    vi.mocked(partyService.getRepresentingOrganizations).mockResolvedValue([
      {
        organization_id: 'org-1',
        name: '总部',
        code: 'ROOT',
        level: 1,
        status: 'active',
        parent_id: null,
        represented_party_perspective: 'owner',
      },
      {
        organization_id: 'org-2',
        name: '华南分部',
        code: 'SOUTH',
        level: 2,
        status: 'active',
        parent_id: 'org-1',
        represented_party_perspective: 'manager',
      },
    ]);

    renderWithProviders(
      <Routes>
        <Route path="/system/parties/:id" element={<PartyDetailPage />} />
      </Routes>,
      { route: '/system/parties/party-1' }
    );

    expect(await screen.findByText('代表组织（只读）')).toBeInTheDocument();
    expect(await screen.findByText('总部')).toBeInTheDocument();
    expect(await screen.findByText('华南分部')).toBeInTheDocument();
    expect(screen.getByText('所有者')).toBeInTheDocument();
    expect(screen.getByText('管理者')).toBeInTheDocument();
    expect(await screen.findByText('共 2 个组织直接代表该主体')).toBeInTheDocument();
    expect(partyService.getRepresentingOrganizations).toHaveBeenCalledWith('party-1');
  });

  it('renders an empty state when no organizations represent the party', async () => {
    vi.mocked(partyService.getRepresentingOrganizations).mockResolvedValue([]);

    renderWithProviders(
      <Routes>
        <Route path="/system/parties/:id" element={<PartyDetailPage />} />
      </Routes>,
      { route: '/system/parties/party-1' }
    );

    expect(await screen.findByText('代表组织（只读）')).toBeInTheDocument();
    expect(await screen.findByText('暂无直接代表该主体的组织')).toBeInTheDocument();
  });
});
