import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen } from '@/test/utils/test-helpers';
import ContractGroupListPage from '../ContractGroupListPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/services/contractGroupService', () => ({
  contractGroupService: {
    getContractGroups: vi.fn(),
  },
}));

import { contractGroupService } from '@/services/contractGroupService';

describe('ContractGroupListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(contractGroupService.getContractGroups).mockResolvedValue({
      items: [
        {
          contract_group_id: 'group-1',
          group_code: 'GRP-TEST-202603-0001',
          revenue_mode: 'LEASE',
          operator_party_id: 'party-op',
          owner_party_id: 'party-owner',
          effective_from: '2026-03-01',
          effective_to: '2026-12-31',
          derived_status: '筹备中',
          data_status: '正常',
          created_at: '2026-03-01T00:00:00Z',
          updated_at: '2026-03-02T00:00:00Z',
        },
      ],
      total: 1,
      offset: 0,
      limit: 20,
    });
  });

  it('renders the list title, row data, and create action', async () => {
    renderWithProviders(<ContractGroupListPage />);

    expect(await screen.findByText('合同组管理')).toBeInTheDocument();
    expect(await screen.findByText('GRP-TEST-202603-0001')).toBeInTheDocument();
    expect(screen.getByText('新建合同组')).toBeInTheDocument();
  });

  it('navigates to the create page', async () => {
    renderWithProviders(<ContractGroupListPage />);

    fireEvent.click(await screen.findByText('新建合同组'));

    expect(mockNavigate).toHaveBeenCalledWith('/contract-groups/new');
  });

  it('navigates to the pdf import page', async () => {
    renderWithProviders(<ContractGroupListPage />);

    fireEvent.click(await screen.findByText('PDF导入'));

    expect(mockNavigate).toHaveBeenCalledWith('/contract-groups/import');
  });
});
