import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen } from '@/test/utils/test-helpers';
import ContractGroupDetailPage from '../ContractGroupDetailPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: 'group-1' }),
  };
});

vi.mock('@/services/contractGroupService', () => ({
  contractGroupService: {
    getContractGroup: vi.fn(),
  },
}));

import { contractGroupService } from '@/services/contractGroupService';

describe('ContractGroupDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(contractGroupService.getContractGroup).mockResolvedValue({
      contract_group_id: 'group-1',
      group_code: 'GRP-TEST-202603-0001',
      revenue_mode: 'LEASE',
      operator_party_id: 'party-op',
      owner_party_id: 'party-owner',
      effective_from: '2026-03-01',
      effective_to: '2026-12-31',
      derived_status: '生效中',
      data_status: '正常',
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-02T00:00:00Z',
      version: 1,
      settlement_rule: {
        version: 'v1',
        cycle: '月付',
        settlement_mode: 'manual',
        amount_rule: { basis: 'fixed' },
        payment_rule: { due_day: 15 },
      },
      revenue_attribution_rule: null,
      revenue_share_rule: null,
      risk_tags: ['高价值'],
      predecessor_group_id: null,
      upstream_contract_ids: ['contract-1'],
      downstream_contract_ids: [],
      contracts: [
        {
          contract_id: 'contract-1',
          contract_number: 'C-001',
          contract_direction: 'INBOUND',
          group_relation_type: 'UPSTREAM',
          lessor_party_id: 'party-a',
          lessee_party_id: 'party-b',
          effective_from: '2026-03-01',
          effective_to: '2026-12-31',
          status: 'ACTIVE',
          review_status: 'APPROVED',
        },
      ],
    });
  });

  it('renders contract group details and nested contracts', async () => {
    renderWithProviders(<ContractGroupDetailPage />, { route: '/contract-groups/group-1' });

    expect(
      await screen.findByRole('heading', { name: 'GRP-TEST-202603-0001' })
    ).toBeInTheDocument();
    expect(screen.getByText('高价值')).toBeInTheDocument();
    expect(screen.getByText('C-001')).toBeInTheDocument();
    expect(screen.getByText('UPSTREAM')).toBeInTheDocument();
  });

  it('navigates to the edit page', async () => {
    renderWithProviders(<ContractGroupDetailPage />, { route: '/contract-groups/group-1' });

    fireEvent.click(await screen.findByText('编辑合同组'));

    expect(mockNavigate).toHaveBeenCalledWith('/contract-groups/group-1/edit');
  });

  it('renders agency mode warning when the group is agency operated', async () => {
    vi.mocked(contractGroupService.getContractGroup).mockResolvedValue({
      contract_group_id: 'group-2',
      group_code: 'GRP-AGENCY-202603-0001',
      revenue_mode: 'AGENCY',
      operator_party_id: 'party-op',
      owner_party_id: 'party-owner',
      effective_from: '2026-03-01',
      effective_to: '2026-12-31',
      derived_status: '生效中',
      data_status: '正常',
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-02T00:00:00Z',
      version: 1,
      settlement_rule: {
        version: 'v1',
        cycle: '月付',
        settlement_mode: 'manual',
        amount_rule: { basis: 'fixed' },
        payment_rule: { due_day: 15 },
      },
      revenue_attribution_rule: null,
      revenue_share_rule: null,
      risk_tags: [],
      predecessor_group_id: null,
      upstream_contract_ids: [],
      downstream_contract_ids: ['contract-2'],
      contracts: [
        {
          contract_id: 'contract-2',
          contract_number: 'C-AGENCY-001',
          contract_direction: 'OUTBOUND',
          group_relation_type: 'DIRECT_LEASE',
          lessor_party_id: 'party-owner',
          lessee_party_id: 'party-customer',
          effective_from: '2026-03-01',
          effective_to: '2026-12-31',
          status: 'ACTIVE',
          review_status: 'APPROVED',
        },
      ],
    });

    renderWithProviders(<ContractGroupDetailPage />, { route: '/contract-groups/group-1' });

    expect(await screen.findByText('代理口径，非自营出租')).toBeInTheDocument();
  });
});
