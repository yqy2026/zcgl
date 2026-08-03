import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
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

vi.mock('@/services/ledgerService', () => ({
  ledgerService: {
    recalculateContractLedger: vi.fn(),
  },
}));

import { contractGroupService } from '@/services/contractGroupService';
import { ledgerService } from '@/services/ledgerService';

describe('ContractGroupDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(contractGroupService.getContractGroup).mockResolvedValue({
      contract_group_id: 'group-1',
      group_code: 'GRP-TEST-202603-0001',
      revenue_mode: 'lease',
      operator_party_id: 'party-op',
      owner_party_id: 'party-owner',
      effective_from: '2026-03-01',
      effective_to: '2026-12-31',
      derived_status: '生效中',
      data_status: '正常',
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-02T00:00:00Z',
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
          lessor_name_snapshot: '签署甲方',
          lessee_name_snapshot: '签署乙方',
          effective_from: '2026-03-01',
          effective_to: '2026-12-31',
          status: 'ACTIVE',
        },
      ],
    });
    vi.mocked(ledgerService.recalculateContractLedger).mockResolvedValue({
      created: 0,
      updated: 0,
      voided: 0,
      skipped_entries: [],
    });
  });

  it('renders contract relation details and nested contracts with business wording', async () => {
    renderWithProviders(<ContractGroupDetailPage />, { route: '/contract-center/group-1' });

    expect(
      await screen.findByRole('heading', { name: 'GRP-TEST-202603-0001' })
    ).toBeInTheDocument();
    expect(screen.getByText('合同关系编码')).toBeInTheDocument();
    expect(screen.getByText('承租转租')).toBeInTheDocument();
    expect(screen.getByText('固定金额')).toBeInTheDocument();
    expect(screen.getByText('每月 15 日')).toBeInTheDocument();
    expect(screen.getByText('高价值')).toBeInTheDocument();
    expect(screen.getByText('C-001')).toBeInTheDocument();
    expect(screen.getByText('上游承租合同')).toBeInTheDocument();
    expect(screen.getByText('签署甲方')).toBeInTheDocument();
    expect(screen.getByText('签署乙方')).toBeInTheDocument();
    expect(screen.queryByText('合同组详情')).not.toBeInTheDocument();
    expect(screen.queryByText('合同组编码')).not.toBeInTheDocument();
    expect(screen.queryByText('运营方主体 ID')).not.toBeInTheDocument();
    expect(screen.queryByText('产权方主体 ID')).not.toBeInTheDocument();
    expect(screen.queryByText('UPSTREAM')).not.toBeInTheDocument();
    expect(screen.queryByText('收益归属规则')).not.toBeInTheDocument();
    expect(screen.queryByText('收益分成规则')).not.toBeInTheDocument();
  });

  it('navigates to the edit page', async () => {
    renderWithProviders(<ContractGroupDetailPage />, { route: '/contract-center/group-1' });

    fireEvent.click(await screen.findByText('编辑合同关系'));

    expect(mockNavigate).toHaveBeenCalledWith('/contract-center/group-1/edit');
  });

  it('renders skipped paid ledger entries after recalculation', async () => {
    vi.mocked(ledgerService.recalculateContractLedger).mockResolvedValue({
      created: 1,
      updated: 2,
      voided: 0,
      skipped_entries: [
        {
          entry_id: 'entry-jan',
          year_month: '2026-01',
          payment_status: 'paid',
          reason: 'paid_or_partial_entry_requires_manual_resolution',
        },
      ],
    });

    renderWithProviders(<ContractGroupDetailPage />, { route: '/contract-center/group-1' });

    fireEvent.click(await screen.findByRole('button', { name: '重算台账' }));

    await waitFor(() => {
      expect(ledgerService.recalculateContractLedger).toHaveBeenCalledWith('contract-1');
    });
    expect(await screen.findByText('台账重算结果 - C-001')).toBeInTheDocument();
    expect(screen.getByText('2026-01')).toBeInTheDocument();
    expect(screen.getByText('已收/部分已收条目需人工对账处理')).toBeInTheDocument();
    expect(screen.getByText('存在已收或部分已收条目未自动改写')).toBeInTheDocument();
  });

  it('renders an empty settlement rule state when the group has no rule yet', async () => {
    vi.mocked(contractGroupService.getContractGroup).mockResolvedValue({
      contract_group_id: 'group-3',
      group_code: 'GRP-NO-RULE-202603-0001',
      revenue_mode: 'lease',
      operator_party_id: 'party-op',
      owner_party_id: 'party-owner',
      effective_from: '2026-03-01',
      effective_to: null,
      derived_status: '筹备中',
      data_status: '正常',
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-02T00:00:00Z',
      settlement_rule: null,
      revenue_attribution_rule: null,
      revenue_share_rule: null,
      risk_tags: [],
      upstream_contract_ids: [],
      downstream_contract_ids: [],
      contracts: [],
    });

    renderWithProviders(<ContractGroupDetailPage />, { route: '/contract-center/group-1' });

    expect(
      await screen.findByRole('heading', { name: 'GRP-NO-RULE-202603-0001' })
    ).toBeInTheDocument();
    expect(screen.getAllByText('未配置').length).toBeGreaterThan(0);
  });

  it('renders agency mode warning when the group is agency operated', async () => {
    vi.mocked(contractGroupService.getContractGroup).mockResolvedValue({
      contract_group_id: 'group-2',
      group_code: 'GRP-AGENCY-202603-0001',
      revenue_mode: 'agency',
      operator_party_id: 'party-op',
      owner_party_id: 'party-owner',
      effective_from: '2026-03-01',
      effective_to: '2026-12-31',
      derived_status: '生效中',
      data_status: '正常',
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-02T00:00:00Z',
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
          lessor_name_snapshot: '签署产权方',
          lessee_name_snapshot: '签署客户',
          effective_from: '2026-03-01',
          effective_to: '2026-12-31',
          status: 'ACTIVE',
        },
      ],
    });

    renderWithProviders(<ContractGroupDetailPage />, { route: '/contract-center/group-1' });

    expect(await screen.findByText('代理口径，非自营出租')).toBeInTheDocument();
  });
});
