import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen } from '@/test/utils/test-helpers';
import { useQuery } from '@tanstack/react-query';

import ProjectDetailPage from '../ProjectDetailPage';

const mockBuildQueryScopeKey = vi.fn(() => 'user:user-1|scope:owner,manager');
const mockNavigate = vi.fn();

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: (value: unknown) => mockBuildQueryScopeKey(value),
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'project-1' }),
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/hooks/useArrayListData', () => ({
  useArrayListData: () => ({
    data: [],
    loading: false,
    pagination: { current: 1, pageSize: 10, total: 0 },
    loadList: vi.fn(),
    updatePagination: vi.fn(),
  }),
}));

describe('ProjectDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useQuery).mockImplementation(options => {
      const [scope] = options.queryKey as [string, ...unknown[]];
      if (scope === 'project') {
        return {
          data: {
            id: 'project-1',
            project_name: '项目A',
            project_code: 'PRJ-TEST-000001',
            status: 'active',
            data_status: '正常',
            created_at: '2026-03-01T00:00:00Z',
            updated_at: '2026-03-02T00:00:00Z',
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-assets') {
        return {
          data: {
            items: [
              {
                id: 'asset-1',
                asset_name: '资产A',
              },
            ],
            total: 1,
            summary: {
              total_assets: 1,
              total_rentable_area: 0,
              total_rented_area: 0,
              occupancy_rate: 0,
            },
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-contract-relations') {
        return {
          data: {
            items: [
              {
                contract_relation_id: 'group-lease',
                project_id: 'project-1',
                display_name: 'GRP-LEASE',
                revenue_mode: 'lease',
                relation_kind: 'lease_sublease',
                owner_party_id: 'owner-1',
                operator_party_id: 'manager-1',
                asset_ids: ['asset-1'],
                primary_contract_ids: ['contract-upstream'],
                terminal_contract_ids: ['contract-downstream'],
                derived_status: '生效中',
                risk_tags: ['到期风险'],
              },
              {
                contract_relation_id: 'group-agency',
                project_id: 'project-1',
                display_name: 'GRP-AGENCY',
                revenue_mode: 'agency',
                relation_kind: 'agency_operation',
                owner_party_id: 'owner-2',
                operator_party_id: 'manager-1',
                asset_ids: ['asset-2', 'asset-3'],
                primary_contract_ids: ['contract-entrusted'],
                terminal_contract_ids: ['contract-direct'],
                derived_status: '筹备中',
                risk_tags: null,
              },
            ],
            total: 2,
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-ledger-summary') {
        return {
          data: {
            receivable_amount: '2650.00',
            payable_amount: '1000.00',
            received_amount: '1400.00',
            paid_amount: '700.00',
            overdue_amount: '600.00',
            service_fee_receivable: '250.00',
            service_fee_received: '200.00',
            terminal_collection: {
              amount_due: '7400.00',
              paid_amount: '6200.00',
              outstanding_amount: '1200.00',
              overdue_amount: '600.00',
            },
            operator_income: {
              amount_due: '2650.00',
              paid_amount: '1400.00',
              outstanding_amount: '1250.00',
              overdue_amount: '0.00',
            },
            operator_cost: {
              amount_due: '1000.00',
              paid_amount: '700.00',
              outstanding_amount: '300.00',
              overdue_amount: '0.00',
            },
            service_fee_settlement: {
              amount_due: '250.00',
              paid_amount: '200.00',
              outstanding_amount: '50.00',
              overdue_amount: '0.00',
            },
            operating_result: {
              accrual_net_amount: '1650.00',
              cash_net_amount: '700.00',
            },
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-risks') {
        return {
          data: {
            items: [
              {
                risk_id: 'group-lease:manual_tag:到期风险',
                risk_type: 'manual_tag',
                severity: 'warning',
                message: '到期风险',
                contract_relation_id: 'group-lease',
                display_name: 'GRP-LEASE',
              },
            ],
            total: 1,
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-tenants') {
        return {
          data: {
            items: [
              {
                party_id: 'tenant-1',
                party_name: '终端租户甲',
                group_relation_type: '下游',
                contract_count: 2,
              },
              {
                party_id: 'tenant-2',
                party_name: '直租租户乙',
                group_relation_type: '直租',
                contract_count: 1,
              },
            ],
            total: 2,
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-analytics') {
        return {
          data: {
            asset_summary: {
              total_assets: 3,
              total_rentable_area: 300,
              total_rented_area: 210,
              occupancy_rate: 70,
            },
            contract_relation_count: 2,
            tenant_count: null,
            customer_contract_count: null,
            customer_metrics_suppression_reason: 'customer_metrics_requires_single_perspective',
            risk_count: 2,
            high_risk_count: 1,
            receivable_amount: '2650.00',
            payable_amount: '1000.00',
            received_amount: '1400.00',
            paid_amount: '700.00',
            overdue_amount: '600.00',
            service_fee_receivable: '250.00',
            service_fee_received: '200.00',
            mode_summaries: [
              {
                relation_kind: 'lease_sublease',
                label: '承租转租',
                contract_relation_count: 1,
                asset_count: 2,
                primary_contract_count: 1,
                terminal_contract_count: 1,
                customer_count: null,
                customer_contract_count: null,
                receivable_amount: '2400.00',
                payable_amount: '1000.00',
                received_amount: '1200.00',
                paid_amount: '700.00',
                overdue_amount: '600.00',
                risk_count: 1,
              },
              {
                relation_kind: 'agency_operation',
                label: '代理运营',
                contract_relation_count: 1,
                asset_count: 2,
                primary_contract_count: 1,
                terminal_contract_count: 1,
                customer_count: null,
                customer_contract_count: null,
                receivable_amount: '250.00',
                payable_amount: '0.00',
                received_amount: '200.00',
                paid_amount: '0.00',
                overdue_amount: '0.00',
                risk_count: 1,
              },
            ],
            monthly_trends: [
              {
                period: '2026-01',
                receivable_amount: '2000.00',
                payable_amount: '1000.00',
                received_amount: '1600.00',
                paid_amount: '1000.00',
                overdue_amount: '0.00',
              },
              {
                period: '2026-02',
                receivable_amount: '2650.00',
                payable_amount: '0.00',
                received_amount: '1400.00',
                paid_amount: '0.00',
                overdue_amount: '600.00',
              },
            ],
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'asset-lease-summary') {
        return {
          data: {
            total_contracts: 0,
            occupancy_rate: 0,
            customer_summary: [],
            by_type: [],
          },
          isLoading: false,
          error: null,
        };
      }
      return {
        data: undefined,
        isLoading: false,
        error: null,
      };
    });
  });

  it('project detail queries should include scope key in queryKey', () => {
    renderWithProviders(<ProjectDetailPage />);

    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project', 'user:user-1|scope:owner,manager', 'project-1'],
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project-assets', 'user:user-1|scope:owner,manager', 'project-1'],
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project-contract-relations', 'user:user-1|scope:owner,manager', 'project-1'],
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project-ledger-summary', 'user:user-1|scope:owner,manager', 'project-1'],
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project-risks', 'user:user-1|scope:owner,manager', 'project-1'],
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project-tenants', 'user:user-1|scope:owner,manager', 'project-1'],
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['project-analytics', 'user:user-1|scope:owner,manager', 'project-1'],
      })
    );
    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: [
          'asset-lease-summary',
          'user:user-1|scope:owner,manager',
          'asset-1',
          expect.any(String),
          expect.any(String),
        ],
      })
    );
    expect(mockBuildQueryScopeKey).toHaveBeenCalledWith(undefined);
  });

  it('uses canonical project route for back navigation', () => {
    renderWithProviders(<ProjectDetailPage />, { route: '/project/project-1' });

    fireEvent.click(screen.getByLabelText('返回'));

    expect(mockNavigate).toHaveBeenCalledWith('/project');
  });

  it('renders customer summary links that navigate to customer detail', () => {
    vi.mocked(useQuery).mockImplementation(options => {
      const [scope] = options.queryKey as [string, ...unknown[]];
      if (scope === 'project') {
        return {
          data: {
            id: 'project-1',
            project_name: '项目A',
            project_code: 'PRJ-TEST-000001',
            status: 'active',
            data_status: '正常',
            created_at: '2026-03-01T00:00:00Z',
            updated_at: '2026-03-02T00:00:00Z',
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-assets') {
        return {
          data: {
            items: [{ id: 'asset-1', asset_name: '资产A' }],
            total: 1,
            summary: {
              total_assets: 1,
              total_rentable_area: 0,
              total_rented_area: 0,
              occupancy_rate: 0,
            },
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'asset-lease-summary') {
        return {
          data: {
            total_contracts: 1,
            occupancy_rate: 0,
            customer_summary: [
              {
                party_id: 'party-customer-1',
                party_name: '终端租户甲',
                group_relation_type: '直租',
                contract_count: 1,
              },
            ],
            by_type: [],
          },
          isLoading: false,
          error: null,
        };
      }
      return { data: undefined, isLoading: false, error: null };
    });

    renderWithProviders(<ProjectDetailPage />, { route: '/project/project-1' });

    fireEvent.click(screen.getByRole('button', { name: '查看客户终端租户甲详情' }));

    expect(mockNavigate).toHaveBeenCalledWith('/customers/party-customer-1');
  });

  it('renders project contract relations as business-facing project content', () => {
    renderWithProviders(<ProjectDetailPage />, { route: '/project/project-1' });

    expect(screen.getAllByText('合同关系').length).toBeGreaterThan(0);
    expect(screen.getAllByText('承租转租').length).toBeGreaterThan(0);
    expect(screen.getAllByText('代理运营').length).toBeGreaterThan(0);
    expect(screen.getByText('收付款摘要')).toBeInTheDocument();
    expect(screen.getAllByText('终端租户收缴').length).toBeGreaterThan(0);
    expect(screen.getAllByText('运营方收入').length).toBeGreaterThan(0);
    expect(screen.getAllByText('运营方成本').length).toBeGreaterThan(0);
    expect(screen.getAllByText('服务费结算').length).toBeGreaterThan(0);
    expect(screen.getAllByText('经营净流入').length).toBeGreaterThan(0);
    expect(screen.getAllByText('¥6,200.00').length).toBeGreaterThan(0);
    expect(screen.getByText('¥1,400.00')).toBeInTheDocument();
    expect(screen.getAllByText('¥700.00').length).toBeGreaterThan(0);
    expect(screen.getByText('¥200.00')).toBeInTheDocument();
    expect(screen.getByText('应收 ¥7,400.00 / 未收 ¥1,200.00')).toBeInTheDocument();
    expect(screen.queryByText('待台账接入')).not.toBeInTheDocument();
    expect(screen.getByText('风险提示')).toBeInTheDocument();
    expect(screen.getByText('生效中')).toBeInTheDocument();
    expect(screen.getAllByText('到期风险').length).toBeGreaterThan(0);
    expect(screen.getByText('租户/客户')).toBeInTheDocument();
    expect(screen.getAllByText('客户主体').length).toBeGreaterThan(0);
    expect(screen.getByText('客户合同')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '查看客户终端租户甲详情' })).toBeInTheDocument();
    expect(screen.getByText('3 份合同')).toBeInTheDocument();
    expect(screen.getByText('项目分析')).toBeInTheDocument();
    expect(screen.getByText('经营风险')).toBeInTheDocument();
    expect(screen.getByText('客户指标需选产权方或运营方视图')).toBeInTheDocument();
    expect(screen.getAllByText('需选视图').length).toBeGreaterThan(0);
    expect(screen.getByText('项目分析趋势')).toBeInTheDocument();
    expect(screen.getByText('应收环比 +32.5%')).toBeInTheDocument();
    expect(screen.getByText('2026-02')).toBeInTheDocument();
    expect(screen.getAllByText('¥250.00').length).toBeGreaterThan(0);
    expect(screen.queryByText('合同组编码')).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: '查看明细' })[0]);

    expect(mockNavigate).toHaveBeenCalledWith('/contract-center/group-lease');
  });

  it('renders project risk panel from project risks endpoint', () => {
    vi.mocked(useQuery).mockImplementation(options => {
      const [scope] = options.queryKey as [string, ...unknown[]];
      if (scope === 'project') {
        return {
          data: {
            id: 'project-1',
            project_name: '项目A',
            project_code: 'PRJ-TEST-000001',
            status: 'active',
            data_status: '正常',
            created_at: '2026-03-01T00:00:00Z',
            updated_at: '2026-03-02T00:00:00Z',
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-assets') {
        return {
          data: {
            items: [],
            total: 0,
            summary: {
              total_assets: 0,
              total_rentable_area: 0,
              total_rented_area: 0,
              occupancy_rate: 0,
            },
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-contract-relations') {
        return {
          data: {
            items: [
              {
                contract_relation_id: 'group-lease',
                project_id: 'project-1',
                display_name: 'GRP-LEASE',
                revenue_mode: 'lease',
                relation_kind: 'lease_sublease',
                owner_party_id: 'owner-1',
                operator_party_id: 'manager-1',
                asset_ids: ['asset-1'],
                primary_contract_ids: [],
                terminal_contract_ids: ['contract-downstream'],
                derived_status: '生效中',
                risk_tags: null,
              },
            ],
            total: 1,
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-ledger-summary') {
        return {
          data: {
            receivable_amount: '0.00',
            payable_amount: '0.00',
            received_amount: '0.00',
            paid_amount: '0.00',
            overdue_amount: '0.00',
            service_fee_receivable: '0.00',
            service_fee_received: '0.00',
            terminal_collection: {
              amount_due: '0.00',
              paid_amount: '0.00',
              outstanding_amount: '0.00',
              overdue_amount: '0.00',
            },
            operator_income: {
              amount_due: '0.00',
              paid_amount: '0.00',
              outstanding_amount: '0.00',
              overdue_amount: '0.00',
            },
            operator_cost: {
              amount_due: '0.00',
              paid_amount: '0.00',
              outstanding_amount: '0.00',
              overdue_amount: '0.00',
            },
            service_fee_settlement: {
              amount_due: '0.00',
              paid_amount: '0.00',
              outstanding_amount: '0.00',
              overdue_amount: '0.00',
            },
            operating_result: {
              accrual_net_amount: '0.00',
              cash_net_amount: '0.00',
            },
          },
          isLoading: false,
          error: null,
        };
      }
      if (scope === 'project-risks') {
        return {
          data: {
            items: [
              {
                risk_id: 'group-lease:manual_tag:资料待复核',
                risk_type: 'manual_tag',
                severity: 'warning',
                message: '资料待复核',
                contract_relation_id: 'group-lease',
                display_name: 'GRP-LEASE',
              },
            ],
            total: 1,
          },
          isLoading: false,
          error: null,
        };
      }
      return { data: undefined, isLoading: false, error: null };
    });

    renderWithProviders(<ProjectDetailPage />, { route: '/project/project-1' });

    expect(screen.getByText('风险提示')).toBeInTheDocument();
    expect(screen.getByText('资料待复核')).toBeInTheDocument();
    expect(screen.getAllByText('GRP-LEASE').length).toBeGreaterThan(0);
    expect(screen.queryByText('暂无风险提示')).not.toBeInTheDocument();
  });

  it('starts creating a contract relation from the current project', () => {
    renderWithProviders(<ProjectDetailPage />, { route: '/project/project-1' });

    fireEvent.click(screen.getByRole('button', { name: '新建合同关系' }));

    expect(mockNavigate).toHaveBeenCalledWith('/contract-center/new?project_id=project-1');
  });

  it('starts creating an upstream lease contract from a project relation card', () => {
    renderWithProviders(<ProjectDetailPage />, { route: '/project/project-1' });

    fireEvent.click(screen.getByRole('button', { name: '新增上游承租合同' }));

    expect(mockNavigate).toHaveBeenCalledWith(
      '/contract-center/group-lease/contracts/new?project_id=project-1&role=UPSTREAM'
    );
  });

  it('starts creating an entrusted agency agreement from an agency relation card', () => {
    renderWithProviders(<ProjectDetailPage />, { route: '/project/project-1' });

    fireEvent.click(screen.getByRole('button', { name: '新增委托协议' }));

    expect(mockNavigate).toHaveBeenCalledWith(
      '/contract-center/group-agency/contracts/new?project_id=project-1&role=ENTRUSTED'
    );
  });
});
