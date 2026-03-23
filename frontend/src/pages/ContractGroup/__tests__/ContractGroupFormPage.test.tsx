import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import ContractGroupFormPage from '../ContractGroupFormPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({}),
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
    vi.mocked(contractGroupService.createContractGroup).mockResolvedValue({
      contract_group_id: 'group-1',
      group_code: 'GRP-TEST-202603-0001',
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
});
