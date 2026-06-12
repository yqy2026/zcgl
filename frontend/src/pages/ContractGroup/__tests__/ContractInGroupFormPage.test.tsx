import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import ContractInGroupFormPage from '../ContractInGroupFormPage';

const mockNavigate = vi.fn();
const mockUseParams = vi.hoisted(() => vi.fn(() => ({ id: 'group-1' })));

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
    addContractToGroup: vi.fn(),
  },
}));

vi.mock('@/services/projectService', () => ({
  projectService: {
    getProjectAssets: vi.fn(),
  },
}));

vi.mock('@/services/partyService', () => ({
  partyService: {
    getParties: vi.fn(),
    searchParties: vi.fn(),
  },
}));

import { contractGroupService } from '@/services/contractGroupService';
import { partyService } from '@/services/partyService';
import { projectService } from '@/services/projectService';

describe('ContractInGroupFormPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ id: 'group-1' });
    vi.mocked(contractGroupService.addContractToGroup).mockResolvedValue({
      contract_id: 'contract-1',
      contract_group_id: 'group-1',
      contract_number: 'HT-2026-001',
      contract_direction: 'LESSOR',
      group_relation_type: 'UPSTREAM',
      lessor_party_id: 'party-owner',
      lessee_party_id: 'party-op',
      effective_from: '2026-03-01',
      effective_to: null,
      currency_code: 'CNY',
      is_tax_included: true,
      status: 'DRAFT',
      review_status: 'DRAFT',
      data_status: '正常',
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-01T00:00:00Z',
    });
    vi.mocked(projectService.getProjectAssets).mockResolvedValue({
      items: [
        {
          id: 'asset-1',
          asset_name: '资产A',
          address: '项目内地址A',
          ownership_status: '已确权',
          property_nature: '经营性',
          usage_status: '出租',
          include_in_occupancy_rate: true,
          is_sublease: false,
          is_litigated: false,
          created_at: '2026-03-01T00:00:00Z',
          updated_at: '2026-03-01T00:00:00Z',
        },
      ],
      total: 1,
      summary: {
        total_assets: 1,
        total_rentable_area: 0,
        total_rented_area: 0,
        occupancy_rate: 0,
      },
    });
    vi.mocked(partyService.getParties).mockResolvedValue({
      items: [
        {
          id: 'party-owner',
          party_type: 'legal_entity',
          name: '产权公司',
          code: 'OWN-001',
          status: 'active',
          review_status: 'approved',
          created_at: '2026-03-01T00:00:00Z',
          updated_at: '2026-03-01T00:00:00Z',
        },
        {
          id: 'party-op',
          party_type: 'legal_entity',
          name: '运营管理公司',
          code: 'OP-001',
          status: 'active',
          review_status: 'approved',
          created_at: '2026-03-01T00:00:00Z',
          updated_at: '2026-03-01T00:00:00Z',
        },
      ],
      total: 2,
      skip: 0,
      limit: 500,
      isTruncated: false,
    });
  });

  it('creates an upstream lease contract inside the selected relation', async () => {
    renderWithProviders(<ContractInGroupFormPage />, {
      route: '/contract-center/group-1/contracts/new?project_id=project-1&role=UPSTREAM',
    });

    expect(await screen.findByText('新增上游承租合同')).toBeInTheDocument();
    expect(screen.queryByText('UPSTREAM')).not.toBeInTheDocument();
    expect(screen.queryByText('主体 ID')).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('合同编号'), {
      target: { value: 'HT-2026-001' },
    });
    fireEvent.change(screen.getByLabelText('出租方/委托方主体'), {
      target: { value: 'party-owner' },
    });
    fireEvent.change(screen.getByLabelText('承租方/受托方主体'), {
      target: { value: 'party-op' },
    });
    fireEvent.change(screen.getByLabelText('开始日期'), {
      target: { value: '2026-03-01' },
    });
    fireEvent.change(screen.getByLabelText('租金总额'), {
      target: { value: '120000' },
    });
    fireEvent.click(await screen.findByRole('checkbox', { name: /资产A/ }));

    fireEvent.click(screen.getByRole('button', { name: '保存合同' }));

    await waitFor(() => {
      expect(contractGroupService.addContractToGroup).toHaveBeenCalledWith('group-1', {
        contract_group_id: 'group-1',
        contract_number: 'HT-2026-001',
        contract_direction: 'LESSOR',
        group_relation_type: 'UPSTREAM',
        lessor_party_id: 'party-owner',
        lessee_party_id: 'party-op',
        effective_from: '2026-03-01',
        asset_ids: ['asset-1'],
        lease_detail: {
          rent_amount: '120000',
          payment_cycle: '月付',
        },
      });
    });
    expect(mockNavigate).toHaveBeenCalledWith('/contract-center/group-1');
  });

  it('blocks contract creation when project context is missing', async () => {
    renderWithProviders(<ContractInGroupFormPage />, {
      route: '/contract-center/group-1/contracts/new?role=UPSTREAM',
    });

    expect(await screen.findByText('请先从项目合同关系卡片发起新增合同')).toBeInTheDocument();
    expect(screen.queryByText('保存合同')).not.toBeInTheDocument();
    expect(contractGroupService.addContractToGroup).not.toHaveBeenCalled();
  });

  it('requires selecting at least one project asset before saving', async () => {
    renderWithProviders(<ContractInGroupFormPage />, {
      route: '/contract-center/group-1/contracts/new?project_id=project-1&role=UPSTREAM',
    });

    expect(await screen.findByText('新增上游承租合同')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('合同编号'), {
      target: { value: 'HT-2026-002' },
    });
    fireEvent.change(await screen.findByLabelText('出租方/委托方主体'), {
      target: { value: 'party-owner' },
    });
    fireEvent.change(await screen.findByLabelText('承租方/受托方主体'), {
      target: { value: 'party-op' },
    });
    fireEvent.change(screen.getByLabelText('开始日期'), {
      target: { value: '2026-03-01' },
    });
    fireEvent.change(screen.getByLabelText('租金总额'), {
      target: { value: '120000' },
    });

    fireEvent.click(screen.getByRole('button', { name: '保存合同' }));

    expect(await screen.findByText('请选择合同资产范围')).toBeInTheDocument();
    expect(contractGroupService.addContractToGroup).not.toHaveBeenCalled();
  });

  it('creates an entrusted agency agreement with agency-facing party labels', async () => {
    renderWithProviders(<ContractInGroupFormPage />, {
      route: '/contract-center/group-1/contracts/new?project_id=project-1&role=ENTRUSTED',
    });

    expect(await screen.findByText('新增委托协议')).toBeInTheDocument();
    expect(await screen.findByLabelText('委托方主体')).toBeInTheDocument();
    expect(await screen.findByLabelText('受托方主体')).toBeInTheDocument();
    expect(screen.queryByText('ENTRUSTED')).not.toBeInTheDocument();
    expect(screen.queryByText('主体 ID')).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('合同编号'), {
      target: { value: 'WT-2026-001' },
    });
    fireEvent.change(screen.getByLabelText('委托方主体'), {
      target: { value: 'party-owner' },
    });
    fireEvent.change(screen.getByLabelText('受托方主体'), {
      target: { value: 'party-op' },
    });
    fireEvent.change(screen.getByLabelText('开始日期'), {
      target: { value: '2026-04-01' },
    });
    fireEvent.change(screen.getByLabelText('服务费比例（%）'), {
      target: { value: '5' },
    });
    fireEvent.click(await screen.findByRole('checkbox', { name: /资产A/ }));

    fireEvent.click(screen.getByRole('button', { name: '保存合同' }));

    await waitFor(() => {
      expect(contractGroupService.addContractToGroup).toHaveBeenCalledWith('group-1', {
        contract_group_id: 'group-1',
        contract_number: 'WT-2026-001',
        contract_direction: 'LESSEE',
        group_relation_type: 'ENTRUSTED',
        lessor_party_id: 'party-owner',
        lessee_party_id: 'party-op',
        effective_from: '2026-04-01',
        asset_ids: ['asset-1'],
        agency_detail: {
          service_fee_ratio: '0.05',
          fee_calculation_base: 'actual_received',
        },
      });
    });
    expect(mockNavigate).toHaveBeenCalledWith('/contract-center/group-1');
  });
});
