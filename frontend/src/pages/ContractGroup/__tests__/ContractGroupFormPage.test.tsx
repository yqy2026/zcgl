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
      sequence_no: 1,
      is_supplemental: false,
      lifecycle_status: 'DRAFT',
      termination_reason: null,
      signed_at: null,
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
        {
          id: 'asset-2',
          asset_name: '资产B',
          address: '项目内地址B',
          ownership_status: '已确权',
          property_nature: '经营性',
          usage_status: '空置',
          include_in_occupancy_rate: true,
          is_sublease: false,
          is_litigated: false,
          created_at: '2026-03-01T00:00:00Z',
          updated_at: '2026-03-01T00:00:00Z',
        },
      ],
      total: 2,
      summary: {
        total_assets: 2,
        total_rentable_area: 0,
        total_rented_area: 0,
        occupancy_rate: 0,
      },
    });
    vi.mocked(partyService.getParties).mockResolvedValue({
      items: [
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
      ],
      total: 2,
      skip: 0,
      limit: 500,
      isTruncated: false,
    });
  });

  it('submits the minimal create payload to the contract group service', async () => {
    renderWithProviders(<ContractGroupFormPage />, {
      route: '/contract-center/new?project_id=project-1',
    });

    fireEvent.change(screen.getByLabelText('经营模式'), {
      target: { value: 'LEASE' },
    });

    await screen.findAllByText('运营管理公司（OP-001）');
    expect(screen.getAllByText('运营管理公司（OP-001）').length).toBeGreaterThan(0);
    expect(screen.getAllByText('产权公司（OWN-001）').length).toBeGreaterThan(0);
    expect(partyService.getParties).toHaveBeenCalledWith({ limit: 500 });

    fireEvent.change(screen.getByLabelText('运营方主体'), {
      target: { value: 'party-op' },
    });
    fireEvent.change(screen.getByLabelText('产权方主体'), {
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
    fireEvent.change(screen.getByLabelText('计费依据'), {
      target: { value: 'fixed' },
    });
    fireEvent.change(screen.getByLabelText('付款日'), {
      target: { value: '15' },
    });
    fireEvent.change(screen.getByLabelText('收益归属口径'), {
      target: { value: 'operator' },
    });
    fireEvent.change(screen.getByLabelText('运营方分成比例（%）'), {
      target: { value: '30' },
    });

    expect(screen.getAllByText('新建合同关系').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('所属项目 ID')).toHaveValue('project-1');
    expect(await screen.findByText('资产A')).toBeInTheDocument();
    expect(screen.getByText('资产B')).toBeInTheDocument();
    expect(projectService.getProjectAssets).toHaveBeenCalledWith('project-1');
    expect(screen.queryByText('前序合同关系 ID')).not.toBeInTheDocument();
    expect(screen.queryByText('新建合同组')).not.toBeInTheDocument();
    expect(screen.queryByText('前驱合同组 ID')).not.toBeInTheDocument();
    expect(screen.queryByText('运营方主体 ID')).not.toBeInTheDocument();
    expect(screen.queryByText('产权方主体 ID')).not.toBeInTheDocument();
    expect(screen.queryByText('金额规则 JSON')).not.toBeInTheDocument();
    expect(screen.queryByText('支付规则 JSON')).not.toBeInTheDocument();
    expect(screen.queryByText('收益归属规则 JSON')).not.toBeInTheDocument();
    expect(screen.queryByText('收益分成规则 JSON')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('checkbox', { name: /资产A/ }));
    fireEvent.click(screen.getByRole('checkbox', { name: /资产B/ }));

    fireEvent.click(screen.getByRole('button', { name: '创建合同关系' }));

    await waitFor(() => {
      expect(contractGroupService.createContractGroup).toHaveBeenCalledWith({
        project_id: 'project-1',
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
        revenue_attribution_rule: { scope: 'operator' },
        revenue_share_rule: { operator_ratio_percent: 30 },
        asset_ids: ['asset-1', 'asset-2'],
      });
    });
  });

  it('shows empty project asset state when the project has no assets', async () => {
    vi.mocked(projectService.getProjectAssets).mockResolvedValueOnce({
      items: [],
      total: 0,
      summary: {
        total_assets: 0,
        total_rentable_area: 0,
        total_rented_area: 0,
        occupancy_rate: 0,
      },
    });

    renderWithProviders(<ContractGroupFormPage />, {
      route: '/contract-center/new?project_id=project-empty',
    });

    expect(await screen.findByText('该项目暂无可选资产')).toBeInTheDocument();
  });

  it('shows empty party state when there are no available parties', async () => {
    vi.mocked(partyService.getParties).mockResolvedValueOnce({
      items: [],
      total: 0,
      skip: 0,
      limit: 500,
      isTruncated: false,
    });

    renderWithProviders(<ContractGroupFormPage />, {
      route: '/contract-center/new?project_id=project-1',
    });

    expect(await screen.findByText('暂无可选主体')).toBeInTheDocument();
  });

  it('blocks creating a contract relation without project context', async () => {
    renderWithProviders(<ContractGroupFormPage />, { route: '/contract-center/new' });

    expect(await screen.findByText('请先从项目详情发起新建合同关系')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '创建合同关系' })).not.toBeInTheDocument();
  });

  it('renders edit mode with business wording instead of enum and subject id labels', async () => {
    mockUseParams.mockReturnValue({ id: 'group-1' });

    renderWithProviders(<ContractGroupFormPage />, { route: '/contract-center/group-1/edit' });

    await screen.findAllByText('编辑合同关系');
    expect(await screen.findByLabelText('经营模式')).toHaveValue('LEASE');
    expect(screen.getByText('承租转租')).toBeInTheDocument();
    expect(screen.queryByText('LEASE')).not.toBeInTheDocument();
    expect(screen.queryByText('AGENCY')).not.toBeInTheDocument();
    expect(screen.queryByText('运营方主体 ID')).not.toBeInTheDocument();
    expect(screen.queryByText('产权方主体 ID')).not.toBeInTheDocument();
  });

  it('does not emit antd alert deprecation warnings when edit-mode loading fails', async () => {
    mockUseParams.mockReturnValue({ id: 'group-1' });
    vi.mocked(contractGroupService.getContractGroup).mockRejectedValueOnce(
      new Error('load failed')
    );
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      renderWithProviders(<ContractGroupFormPage />, { route: '/contract-center/group-1/edit' });

      expect(await screen.findByText('load failed')).toBeInTheDocument();

      expect(formatConsoleMessages(consoleErrorSpy.mock.calls)).not.toContain('[antd: Alert]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });
});
