import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import OwnershipDetailPage from '../OwnershipDetailPage';
import { renderWithProviders } from '@/test/utils/test-helpers';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'owner-1' }),
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnership: vi.fn(),
  },
}));

vi.mock('@/services/assetService', () => ({
  assetService: {
    getAssets: vi.fn(),
  },
}));

import { ownershipService } from '@/services/ownershipService';
import { assetService } from '@/services/assetService';

const formatStderrWrites = (calls: unknown[][]) => calls.map(call => String(call[0] ?? '')).join(' ');

vi.mock('../OwnershipDetailPage.module.css', () => ({
  default: new Proxy(
    {},
    {
      get: (_target, property) => String(property),
    }
  ),
}));

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');

  const Card = ({
    children,
    title,
  }: {
    children?: React.ReactNode;
    title?: React.ReactNode;
  }) => (
    <div data-testid="card">
      {title != null && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  );

  const Alert = ({
    title,
    description,
  }: {
    title?: React.ReactNode;
    description?: React.ReactNode;
  }) => (
    <div data-testid="alert">
      {title}
      {description}
    </div>
  );

  const Tabs = ({ items }: { items?: Array<{ label?: React.ReactNode; children?: React.ReactNode }> }) => (
    <div data-testid="tabs">
      {(items ?? []).map((item, index) => (
        <div key={index}>
          <div>{item.label}</div>
          <div>{item.children}</div>
        </div>
      ))}
    </div>
  );

  const Statistic = ({
    title,
    value,
    suffix,
  }: {
    title?: React.ReactNode;
    value?: React.ReactNode;
    suffix?: React.ReactNode;
  }) => (
    <div data-testid="statistic">
      <span>{title}</span>
      <span>
        {value}
        {suffix}
      </span>
    </div>
  );

  const Descriptions = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="descriptions">{children}</div>
  );
  const DescriptionsItem = ({
    label,
    children,
  }: {
    label?: React.ReactNode;
    children?: React.ReactNode;
  }) => (
    <div data-testid="descriptions-item">
      <span>{label}</span>
      <span>{children}</span>
    </div>
  );
  Descriptions.Item = DescriptionsItem;

  const Table = () => <div data-testid="table" />;
  const Badge = ({ text }: { text?: React.ReactNode }) => <span>{text}</span>;
  const Tag = ({ children }: { children?: React.ReactNode }) => <span>{children}</span>;
  const Button = ({
    children,
    onClick,
  }: {
    children?: React.ReactNode;
    onClick?: () => void;
  }) => <button onClick={onClick}>{children}</button>;
  const Space = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  const Row = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  const Col = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  const Popconfirm = ({ children }: { children?: React.ReactNode }) => <>{children}</>;
  const Modal = ({ children }: { children?: React.ReactNode }) => <>{children}</>;
  const Select = ({ children }: { children?: React.ReactNode }) => <select>{children}</select>;
  Select.Option = ({
    children,
    value,
  }: {
    children?: React.ReactNode;
    value?: string;
  }) => <option value={value}>{children}</option>;
  const Input = ({ value }: { value?: string }) => <input value={value} readOnly />;
  Input.TextArea = ({ value }: { value?: string }) => <textarea value={value} readOnly />;
  const DatePicker = () => <input readOnly />;
  DatePicker.RangePicker = () => <input readOnly />;
  const Form = ({ children }: { children?: React.ReactNode }) => <form>{children}</form>;
  Form.Item = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  Form.useForm = () => [{ setFieldsValue: vi.fn(), validateFields: vi.fn() }];

  return {
    ...actual,
    Card,
    Alert,
    Tabs,
    Statistic,
    Descriptions,
    Table,
    Badge,
    Tag,
    Button,
    Space,
    Row,
    Col,
    Popconfirm,
    Modal,
    Select,
    Input,
    DatePicker,
    Form,
  };
});

const readOwnershipDetailSource = (): string => {
  return readFileSync(
    resolve(process.cwd(), 'src/pages/Ownership/OwnershipDetailPage.tsx'),
    'utf8'
  );
};

describe('OwnershipDetailPage legacy contract retirement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ownershipService.getOwnership).mockResolvedValue({
      id: 'owner-1',
      name: '测试权属方',
      short_name: '测试简称',
      is_active: true,
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-02T00:00:00Z',
    });
    vi.mocked(assetService.getAssets).mockResolvedValue({
      items: [
        {
          id: 'asset-1',
          asset_name: '测试物业',
          usage_status: '已出租',
          rentable_area: 100,
          project_name: '测试项目',
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    });
  });

  it('stops importing legacy rentContractService', () => {
    const source = readOwnershipDetailSource();

    expect(source).not.toContain("from '@/services/rentContractService'");
    expect(source).toContain('旧租赁合同与财务汇总入口已退休');
  });

  it('renders explicit migration alerts for legacy contract and finance sections', async () => {
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      renderWithProviders(<OwnershipDetailPage />, { route: '/ownership/owner-1' });

      expect(
        await screen.findAllByText(/旧租赁合同与财务汇总入口已退休/)
      ).toHaveLength(2);
      expect(screen.getByText('关联合同（迁移中）')).toBeInTheDocument();
      expect(screen.getByText(/财务汇总迁移中/)).toBeInTheDocument();
      expect(screen.getByText(/关联资产 \(1\)/)).toBeInTheDocument();
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain(
        'Could not parse CSS stylesheet'
      );
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });
});
