import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ContractGroupService } from '../contractGroupService';

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
      message: error instanceof Error ? error.message : 'Unknown error',
      code: 'UNKNOWN',
    })),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

import { apiClient } from '@/api/client';

describe('ContractGroupService', () => {
  let service: ContractGroupService;

  beforeEach(() => {
    service = new ContractGroupService();
    vi.clearAllMocks();
  });

  it('lists contract groups with offset pagination', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        items: [
          {
            contract_group_id: 'group-1',
            group_code: 'GRP-TEST-202603-0001',
          },
        ],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });

    const result = await service.getContractGroups({
      offset: 0,
      limit: 20,
      revenue_mode: 'LEASE',
    });

    expect(result.total).toBe(1);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/contract-groups',
      expect.objectContaining({
        params: expect.objectContaining({
          offset: 0,
          limit: 20,
          revenue_mode: 'LEASE',
        }),
      })
    );
  });

  it('gets contract group detail', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        contract_group_id: 'group-1',
        group_code: 'GRP-TEST-202603-0001',
        contracts: [],
      },
    });

    const result = await service.getContractGroup('group-1');

    expect(result.contract_group_id).toBe('group-1');
    expect(apiClient.get).toHaveBeenCalledWith('/contract-groups/group-1', expect.any(Object));
  });

  it('creates a contract group', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        contract_group_id: 'group-1',
        group_code: 'GRP-TEST-202603-0001',
      },
    });

    await service.createContractGroup({
      revenue_mode: 'LEASE',
      operator_party_id: 'party-op',
      owner_party_id: 'party-owner',
      effective_from: '2026-03-01',
      settlement_rule: {
        version: 'v1',
        cycle: '月付',
        settlement_mode: 'manual',
        amount_rule: { basis: 'fixed' },
        payment_rule: { due_day: 15 },
      },
      asset_ids: [],
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/contract-groups',
      expect.objectContaining({
        revenue_mode: 'LEASE',
        operator_party_id: 'party-op',
      }),
      expect.any(Object)
    );
  });

  it('updates a contract group', async () => {
    vi.mocked(apiClient.put).mockResolvedValue({
      success: true,
      data: {
        contract_group_id: 'group-1',
        group_code: 'GRP-TEST-202603-0001',
      },
    });

    await service.updateContractGroup('group-1', {
      effective_to: '2026-12-31',
      settlement_rule: {
        version: 'v2',
        cycle: '季付',
        settlement_mode: 'manual',
        amount_rule: { basis: 'fixed' },
        payment_rule: { due_day: 15 },
      },
    });

    expect(apiClient.put).toHaveBeenCalledWith(
      '/contract-groups/group-1',
      expect.objectContaining({
        effective_to: '2026-12-31',
      }),
      expect.any(Object)
    );
  });
});
