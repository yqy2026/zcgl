import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import { Route, Routes } from 'react-router-dom';
import { buildQueryScopeKey } from '@/utils/queryScope';

vi.mock('@/services/partyService', () => ({
  partyService: {
    getCustomerProfile: vi.fn(),
  },
}));

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: vi.fn(() => 'user:user-1|scope:owner,manager'),
}));

import CustomerDetailPage from '../CustomerDetailPage';
import { partyService } from '@/services/partyService';

describe('CustomerDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(partyService.getCustomerProfile).mockResolvedValue({
      customer_party_id: 'party-customer-1',
      customer_name: '终端租户甲',
      customer_type: 'external',
      subject_nature: 'enterprise',
      binding_type: 'manager',
      contract_role: 'entrusted_operation',
      contact_name: '张三',
      contact_phone: '13800000000',
      identifier_type: 'USCC',
      unified_identifier: '91310000123456789A',
      address: '上海市徐汇区测试路 1 号',
      status: 'active',
      historical_contract_count: 2,
      risk_tags: ['手工关注', '代理口径冲突'],
      risk_tag_items: [
        { tag: '手工关注', source: 'manual', updated_at: null },
        { tag: '代理口径冲突', source: 'rule', updated_at: '2026-03-30T00:00:00Z' },
      ],
      payment_term_preference: '月付',
      contracts: [
        {
          contract_id: 'contract-1',
          contract_number: 'CTR-001',
          group_code: 'GRP-001',
          revenue_mode: 'AGENCY',
          group_relation_type: 'DIRECT_LEASE',
          status: 'ACTIVE',
          effective_from: '2026-01-01T00:00:00Z',
          effective_to: '2026-12-31T00:00:00Z',
        },
      ],
    });
  });

  it('renders customer profile overview and contract history', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/customers/:id" element={<CustomerDetailPage />} />
      </Routes>,
      { route: '/customers/party-customer-1' }
    );

    expect(await screen.findByText('终端租户甲')).toBeInTheDocument();
    expect(screen.getByText('手工关注')).toBeInTheDocument();
    expect(screen.getByText('代理口径冲突')).toBeInTheDocument();
    expect(screen.getByText('CTR-001')).toBeInTheDocument();
    expect(screen.getByText('月付')).toBeInTheDocument();
    expect(buildQueryScopeKey).toHaveBeenCalledWith();
  });
});
