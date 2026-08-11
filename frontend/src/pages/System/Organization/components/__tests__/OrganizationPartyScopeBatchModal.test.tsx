import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import { organizationService } from '@/services/organizationService';
import OrganizationPartyScopeBatchModal from '../OrganizationPartyScopeBatchModal';

vi.mock('@/services/organizationService', () => ({
  organizationService: {
    previewOrganizationPartyScopeBatch: vi.fn(),
    commitOrganizationPartyScopeBatch: vi.fn(),
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

const organizations = [
  {
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
  },
  {
    id: 'org-2',
    name: '事业部B',
    code: 'DIV002',
    level: 1,
    sort_order: 0,
    type: 'division',
    status: 'active',
    is_deleted: false,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

describe('OrganizationPartyScopeBatchModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('previews and commits the same direct Party scope proposal for every selected organization', async () => {
    vi.mocked(organizationService.previewOrganizationPartyScopeBatch).mockResolvedValue({
      items: organizations.map(organization => ({
        organization,
        before_scope: {},
        after_scope: {
          represented_party_id: 'party-1',
          represented_party_perspective: 'owner',
          effective_party_id: 'party-1',
          effective_party_perspective: 'owner',
          source_organization_id: organization.id,
        },
        impact: {
          organization_count: 1,
          organization_scope_change_count: 1,
          user_count: 1,
          user_scope_change_count: 1,
        },
      })),
      impact: {
        organization_count: 2,
        organization_scope_change_count: 2,
        user_count: 2,
        user_scope_change_count: 2,
      },
      preview_token: 'batch-preview-token',
      expires_at: '2026-08-06T12:00:00Z',
    });
    vi.mocked(organizationService.commitOrganizationPartyScopeBatch).mockResolvedValue({
      items: [],
      impact: {
        organization_count: 2,
        organization_scope_change_count: 2,
        user_count: 2,
        user_scope_change_count: 2,
      },
      committed_at: '2026-08-06T12:01:00Z',
      idempotent: false,
    });
    const onClose = vi.fn();
    const onChanged = vi.fn();

    renderWithProviders(
      <OrganizationPartyScopeBatchModal
        open
        organizations={organizations}
        onClose={onClose}
        onChanged={onChanged}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '选择法人主体' }));
    fireEvent.mouseDown(screen.getByLabelText('批量默认视角'));
    fireEvent.click(await screen.findByText('产权方'));
    fireEvent.click(screen.getByRole('button', { name: '生成预览' }));

    await waitFor(() => {
      expect(organizationService.previewOrganizationPartyScopeBatch).toHaveBeenCalledWith({
        items: [
          {
            organization_id: 'org-1',
            represented_party_id: 'party-1',
            represented_party_perspective: 'owner',
          },
          {
            organization_id: 'org-2',
            represented_party_id: 'party-1',
            represented_party_perspective: 'owner',
          },
        ],
      });
    });

    fireEvent.change(screen.getByLabelText('批量变更原因'), {
      target: { value: '统一调整组织主体范围' },
    });
    fireEvent.click(screen.getByRole('button', { name: '提交变更' }));

    await waitFor(() => {
      expect(organizationService.commitOrganizationPartyScopeBatch).toHaveBeenCalledWith({
        preview_token: 'batch-preview-token',
        reason: '统一调整组织主体范围',
        idempotency_key: expect.any(String),
      });
      expect(onChanged).toHaveBeenCalledOnce();
      expect(onClose).toHaveBeenCalledOnce();
    });
  });
});

describe('fetchEligibleRepresentedParties（#82 服务端过滤）', () => {
  it('请求携带 review_status=approved 且结果透传不再客户端过滤', async () => {
    const { fetchEligibleRepresentedParties } = await import(
      '../OrganizationPartyScopeBatchModal'
    );
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
