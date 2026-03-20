import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import ContractImportReview from '../ContractImportReview';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
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

const buildResult = () => ({
  success: true,
  session_id: 'session-123',
  file_info: {
    filename: 'contract.pdf',
    size: 1024,
    content_type: 'application/pdf',
  },
  extraction_result: {
    success: true,
    data: {
      contract_number: 'HT-001',
      tenant_name: '测试租户',
      start_date: '2026-01-01',
      end_date: '2026-12-31',
      monthly_rent: '10000',
    },
    confidence_score: 98,
    extraction_method: 'smart',
    processed_fields: 5,
    total_fields: 5,
    warnings: [],
    field_evidence: null,
    field_sources: null,
  },
  validation_result: {
    success: true,
    errors: [],
    warnings: [],
    validated_data: {
      contract_number: 'HT-001',
      tenant_name: '测试租户',
      start_date: '2026-01-01',
      end_date: '2026-12-31',
      monthly_rent: 10000,
      total_deposit: 0,
      rent_terms: [],
    },
    validation_score: 96,
    processed_fields: 5,
    required_fields_count: 4,
    missing_required_fields: [],
  },
  matching_result: {
    matched_assets: [
      {
        id: 'asset-001',
        asset_name: '资产 A',
        address: '测试地址',
        similarity: 95,
      },
    ],
    matched_ownerships: [
      {
        id: 'party-owner',
        ownership_name: '产权方 A',
        similarity: 93,
      },
    ],
    duplicate_contracts: [],
    recommendations: {
      asset_id: 'asset-001',
      owner_party_id: 'party-owner',
    },
    match_confidence: 92,
  },
  summary: {
    extraction_confidence: 98,
    validation_score: 96,
    match_confidence: 92,
    total_confidence: 95,
  },
  recommendations: [],
  ready_for_import: true,
});

describe('ContractImportReview confirm context', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sanitizes invalid validated_data values before hydrating review fields', async () => {
    const result = buildResult();
    result.validation_result.validated_data = {
      ...result.validation_result.validated_data,
      revenue_mode: { invalid: true },
      contract_direction: { invalid: true },
      group_relation_type: { invalid: true },
      operator_party_id: { invalid: true },
      contract_number: { invalid: true },
      lessor_party_id: { invalid: true },
      lessee_party_id: { invalid: true },
      tenant_name: { invalid: true },
      tenant_contact: { invalid: true },
      sign_date: { invalid: true },
      rent_terms: { invalid: true },
    };

    renderWithProviders(
      <ContractImportReview
        sessionId="session-123"
        result={result}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        onBack={vi.fn()}
      />
    );

    expect(screen.getByPlaceholderText('请输入合同编号')).toHaveValue('');
    expect(screen.getByPlaceholderText('请输入承租方名称')).toHaveValue('');

    fireEvent.click(screen.getByRole('tab', { name: '新体系上下文' }));

    expect(screen.getByLabelText('经营模式')).toHaveValue('');
    expect(screen.getByLabelText('合同方向')).toHaveValue('');
    expect(screen.getByLabelText('合同角色')).toHaveValue('');
    expect(screen.getByLabelText('运营方主体 ID')).toHaveValue('');
    expect(screen.getByLabelText('出租方/委托方主体 ID')).toHaveValue('');
    expect(screen.getByLabelText('承租方/受托方主体 ID')).toHaveValue('');
  });

  it('submits the explicit contract-group context and navigates to the new group detail page', async () => {
    const onConfirm = vi.fn().mockResolvedValue({
      success: true,
      message: '导入成功',
      contract_group_id: 'group-123',
      contract_id: 'contract-456',
    });

    renderWithProviders(
      <ContractImportReview
        sessionId="session-123"
        result={buildResult()}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
        onBack={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('tab', { name: '新体系上下文' }));

    fireEvent.change(screen.getByLabelText('经营模式'), {
      target: { value: 'LEASE' },
    });
    fireEvent.change(screen.getByLabelText('合同方向'), {
      target: { value: 'LESSOR' },
    });
    fireEvent.change(screen.getByLabelText('合同角色'), {
      target: { value: 'UPSTREAM' },
    });
    fireEvent.change(screen.getByLabelText('运营方主体 ID'), {
      target: { value: 'party-operator' },
    });
    fireEvent.change(screen.getByLabelText('出租方/委托方主体 ID'), {
      target: { value: 'party-lessor' },
    });
    fireEvent.change(screen.getByLabelText('承租方/受托方主体 ID'), {
      target: { value: 'party-lessee' },
    });
    fireEvent.change(screen.getByLabelText('结算规则 JSON'), {
      target: {
        value:
          '{"version":"v1","cycle":"月付","settlement_mode":"manual","amount_rule":{"basis":"fixed"},"payment_rule":{"due_day":15}}',
      },
    });

    fireEvent.click(screen.getByRole('button', { name: '确认导入' }));

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith(
        expect.objectContaining({
          revenue_mode: 'LEASE',
          contract_direction: 'LESSOR',
          group_relation_type: 'UPSTREAM',
          operator_party_id: 'party-operator',
          owner_party_id: 'party-owner',
          lessor_party_id: 'party-lessor',
          lessee_party_id: 'party-lessee',
          asset_id: 'asset-001',
          settlement_rule: {
            version: 'v1',
            cycle: '月付',
            settlement_mode: 'manual',
            amount_rule: { basis: 'fixed' },
            payment_rule: { due_day: 15 },
          },
        })
      );
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/contract-groups/group-123');
    });
  });

  it('collects agency_detail fields when revenue_mode is AGENCY', async () => {
    const onConfirm = vi.fn().mockResolvedValue({
      success: true,
      message: '导入成功',
      contract_group_id: 'group-agency-123',
      contract_id: 'contract-agency-456',
    });

    renderWithProviders(
      <ContractImportReview
        sessionId="session-123"
        result={buildResult()}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
        onBack={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('tab', { name: '新体系上下文' }));

    fireEvent.change(screen.getByLabelText('经营模式'), {
      target: { value: 'AGENCY' },
    });
    fireEvent.change(screen.getByLabelText('合同方向'), {
      target: { value: 'LESSEE' },
    });
    fireEvent.change(screen.getByLabelText('合同角色'), {
      target: { value: 'ENTRUSTED' },
    });
    fireEvent.change(screen.getByLabelText('运营方主体 ID'), {
      target: { value: 'party-operator' },
    });
    fireEvent.change(screen.getByLabelText('出租方/委托方主体 ID'), {
      target: { value: 'party-owner' },
    });
    fireEvent.change(screen.getByLabelText('承租方/受托方主体 ID'), {
      target: { value: 'party-operator' },
    });
    fireEvent.change(screen.getByLabelText('结算规则 JSON'), {
      target: {
        value:
          '{"version":"v1","cycle":"月付","settlement_mode":"manual","amount_rule":{"basis":"actual_received"},"payment_rule":{"due_day":15}}',
      },
    });
    fireEvent.change(screen.getByLabelText('服务费比例'), {
      target: { value: '0.08' },
    });
    fireEvent.change(screen.getByLabelText('计费基数'), {
      target: { value: 'actual_received' },
    });
    fireEvent.change(screen.getByLabelText('代理范围说明'), {
      target: { value: '招商及代收租金' },
    });

    fireEvent.click(screen.getByRole('button', { name: '确认导入' }));

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith(
        expect.objectContaining({
          revenue_mode: 'AGENCY',
          contract_direction: 'LESSEE',
          group_relation_type: 'ENTRUSTED',
          operator_party_id: 'party-operator',
          owner_party_id: 'party-owner',
          lessor_party_id: 'party-owner',
          lessee_party_id: 'party-operator',
          agency_detail: {
            service_fee_ratio: '0.08',
            fee_calculation_base: 'actual_received',
            agency_scope: '招商及代收租金',
          },
        })
      );
    });
  });

  it('blocks confirm when fee_calculation_base is not an allowed enum value', async () => {
    const onConfirm = vi.fn().mockResolvedValue({
      success: true,
      message: '导入成功',
      contract_group_id: 'group-agency-123',
      contract_id: 'contract-agency-456',
    });

    renderWithProviders(
      <ContractImportReview
        sessionId="session-123"
        result={buildResult()}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
        onBack={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('tab', { name: '新体系上下文' }));

    fireEvent.change(screen.getByLabelText('经营模式'), {
      target: { value: 'AGENCY' },
    });
    fireEvent.change(screen.getByLabelText('合同方向'), {
      target: { value: 'LESSEE' },
    });
    fireEvent.change(screen.getByLabelText('合同角色'), {
      target: { value: 'ENTRUSTED' },
    });
    fireEvent.change(screen.getByLabelText('运营方主体 ID'), {
      target: { value: 'party-operator' },
    });
    fireEvent.change(screen.getByLabelText('出租方/委托方主体 ID'), {
      target: { value: 'party-owner' },
    });
    fireEvent.change(screen.getByLabelText('承租方/受托方主体 ID'), {
      target: { value: 'party-operator' },
    });
    fireEvent.change(screen.getByLabelText('结算规则 JSON'), {
      target: {
        value:
          '{"version":"v1","cycle":"月付","settlement_mode":"manual","amount_rule":{"basis":"actual_received"},"payment_rule":{"due_day":15}}',
      },
    });
    fireEvent.change(screen.getByLabelText('服务费比例'), {
      target: { value: '0.08' },
    });
    fireEvent.change(screen.getByLabelText('计费基数'), {
      target: { value: 'dueAmount' },
    });

    fireEvent.click(screen.getByRole('button', { name: '确认导入' }));

    await waitFor(() => {
      expect(onConfirm).not.toHaveBeenCalled();
      expect(screen.getByText('计费基数必须是 actual_received 或 due_amount')).toBeInTheDocument();
    });
  });
});
