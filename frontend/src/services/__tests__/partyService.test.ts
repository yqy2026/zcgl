import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorType } from '@/types/apiResponse';
import { PartyService } from '../partyService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn(error => ({
      message: error instanceof Error ? error.message : String(error),
    })),
  },
}));

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';

describe('PartyService', () => {
  let service: PartyService;

  beforeEach(() => {
    service = new PartyService();
    vi.clearAllMocks();
  });

  it('normalizes list response when backend returns raw array', async () => {
    const mockItems = [{ id: 'party-1', name: '甲方' }] as Array<Record<string, unknown>>;
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: mockItems,
    });

    const result = await service.getParties({ skip: 10, limit: 50 });

    expect(result.items).toEqual(mockItems);
    expect(result.skip).toBe(10);
    expect(result.limit).toBe(50);
    expect(result.isTruncated).toBe(false);
  });

  it('passes the business role filter to the Party list endpoint', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [],
    });

    await service.getParties({ business_role: 'operator' });

    expect(apiClient.get).toHaveBeenCalledWith(
      '/parties',
      expect.objectContaining({
        params: expect.objectContaining({ business_role: 'operator' }),
      })
    );
  });

  it('passes the review_status filter to the Party list endpoint (#81)', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [],
    });

    await service.searchParties('acme', { review_status: 'approved' });

    expect(apiClient.get).toHaveBeenCalledWith(
      '/parties',
      expect.objectContaining({
        params: expect.objectContaining({
          search: 'acme',
          review_status: 'approved',
        }),
      })
    );
  });
  it('normalizes list response when backend returns paged envelope', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        items: [{ id: 'party-1', name: '甲方' }],
        total: 101,
        skip: 0,
        limit: 20,
      },
    });

    const result = await service.getParties({ limit: 20 });

    expect(result.items).toHaveLength(1);
    expect(result.total).toBe(101);
    expect(result.isTruncated).toBe(true);
  });

  it('searches parties with default limit=20', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [],
    });

    await service.searchParties('  acme  ');

    expect(apiClient.get).toHaveBeenCalledWith(
      '/parties',
      expect.objectContaining({
        params: expect.objectContaining({
          search: 'acme',
          limit: 20,
        }),
      })
    );
  });

  it('fetches party by id', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: { id: 'party-1', name: '甲方' },
    });

    const result = await service.getPartyById('party-1');

    expect(result.id).toBe('party-1');
    expect(apiClient.get).toHaveBeenCalledWith(
      '/parties/party-1',
      expect.objectContaining({ cache: true })
    );
  });

  it('fetches customer profile by id', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        customer_party_id: 'party-1',
        customer_name: '终端租户甲',
        customer_type: 'external',
        historical_contract_count: 2,
        risk_tags: ['手工关注'],
        risk_tag_items: [{ tag: '手工关注', source: 'manual', updated_at: null }],
        contracts: [],
      },
    });

    const result = await service.getCustomerProfile('party-1');

    expect(result.customer_party_id).toBe('party-1');
    expect(apiClient.get).toHaveBeenCalledWith(
      '/customers/party-1',
      expect.objectContaining({ cache: true })
    );
  });

  it('creates and updates party', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        id: 'party-1',
        party_type: 'legal_entity',
        name: '甲方',
        code: 'LE-000001',
        identifier_type: 'unified_social_credit_code',
        identifier_display: '91440101231229726P',
      },
    });
    vi.mocked(apiClient.put).mockResolvedValue({
      success: true,
      data: {
        id: 'party-1',
        party_type: 'legal_entity',
        name: '甲方-更新',
        code: 'LE-000001',
      },
    });

    const created = await service.createParty({
      party_type: 'legal_entity',
      name: '甲方',
      identifier_type: 'unified_social_credit_code',
      identifier_value: '91440101231229726P',
    });
    const updated = await service.updateParty('party-1', {
      name: '甲方-更新',
      identifier_type: 'foreign_registration_number',
      identifier_value: 'HK-123456',
    });

    expect(created.id).toBe('party-1');
    expect(updated.name).toBe('甲方-更新');
    expect(apiClient.post).toHaveBeenCalledWith(
      '/parties',
      {
        party_type: 'legal_entity',
        name: '甲方',
        identifier_type: 'unified_social_credit_code',
        identifier_value: '91440101231229726P',
      },
      expect.objectContaining({ smartExtract: true })
    );
    expect(apiClient.put).toHaveBeenCalledWith(
      '/parties/party-1',
      {
        name: '甲方-更新',
        identifier_type: 'foreign_registration_number',
        identifier_value: 'HK-123456',
      },
      expect.objectContaining({ smartExtract: true })
    );
  });

  it('submits, approves, and rejects party review', async () => {
    vi.mocked(apiClient.post)
      .mockResolvedValueOnce({
        success: true,
        data: { id: 'party-1', review_status: 'pending' },
      })
      .mockResolvedValueOnce({
        success: true,
        data: { id: 'party-1', review_status: 'approved' },
      })
      .mockResolvedValueOnce({
        success: true,
        data: { id: 'party-1', review_status: 'rejected', review_reason: '资料不完整' },
      });

    const submitted = await service.submitReview('party-1');
    const approved = await service.approveReview('party-1');
    const rejected = await service.rejectReview('party-1', { reason: '资料不完整' });

    expect(submitted.review_status).toBe('pending');
    expect(approved.review_status).toBe('approved');
    expect(rejected.review_status).toBe('rejected');
    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      '/parties/party-1/submit-review',
      undefined,
      expect.objectContaining({ smartExtract: true })
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      '/parties/party-1/approve-review',
      undefined,
      expect.objectContaining({ smartExtract: true })
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      3,
      '/parties/party-1/reject-review',
      { reason: '资料不完整' },
      expect.objectContaining({ smartExtract: true })
    );
  });

  it('previews and commits approved party lifecycle changes through dedicated endpoints', async () => {
    const preview = {
      party_id: 'party-1',
      operation: 'deactivate' as const,
      before_state: {
        party_id: 'party-1',
        status: 'active',
        review_status: 'approved',
        available_for_new_references: true,
      },
      after_state: {
        party_id: 'party-1',
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
    const request = {
      preview_token: 'preview-token-1',
      reason: '停止主体的新增引用和有效范围。',
      idempotency_key: 'request-1',
    };
    const committed = {
      ...preview,
      party: { id: 'party-1', status: 'inactive' },
      committed_at: '2026-08-06T01:01:00Z',
      idempotent: false,
    };
    vi.mocked(apiClient.post)
      .mockResolvedValueOnce({ success: true, data: preview })
      .mockResolvedValueOnce({ success: true, data: committed });

    const previewResult = await service.previewLifecycle('party-1', { operation: 'deactivate' });
    const commitResult = await service.deactivate('party-1', request);

    expect(previewResult.preview_token).toBe('preview-token-1');
    expect(commitResult.party.status).toBe('inactive');
    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      '/parties/party-1/status/preview',
      { operation: 'deactivate' },
      expect.objectContaining({ smartExtract: true })
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      '/parties/party-1/deactivate',
      request,
      expect.objectContaining({ smartExtract: true })
    );
  });
  it('fetches representing organizations for a party', async () => {
    const mockOrgs = [
      {
        organization_id: 'org-1',
        name: '总部',
        code: 'ROOT',
        level: 1,
        status: 'active',
        parent_id: null,
        represented_party_perspective: 'owner',
      },
    ];
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: mockOrgs,
    });

    const result = await service.getRepresentingOrganizations('party-1');

    expect(result).toEqual(mockOrgs);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/parties/party-1/organizations',
      expect.objectContaining({
        cache: false,
        smartExtract: true,
        retry: expect.objectContaining({ maxAttempts: 2 }),
      })
    );
  });

  it('throws when representing organizations request fails', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: false,
      data: null,
      error: '网络错误',
    });

    await expect(service.getRepresentingOrganizations('party-1')).rejects.toThrow(
      '获取代表组织失败'
    );
  });

  it('manages contacts through party-scoped endpoints', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [{ id: 'contact-1', party_id: 'party-1', contact_name: '张三', is_primary: true }],
    });
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: { id: 'contact-2', party_id: 'party-1', contact_name: '李四', is_primary: false },
    });

    const contacts = await service.getPartyContacts('party-1');
    const created = await service.createPartyContact('party-1', {
      contact_name: '李四',
      contact_phone: '13800000000',
    });

    expect(contacts[0].contact_name).toBe('张三');
    expect(created.party_id).toBe('party-1');
    expect(apiClient.get).toHaveBeenCalledWith(
      '/parties/party-1/contacts',
      expect.objectContaining({ smartExtract: true })
    );
    expect(apiClient.post).toHaveBeenCalledWith(
      '/parties/party-1/contacts',
      { contact_name: '李四', contact_phone: '13800000000' },
      expect.objectContaining({ smartExtract: true })
    );
  });

  it('imports parties in batch', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        created_count: 1,
        error_count: 0,
        items: [{ index: 0, status: 'created', party_id: 'party-1', message: null }],
      },
    });

    const result = await service.importParties({
      items: [
        {
          party_type: 'legal_entity',
          name: '导入主体',
          identifier_type: 'unified_social_credit_code',
          identifier_value: '91440101231229726P',
        },
      ],
    });

    expect(result.created_count).toBe(1);
    expect(apiClient.post).toHaveBeenCalledWith(
      '/parties/import',
      {
        items: [
          {
            party_type: 'legal_entity',
            name: '导入主体',
            identifier_type: 'unified_social_credit_code',
            identifier_value: '91440101231229726P',
          },
        ],
      },
      expect.objectContaining({ smartExtract: true })
    );
  });

  it('preserves structured error metadata for forbidden detection consumers', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('request failed'));
    vi.mocked(ApiErrorHandler.handleError).mockReturnValue({
      type: ApiErrorType.AUTH_ERROR,
      code: 'HTTP_403',
      message: '权限不足，无法访问',
      statusCode: 403,
      timestamp: '2026-02-28T00:00:00Z',
    });

    await expect(service.searchParties('acme')).rejects.toMatchObject({
      message: '权限不足，无法访问',
      code: 'HTTP_403',
      statusCode: 403,
    });
  });
});
