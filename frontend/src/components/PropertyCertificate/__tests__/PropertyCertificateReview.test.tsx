/**
 * PropertyCertificateReview 组件测试
 * 测试产权证审核组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import { PropertyCertificateReview } from '../PropertyCertificateReview';
import type {
  CertificateExtractionResult,
  CertificateType,
  AssetMatch,
} from '@/types/propertyCertificate';

const { formInstance, formMock } = vi.hoisted(() => {
  const formInstance = {
    validateFields: vi.fn(),
    setFieldsValue: vi.fn(),
  };

  const formMock = vi.fn(
    ({
      children,
      onFinish,
      layout,
    }: {
      children?: React.ReactNode;
      onFinish?: () => void | Promise<void>;
      layout?: string;
    }) => (
      <form
        data-testid="form"
        data-layout={layout}
        onSubmit={event => {
          event.preventDefault();
          onFinish?.();
        }}
      >
        {children}
      </form>
    )
  );
  (formMock as React.FC).displayName = 'MockForm';

  return { formInstance, formMock };
});

interface FormItemMockProps {
  children?: React.ReactNode;
  label?: React.ReactNode;
  name?: string;
  rules?: unknown;
}

interface CollapseMockProps {
  items?: Array<{ key: string; label: React.ReactNode; children: React.ReactNode }>;
  style?: React.CSSProperties;
}

interface ListMockProps<T> {
  dataSource?: T[];
  renderItem?: (item: T) => React.ReactNode;
}

interface ListItemMockProps {
  children?: React.ReactNode;
  onClick?: () => void;
  style?: React.CSSProperties;
}

interface ListItemMetaMockProps {
  title?: React.ReactNode;
  description?: React.ReactNode;
}

// Mock Ant Design components
vi.mock('antd', () => {
  const FormItem = ({ children, label, name }: FormItemMockProps) => (
    <div data-testid="form-item" data-label={label} data-name={name}>
      {children}
    </div>
  );
  FormItem.displayName = 'MockFormItem';
  formMock.Item = FormItem;
  formMock.useForm = vi.fn(() => [formInstance]);

  const ListItem = ({ children, onClick, style }: ListItemMockProps) => (
    <div
      data-testid="list-item"
      data-style={JSON.stringify(style)}
      onClick={onClick}
    >
      {children}
    </div>
  );
  ListItem.displayName = 'MockListItem';

  const ListItemMeta = ({ title, description }: ListItemMetaMockProps) => (
    <div data-testid="list-item-meta">
      <div>{title}</div>
      <div>{description}</div>
    </div>
  );
  ListItemMeta.displayName = 'MockListItemMeta';
  ListItem.Meta = ListItemMeta;

  const List = ({ dataSource, renderItem }: ListMockProps<unknown>) => (
    <div data-testid="list">
      {(dataSource ?? []).map((item, index) => (
        <div key={index}>{renderItem?.(item)}</div>
      ))}
    </div>
  );
  List.displayName = 'MockList';
  (List as unknown as { Item?: typeof ListItem }).Item = ListItem;

  const Card = ({
    children,
    title,
    extra,
  }: {
    children?: React.ReactNode;
    title?: React.ReactNode;
    extra?: React.ReactNode;
  }) => (
    <div data-testid="card">
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      {children}
    </div>
  );
  Card.displayName = 'MockCard';

  const Input = ({ suffix }: { suffix?: React.ReactNode }) => (
    <input data-testid="input" data-suffix={suffix} />
  );
  Input.displayName = 'MockInput';

  const SelectOption = ({ children, value }: { children?: React.ReactNode; value?: string }) => (
    <option value={value}>{children}</option>
  );
  SelectOption.displayName = 'MockSelectOption';

  const Select = Object.assign(
    ({ children, placeholder }: { children?: React.ReactNode; placeholder?: string }) => (
      <select data-testid="select" data-placeholder={placeholder}>
        {children}
      </select>
    ),
    {
      Option: SelectOption,
    }
  );
  Select.displayName = 'MockSelect';

  const DatePicker = ({ style }: { style?: React.CSSProperties }) => (
    <input data-testid="date-picker" data-style={JSON.stringify(style)} />
  );
  DatePicker.displayName = 'MockDatePicker';

  const Button = ({
    children,
    htmlType,
    onClick,
    loading,
  }: {
    children?: React.ReactNode;
    htmlType?: string;
    onClick?: () => void;
    loading?: boolean;
  }) => (
    <button
      data-testid="button"
      type={htmlType}
      data-loading={loading}
      onClick={onClick}
    >
      {children}
    </button>
  );
  Button.displayName = 'MockButton';

  const Space = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  );
  Space.displayName = 'MockSpace';

  const Tag = ({ children, color }: { children?: React.ReactNode; color?: string }) => (
    <span data-testid="tag" data-color={color}>
      {children}
    </span>
  );
  Tag.displayName = 'MockTag';

  const Collapse = ({ items, style }: CollapseMockProps) => (
    <div data-testid="collapse" data-style={JSON.stringify(style)}>
      {items?.map(item => (
        <div key={item.key} data-testid={`collapse-item-${item.key}`}>
          <div>{item.label}</div>
          <div>{item.children}</div>
        </div>
      ))}
    </div>
  );
  Collapse.displayName = 'MockCollapse';

  const TypographyText = ({ children, type }: { children?: React.ReactNode; type?: string }) => (
    <span data-testid="text" data-type={type}>
      {children}
    </span>
  );
  TypographyText.displayName = 'MockTypographyText';

  return {
    Card,
    Form: formMock,
    Input,
    Select,
    DatePicker,
    Button,
    Space,
    Tag,
    Collapse,
    List,
    Typography: {
      Text: TypographyText,
    },
    ListItem,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => {
  const SaveOutlined = () => <span data-testid="save-icon" />;
  SaveOutlined.displayName = 'SaveOutlined';
  return { SaveOutlined };
});

const mockAssetMatches: AssetMatch[] = [
  {
    asset_id: 'asset-1',
    name: '资产一号',
    address: '地址1',
    confidence: 0.88,
    match_reasons: [],
  },
];

const createExtractionResult = (
  overrides: Partial<CertificateExtractionResult> = {}
): CertificateExtractionResult => ({
  session_id: 'session-123',
  certificate_type: 'real_estate' as CertificateType,
  extracted_data: {
    certificate_number: 'CERT-001',
    property_address: '测试地址',
  },
  confidence_score: 0.9,
  asset_matches: [],
  validation_errors: [],
  warnings: [],
  ...overrides,
});

describe('PropertyCertificateReview - 组件导入测试', () => {
  it('应该能够导入组件', () => {
    expect(PropertyCertificateReview).toBeDefined();
  });
});

describe('PropertyCertificateReview - 渲染与提交测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    formInstance.validateFields.mockResolvedValue({
      certificate_number: 'CERT-001',
      property_address: '测试地址',
    });
  });

  it('应显示置信度标签与验证错误/警告', () => {
    renderWithProviders(
      <PropertyCertificateReview
        extractionResult={createExtractionResult({
          confidence_score: 0.92,
          validation_errors: ['错误1'],
          warnings: ['警告1'],
        })}
        onConfirm={vi.fn()}
      />
    );

    expect(screen.getByTestId('tag')).toHaveAttribute('data-color', 'success');
    expect(screen.getByText('置信度: 92.0%')).toBeInTheDocument();
    expect(screen.getByText('验证错误 (1)')).toBeInTheDocument();
    expect(screen.getByText('错误1')).toBeInTheDocument();
    expect(screen.getByText('警告 (1)')).toBeInTheDocument();
    expect(screen.getByText('警告1')).toBeInTheDocument();
  });

  it('未选择资产时应创建新资产', async () => {
    const onConfirm = vi.fn();
    renderWithProviders(
      <PropertyCertificateReview
        extractionResult={createExtractionResult()}
        onConfirm={onConfirm}
      />
    );

    fireEvent.submit(screen.getByTestId('form'));

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith(
        expect.objectContaining({
          session_id: 'session-123',
          asset_ids: [],
          asset_link_id: null,
          should_create_new_asset: true,
        })
      );
    });
  });

  it('选择匹配资产后应关联资产', async () => {
    const onConfirm = vi.fn();
    renderWithProviders(
      <PropertyCertificateReview
        extractionResult={createExtractionResult({ asset_matches: mockAssetMatches })}
        onConfirm={onConfirm}
      />
    );

    fireEvent.click(screen.getByTestId('list-item'));
    fireEvent.submit(screen.getByTestId('form'));

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith(
        expect.objectContaining({
          asset_ids: ['asset-1'],
          asset_link_id: 'asset-1',
          should_create_new_asset: false,
        })
      );
    });
  });
});
