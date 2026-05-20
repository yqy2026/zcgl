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

const minimalCreatePayload = {
  project_id: 'project-1',
  revenue_mode: 'LEASE' as const,
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
};

const minimalContractPayload = {
  contract_group_id: 'group-1',
  contract_number: 'HT-2026-001',
  contract_direction: 'LESSOR' as const,
  group_relation_type: 'UPSTREAM' as const,
  lessor_party_id: 'party-owner',
  lessee_party_id: 'party-op',
  effective_from: '2026-03-01',
  asset_ids: ['asset-1'],
  lease_detail: {
    rent_amount: '120000',
    payment_cycle: '月付',
  },
};

describe('ContractGroupService', () => {
  let service: ContractGroupService;

  beforeEach(() => {
    service = new ContractGroupService();
    vi.clearAllMocks();
  });

  it('lists contract relations with offset pagination', async () => {
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

  it('gets contract relation detail', async () => {
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

  it('creates a contract relation', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        contract_group_id: 'group-1',
        group_code: 'GRP-TEST-202603-0001',
      },
    });

    await service.createContractGroup(minimalCreatePayload);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/contract-groups',
      expect.objectContaining({
        project_id: 'project-1',
        revenue_mode: 'LEASE',
        operator_party_id: 'party-op',
      }),
      expect.any(Object)
    );
  });

  it('updates a contract relation', async () => {
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

  it('adds a contract to an existing contract relation', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: {
        contract_id: 'contract-1',
        contract_group_id: 'group-1',
        contract_number: 'HT-2026-001',
      },
    });

    const result = await service.addContractToGroup('group-1', minimalContractPayload);

    expect(result.contract_id).toBe('contract-1');
    expect(apiClient.post).toHaveBeenCalledWith(
      '/contract-groups/group-1/contracts',
      minimalContractPayload,
      expect.any(Object)
    );
  });

  it('uses contract relation wording for failed API responses', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ success: false, error: 'bad list' });

    await expect(service.getContractGroups()).rejects.toThrow('获取合同关系列表失败: bad list');

    vi.mocked(apiClient.get).mockResolvedValueOnce({ success: false, error: 'bad detail' });

    await expect(service.getContractGroup('group-1')).rejects.toThrow(
      '获取合同关系明细失败: bad detail'
    );

    vi.mocked(apiClient.post).mockResolvedValueOnce({ success: false, error: 'bad create' });

    await expect(service.createContractGroup(minimalCreatePayload)).rejects.toThrow(
      '创建合同关系失败: bad create'
    );

    vi.mocked(apiClient.put).mockResolvedValueOnce({ success: false, error: 'bad update' });

    await expect(
      service.updateContractGroup('group-1', {
        effective_to: '2026-12-31',
      })
    ).rejects.toThrow('更新合同关系失败: bad update');

    vi.mocked(apiClient.post).mockResolvedValueOnce({ success: false, error: 'bad contract' });

    await expect(service.addContractToGroup('group-1', minimalContractPayload)).rejects.toThrow(
      '添加合同失败: bad contract'
    );
  });
});
