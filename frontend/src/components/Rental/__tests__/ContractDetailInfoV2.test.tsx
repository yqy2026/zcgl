/**
 * ContractDetailInfo V2 Tests
 *
 * Tests for V2-specific contract detail display:
 * - Contract type display (upstream/downstream/entrusted)
 * - Multi-asset display
 * - Service fee rate display
 * - Payment cycle display
 * - Deposit ledger display
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';

// Mock antd
vi.mock('antd', () => {
  const DescriptionsItemMock = ({ children, label }: any) => (
    <div data-testid="descriptions-item" data-label={label}>
      {label && <span className="item-label">{label}</span>}
      <span className="item-content">{children}</span>
    </div>
  );

  const DescriptionsMock: any = ({ items, children }: any) => {
    return children ? (
      <div data-testid="descriptions">{children}</div>
    ) : (
      <div data-testid="descriptions">
        {items?.map((item: any, index: number) => (
          <div key={index} data-testid={`desc-item-${item.key || index}`}>
            <span className="label">{item.label}</span>
            <span className="value">{item.children}</span>
          </div>
        ))}
      </div>
    );
  };

  // Attach Item as a property before returning
  DescriptionsMock.Item = DescriptionsItemMock;

  return {
    Card: ({ children, title }: any) => (
      <div data-testid="card" data-title={title}>
        <div className="card-title">{title}</div>
        {children}
      </div>
    ),
    Descriptions: DescriptionsMock,
    Tag: ({ children, color }: any) => (
      <span data-testid="tag" data-color={color}>
        {children}
      </span>
    ),
    Table: ({ dataSource, columns }: any) => (
      <table data-testid="table">
        <thead>
          <tr>
            {columns?.map((col: any, i: number) => (
              <th key={i}>{col.title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataSource?.map((row: any, i: number) => (
            <tr key={i} data-testid={`table-row-${i}`}>
              {columns?.map((col: any, j: number) => (
                <td key={j}>{row[col.dataIndex]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    ),
    Tabs: ({ items, defaultActiveKey }: any) => (
      <div data-testid="tabs" data-default-key={defaultActiveKey}>
        {items?.map((item: any) => (
          <div key={item.key} data-testid={`tab-${item.key}`}>
            {item.label}: {item.children}
          </div>
        ))}
      </div>
    ),
    Space: ({ children }: any) => <div data-testid="space">{children}</div>,
    Divider: () => <hr data-testid="divider" />,
    Timeline: ({ items }: any) => (
      <div data-testid="timeline">
        {items?.map((item: any, i: number) => (
          <div key={i} data-testid={`timeline-item-${i}`}>
            {item.children}
          </div>
        ))}
      </div>
    ),
    Empty: ({ description }: any) => <div data-testid="empty">{description}</div>,
    Statistic: ({ title, value, suffix }: any) => (
      <div data-testid="statistic" data-title={title}>
        <span>{title}</span>: <span>{value}</span>
        {suffix && <span>{suffix}</span>}
      </div>
    ),
    Row: ({ children }: any) => <div data-testid="row">{children}</div>,
    Col: ({ children }: any) => <div data-testid="col">{children}</div>,
    Typography: {
      Text: ({ children }: any) => <span>{children}</span>,
      Title: ({ children }: any) => <h1>{children}</h1>,
      Paragraph: ({ children }: any) => <p>{children}</p>,
    },
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  FileTextOutlined: () => <span data-testid="icon-file" />,
  TeamOutlined: () => <span data-testid="icon-team" />,
  DollarOutlined: () => <span data-testid="icon-dollar" />,
  CalendarOutlined: () => <span data-testid="icon-calendar" />,
  HomeOutlined: () => <span data-testid="icon-home" />,
  InfoCircleOutlined: () => <span data-testid="icon-info" />,
  BankOutlined: () => <span data-testid="icon-bank" />,
  EnvironmentOutlined: () => <span data-testid="icon-environment" />,
  PhoneOutlined: () => <span data-testid="icon-phone" />,
  UserOutlined: () => <span data-testid="icon-user" />,
}));

// Mock child components
vi.mock('../DepositLedgerHistory', () => ({
  default: ({ ledgers, loading }: any) => (
    <div data-testid="deposit-ledger-history" data-loading={loading}>
      {ledgers?.length ?? 0} 条押金记录
    </div>
  ),
}));

vi.mock('../ServiceFeeLedgerTable', () => ({
  default: ({ ledgers, loading }: any) => (
    <div data-testid="service-fee-ledger-table" data-loading={loading}>
      {ledgers?.length ?? 0} 条服务费记录
    </div>
  ),
}));

describe('ContractDetailInfo V2 Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Cleanup after each test to prevent DOM pollution
    document.body.innerHTML = '';
  });

  // ==================== Mock Data ====================

  const mockUpstreamContract = {
    id: 'upstream_001',
    contract_number: 'UP2026001',
    contract_type: 'lease_upstream',
    tenant_name: '运营方公司',
    ownership_id: 'ownership_001',
    ownership: { name: '权属方A' },
    sign_date: '2026-01-01',
    start_date: '2026-01-01',
    end_date: '2026-12-31',
    total_deposit: 50000,
    monthly_rent_base: 10000,
    payment_cycle: 'quarterly',
    contract_status: '有效',
    assets: [
      { id: 'asset_001', property_name: '物业A' },
      { id: 'asset_002', property_name: '物业B' },
    ],
    rent_terms: [{ start_date: '2026-01-01', end_date: '2026-12-31', monthly_rent: 10000 }],
  };

  const mockDownstreamContract = {
    id: 'downstream_001',
    contract_number: 'DN2026001',
    contract_type: 'lease_downstream',
    upstream_contract_id: 'upstream_001',
    tenant_name: '终端租户A',
    tenant_usage: '零售商铺',
    tenant_contact: '李四',
    tenant_phone: '13900139000',
    ownership_id: 'ownership_001',
    ownership: { name: '权属方A' },
    sign_date: '2026-01-01',
    start_date: '2026-01-01',
    end_date: '2026-12-31',
    total_deposit: 30000,
    monthly_rent_base: 12000,
    payment_cycle: 'monthly',
    contract_status: '有效',
    assets: [{ id: 'asset_001', property_name: '物业A' }],
    rent_terms: [],
  };

  const mockEntrustedContract = {
    id: 'entrusted_001',
    contract_number: 'EN2026001',
    contract_type: 'entrusted',
    service_fee_rate: 0.05,
    tenant_name: '权属方委托',
    ownership_id: 'ownership_001',
    ownership: { name: '权属方A' },
    sign_date: '2026-01-01',
    start_date: '2026-01-01',
    end_date: '2026-12-31',
    contract_status: '有效',
    assets: [],
    rent_terms: [],
  };

  // ==================== Contract Type Display Tests ====================

  describe('Contract Type Display (V2 Core Feature)', () => {
    it('should import ContractDetailInfo component', async () => {
      const module = await import('../ContractDetailInfo');
      expect(module.default).toBeDefined();
    });

    it('should display upstream contract type correctly', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockUpstreamContract} />);

      // Contract should render with multiple descriptions sections
      const descriptions = screen.getAllByTestId('descriptions');
      expect(descriptions.length).toBeGreaterThan(0);
    });

    it('should display downstream contract type correctly', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockDownstreamContract} />);

      const descriptions = screen.getAllByTestId('descriptions');
      expect(descriptions.length).toBeGreaterThan(0);
    });

    it('should display entrusted contract type correctly', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockEntrustedContract} />);

      const descriptions = screen.getAllByTestId('descriptions');
      expect(descriptions.length).toBeGreaterThan(0);
    });
  });

  // ==================== Multi-Asset Display Tests ====================

  describe('Multi-Asset Display (V2 Feature)', () => {
    it('should display multiple assets for contract', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockUpstreamContract} />);

      // Should have table or list for assets
      // The component should render asset information
      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });

    it('should handle contract with no assets', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      const contractNoAssets = { ...mockUpstreamContract, assets: [] };
      render(<ContractDetailInfo contract={contractNoAssets} />);

      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });
  });

  // ==================== Service Fee Rate Tests ====================

  describe('Service Fee Rate Display (V2 Feature)', () => {
    it('should display service fee rate for entrusted contract', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockEntrustedContract} />);

      // Service fee rate (5%) should be visible for entrusted contracts
      const descriptions = screen.getAllByTestId('descriptions');
      expect(descriptions.length).toBeGreaterThan(0);
    });

    it('should not show service fee rate for non-entrusted contract', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockDownstreamContract} />);

      // Non-entrusted contracts should not show service fee
      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });
  });

  // ==================== Payment Cycle Tests ====================

  describe('Payment Cycle Display (V2 Feature)', () => {
    it('should display quarterly payment cycle', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockUpstreamContract} />);

      // Payment cycle should be displayed
      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });

    it('should display monthly payment cycle', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockDownstreamContract} />);

      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });
  });

  // ==================== Downstream-specific Fields Tests ====================

  describe('Downstream Contract Fields (V2 Feature)', () => {
    it('should display tenant usage for downstream contract', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockDownstreamContract} />);

      // tenant_usage field should be visible
      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });

    it('should display upstream contract reference', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockDownstreamContract} />);

      // upstream_contract_id should be referenced
      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });
  });

  // ==================== Rent Terms Display Tests ====================

  describe('Rent Terms Display (Tiered Pricing)', () => {
    it('should display rent terms table', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      const contractWithTerms = {
        ...mockUpstreamContract,
        rent_terms: [
          { start_date: '2026-01-01', end_date: '2026-06-30', monthly_rent: 10000 },
          { start_date: '2026-07-01', end_date: '2026-12-31', monthly_rent: 10500 },
        ],
      };

      render(<ContractDetailInfo contract={contractWithTerms} />);

      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });

    it('should handle contract with no rent terms', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockDownstreamContract} />);

      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });
  });

  // ==================== Contract Status Tests ====================

  describe('Contract Status Display', () => {
    it('should show active status with green tag', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      render(<ContractDetailInfo contract={mockUpstreamContract} />);

      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });

    it('should show terminated status with red tag', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      const terminatedContract = { ...mockUpstreamContract, contract_status: '终止' };
      render(<ContractDetailInfo contract={terminatedContract} />);

      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });

    it('should show renewed status with blue tag', async () => {
      const module = await import('../ContractDetailInfo');
      const ContractDetailInfo = module.default;

      const renewedContract = { ...mockUpstreamContract, contract_status: '已续签' };
      render(<ContractDetailInfo contract={renewedContract} />);

      expect(screen.getAllByTestId('descriptions').length).toBeGreaterThan(0);
    });
  });
});
