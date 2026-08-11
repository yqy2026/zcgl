import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import OrganizationBindingDrawer from '../OrganizationBindingDrawer';
import { userService } from '@/services/systemService';
import { organizationService } from '@/services/organizationService';

vi.mock('@/services/systemService', () => ({
  userService: {
    getUsers: vi.fn(),
  },
}));

vi.mock('@/services/organizationService', () => ({
  organizationService: {
    previewOrganizationPartyScope: vi.fn(),
    commitOrganizationPartyScope: vi.fn(),
  },
}));

vi.mock('@/services/partyService', () => ({
  partyService: {
    searchParties: vi.fn(),
  },
}));

vi.mock('@/components/Common/PartySelector', () => ({
  default: ({ onChange }: { onChange?: (value?: string) => void }) => (
    <button type="button" onClick={() => onChange?.('party-1')}>
      选择法人主体
    </button>
  ),
}));

vi.mock('@/pages/System/UserManagement/components/UserPartyBindingModal', () => ({
  default: ({ open, user }: { open: boolean; user: { full_name: string } | null }) =>
    open ? <div data-testid="user-party-binding-modal">{user?.full_name}</div> : null,
}));

describe('OrganizationBindingDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(userService.getUsers).mockResolvedValue({
      items: [
        {
          id: 'user-1',
          username: 'alice',
          email: 'alice@example.com',
          full_name: 'Alice',
          phone: '13800138000',
          status: 'active',
          roles: ['executive'],
          role_ids: ['role-1'],
          account_type: 'human',
          organization_id: 'org-1',
          organization_name: '事业部A',
          last_login: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
          is_locked: false,
          login_attempts: 0,
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    });
  });

  it('loads organization users and opens the binding modal from the organization context', async () => {
    renderWithProviders(
      <OrganizationBindingDrawer
        open
        organization={{
          id: 'org-1',
          name: '事业部A',
          code: 'DIV001',
          level: 1,
          sort_order: 0,
          type: 'division',
          status: 'active',
          is_deleted: false,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        }}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(userService.getUsers).toHaveBeenCalledWith({
        organization_id: 'org-1',
        page_size: 100,
      });
    });

    expect(await screen.findByText('Alice')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /管理 Alice 用户数据范围/i }));

    expect(await screen.findByTestId('user-party-binding-modal')).toHaveTextContent('Alice');
  });

  it('updates the explicit represented party and perspective together', async () => {
    vi.mocked(organizationService.previewOrganizationPartyScope).mockResolvedValue({
      organization_id: 'org-1',
      before_scope: {},
      after_scope: {
        represented_party_id: 'party-1',
        represented_party_perspective: 'manager',
        effective_party_id: 'party-1',
        effective_party_perspective: 'manager',
        source_organization_id: 'org-1',
      },
      impact: {
        organization_count: 2,
        organization_scope_change_count: 2,
        user_count: 1,
        user_scope_change_count: 1,
      },
      preview_token: 'preview-token',
      expires_at: '2026-01-01T00:10:00Z',
    });
    vi.mocked(organizationService.commitOrganizationPartyScope).mockResolvedValue({
      organization: {
        id: 'org-1',
        name: '事业部A',
        code: 'DIV001',
        level: 1,
        sort_order: 0,
        type: 'division',
        status: 'active',
        represented_party_id: 'party-1',
        represented_party_perspective: 'manager',
        is_deleted: false,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      before_scope: {},
      after_scope: {},
      impact: {
        organization_count: 2,
        organization_scope_change_count: 2,
        user_count: 1,
        user_scope_change_count: 1,
      },
      committed_at: '2026-01-01T00:00:00Z',
      idempotent: false,
    });

    renderWithProviders(
      <OrganizationBindingDrawer
        open
        organization={{
          id: 'org-1',
          name: '事业部A',
          code: 'DIV001',
          level: 1,
          sort_order: 0,
          type: 'division',
          status: 'active',
          is_deleted: false,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        }}
        onClose={vi.fn()}
      />
    );

    fireEvent.click(await screen.findByRole('button', { name: '选择法人主体' }));
    fireEvent.mouseDown(screen.getByLabelText('默认视角'));
    fireEvent.click(await screen.findByText('管理方'));
    fireEvent.click(screen.getByRole('button', { name: '保存代表主体' }));

    await waitFor(() => {
      expect(organizationService.previewOrganizationPartyScope).toHaveBeenCalledWith('org-1', {
        represented_party_id: 'party-1',
        represented_party_perspective: 'manager',
      });
    });

    fireEvent.change(screen.getByLabelText('变更原因'), {
      target: { value: '组织权属调整' },
    });
    fireEvent.click(screen.getByRole('button', { name: '提交变更' }));

    await waitFor(() => {
      expect(organizationService.commitOrganizationPartyScope).toHaveBeenCalledWith('org-1', {
        preview_token: 'preview-token',
        reason: '组织权属调整',
        idempotency_key: expect.any(String),
      });
    });
  });
});

describe('fetchEligibleRepresentedParties（#82 服务端过滤）', () => {
  it('请求携带 review_status=approved 且结果透传不再客户端过滤', async () => {
    const { fetchEligibleRepresentedParties } = await import('../OrganizationBindingDrawer');
    const { partyService } = await import('@/services/partyService');
    vi.mocked(partyService.searchParties).mockResolvedValue({
      items: [
        {
          id: 'party-approved',
          name: '已审核主体',
          code: 'LE-000001',
          party_type: 'legal_entity',
          business_roles: ['owner'],
          status: 'active',
          review_status: 'approved',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'party-draft',
          name: '草稿主体',
          code: 'LE-000002',
          party_type: 'legal_entity',
          business_roles: ['owner'],
          status: 'active',
          review_status: 'draft',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      skip: 0,
      limit: 20,
      isTruncated: false,
    });

    const result = await fetchEligibleRepresentedParties('acme');

    expect(partyService.searchParties).toHaveBeenCalledWith('acme', {
      party_type: 'legal_entity',
      status: 'active',
      review_status: 'approved',
      limit: 20,
    });
    // 服务端负责过滤：客户端透传结果，不再 .filter(review_status === 'approved')
    expect(result).toHaveLength(2);
    expect(result.some(party => party.review_status === 'draft')).toBe(true);
  });
});
