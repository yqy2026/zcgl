import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import ContractGroupFormPage from '../ContractGroupFormPage';

const mockNavigate = vi.fn();
const mockUseParams = vi.hoisted(() => vi.fn(() => ({})));

const formatConsoleMessages = (calls: unknown[][]) =>
  calls
    .flat()
    .map(value => String(value))
    .join(' ');

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockUseParams(),
  };
});

vi.mock('@/services/contractGroupService', () => ({
  contractGroupService: {
    createContractGroup: vi.fn(),
    getContractGroup: vi.fn(),
    updateContractGroup: vi.fn(),
  },
}));

import { contractGroupService } from '@/services/contractGroupService';

describe('ContractGroupFormPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({});
    vi.mocked(contractGroupService.createContractGroup).mockResolvedValue({
      contract_group_id: 'group-1',
      group_code: 'GRP-TEST-202603-0001',
    });
    vi.mocked(contractGroupService.getContractGroup).mockResolvedValue({
      contract_group_id: 'group-1',
      group_code: 'GRP-TEST-202603-0001',
      revenue_mode: 'LEASE',
      contract_direction: 'LESSOR',
      group_relation_type: 'UPSTREAM',
      operator_party_id: 'party-op',
      owner_party_id: 'party-owner',
      lessor_party_id: 'party-owner',
      lessee_party_id: 'party-lessee',
      effective_from: '2026-03-01',
      effective_to: null,
      asset_ids: [],
      settlement_rule: {
        version: 'v1',
        cycle: '月付',
        settlement_mode: 'manual',
        amount_rule: { basis: 'fixed' },
        payment_rule: { due_day: 15 },
      },
      current_contract_id: null,
      predecessor_group_id: null,
      sequence_no: 1,
      is_supplemental: false,
      lifecycle_status: 'DRAFT',
      termination_reason: null,
      signed_at: null,
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-01T00:00:00Z',
    });
  });

  it('submits the minimal create payload to the contract group service', async () => {
    renderWithProviders(<ContractGroupFormPage />, { route: '/contract-groups/new' });

    fireEvent.change(screen.getByLabelText('经营模式'), {
      target: { value: 'LEASE' },
    });

    fireEvent.change(screen.getByLabelText('运营方主体 ID'), {
      target: { value: 'party-op' },
    });
    fireEvent.change(screen.getByLabelText('产权方主体 ID'), {
      target: { value: 'party-owner' },
    });
    fireEvent.change(screen.getByLabelText('开始日期'), {
      target: { value: '2026-03-01' },
    });
    fireEvent.change(screen.getByLabelText('规则版本'), {
      target: { value: 'v1' },
    });
    fireEvent.change(screen.getByLabelText('结算周期'), {
      target: { value: '月付' },
    });
    fireEvent.change(screen.getByLabelText('结算模式'), {
      target: { value: 'manual' },
    });
    fireEvent.change(screen.getByLabelText('金额规则 JSON'), {
      target: { value: '{"basis":"fixed"}' },
    });
    fireEvent.change(screen.getByLabelText('支付规则 JSON'), {
      target: { value: '{"due_day":15}' },
    });

    fireEvent.click(screen.getByRole('button', { name: '创建合同组' }));

    await waitFor(() => {
      expect(contractGroupService.createContractGroup).toHaveBeenCalledWith({
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
    });
  });

  it('does not emit antd alert deprecation warnings when edit-mode loading fails', async () => {
    mockUseParams.mockReturnValue({ id: 'group-1' });
    vi.mocked(contractGroupService.getContractGroup).mockRejectedValueOnce(
      new Error('load failed')
    );
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      renderWithProviders(<ContractGroupFormPage />, { route: '/contract-groups/group-1/edit' });

      expect(await screen.findByText('load failed')).toBeInTheDocument();

      expect(formatConsoleMessages(consoleErrorSpy.mock.calls)).not.toContain('[antd: Alert]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });
});
