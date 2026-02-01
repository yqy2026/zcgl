/**
 * AssetForm 组件测试
 * 测试资产表单的核心行为
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, waitFor } from '@testing-library/react';
import AssetForm from '../AssetForm';

const {
  useDictionariesMock,
  rentContractServiceMock,
  messageErrorMock,
  formInstance,
  formMock,
} = vi.hoisted(() => {
  const useDictionariesMock = vi.fn(() => ({}));
  const rentContractServiceMock = {
    getAssetContracts: vi.fn().mockResolvedValue([]),
  };
  const messageErrorMock = vi.fn();
  const formInstance = {
    getFieldsValue: vi.fn(() => ({})),
    setFieldsValue: vi.fn(),
    validateFields: vi.fn(() => Promise.resolve({})),
    resetFields: vi.fn(),
    getFieldValue: vi.fn(() => undefined),
    setFieldValue: vi.fn(),
  };

  const formMock = vi.fn(
    ({
      children,
      onFinish,
    }: {
      children?: React.ReactNode;
      onFinish?: (values: Record<string, unknown>) => void | Promise<void>;
    }) => (
      <form
        data-testid="form"
        onSubmit={event => {
          event.preventDefault();
          onFinish?.({});
        }}
      >
        {children}
      </form>
    )
  );
  (formMock as React.FC).displayName = 'MockForm';

  return {
    useDictionariesMock,
    rentContractServiceMock,
    messageErrorMock,
    formInstance,
    formMock,
  };
});

// Mock dependencies
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('@/services/assetService', () => ({
  assetService: {
    uploadAssetAttachments: vi.fn(),
  },
}));

vi.mock('../../../services/rentContractService', () => ({
  rentContractService: rentContractServiceMock,
}));

vi.mock('../../../hooks/useDictionary', () => ({
  useDictionaries: (...args: unknown[]) => useDictionariesMock(...args),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    error: (...args: unknown[]) => messageErrorMock(...args),
    info: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    loading: vi.fn(),
  },
}));

vi.mock('../Asset', async () => {
  const actual = await vi.importActual('../Asset');
  const AssetBasicInfoSection = () => <div data-testid="basic-info-section" />;
  const AssetAreaSection = () => <div data-testid="area-section" />;
  const AssetStatusSection = () => <div data-testid="status-section" />;
  const AssetReceptionSection = () => <div data-testid="reception-section" />;
  const AssetDetailedSection = () => <div data-testid="detailed-section" />;

  AssetBasicInfoSection.displayName = 'MockAssetBasicInfoSection';
  AssetAreaSection.displayName = 'MockAssetAreaSection';
  AssetStatusSection.displayName = 'MockAssetStatusSection';
  AssetReceptionSection.displayName = 'MockAssetReceptionSection';
  AssetDetailedSection.displayName = 'MockAssetDetailedSection';

  return {
    ...actual,
    AssetBasicInfoSection,
    AssetAreaSection,
    AssetStatusSection,
    AssetReceptionSection,
    AssetDetailedSection,
  };
});

// Mock Ant Design components
vi.mock('antd', () => {
  const FormItem = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="form-item">{children}</div>
  );
  FormItem.displayName = 'MockFormItem';
  formMock.Item = FormItem;
  formMock.useForm = vi.fn(() => [formInstance]);

  const CollapsePanel = ({
    children,
    header,
  }: {
    children?: React.ReactNode;
    header?: React.ReactNode;
  }) => (
    <div data-testid="collapse-panel">
      {header && <div data-testid="collapse-header">{header}</div>}
      {children}
    </div>
  );
  CollapsePanel.displayName = 'MockCollapsePanel';

  const Collapse = Object.assign(
    ({ children }: { children?: React.ReactNode }) => (
      <div data-testid="collapse">{children}</div>
    ),
    { Panel: CollapsePanel }
  );
  Collapse.displayName = 'MockCollapse';

  const Modal = ({
    children,
    open,
    title,
    footer,
  }: {
    children?: React.ReactNode;
    open?: boolean;
    title?: React.ReactNode;
    footer?: React.ReactNode;
  }) => (
    <div data-testid="modal" data-open={open}>
      {title && <div data-testid="modal-title">{title}</div>}
      {children}
      {footer}
    </div>
  );
  Modal.displayName = 'MockModal';

  const Card = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="card">{children}</div>
  );
  Card.displayName = 'MockCard';

  const Input = () => <input data-testid="input" />;
  Input.displayName = 'MockInput';

  const InputNumber = () => <input data-testid="input-number" />;
  InputNumber.displayName = 'MockInputNumber';

  const Select = () => <select data-testid="select" />;
  Select.displayName = 'MockSelect';

  const DatePicker = () => <input data-testid="date-picker" />;
  DatePicker.displayName = 'MockDatePicker';

  const Upload = () => <div data-testid="upload" />;
  Upload.displayName = 'MockUpload';

  const Button = ({ children, onClick }: { children?: React.ReactNode; onClick?: () => void }) => (
    <button data-testid="button" onClick={onClick}>
      {children}
    </button>
  );
  Button.displayName = 'MockButton';

  const Row = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="row">{children}</div>
  );
  Row.displayName = 'MockRow';

  const Col = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="col">{children}</div>
  );
  Col.displayName = 'MockCol';

  const Space = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  );
  Space.displayName = 'MockSpace';

  const Progress = ({ percent }: { percent?: number }) => (
    <div data-testid="progress" data-percent={percent} />
  );
  Progress.displayName = 'MockProgress';

  const TypographyTitle = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="title">{children}</div>
  );
  TypographyTitle.displayName = 'MockTypographyTitle';

  const TypographyText = ({ children }: { children?: React.ReactNode }) => (
    <span data-testid="text">{children}</span>
  );
  TypographyText.displayName = 'MockTypographyText';

  const TypographyParagraph = ({ children }: { children?: React.ReactNode }) => (
    <p data-testid="paragraph">{children}</p>
  );
  TypographyParagraph.displayName = 'MockTypographyParagraph';

  const List = () => <div data-testid="list" />;
  List.displayName = 'MockList';

  const Tag = () => <span data-testid="tag" />;
  Tag.displayName = 'MockTag';

  const Switch = () => <input data-testid="switch" />;
  Switch.displayName = 'MockSwitch';

  const Tooltip = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="tooltip">{children}</div>
  );
  Tooltip.displayName = 'MockTooltip';

  const Divider = () => <div data-testid="divider" />;
  Divider.displayName = 'MockDivider';

  return {
    Card,
    Form: formMock,
    Input,
    InputNumber,
    Select,
    DatePicker,
    Upload,
    Button,
    Row,
    Col,
    Space,
    Progress,
    Typography: {
      Title: TypographyTitle,
      Text: TypographyText,
      Paragraph: TypographyParagraph,
    },
    List,
    Tag,
    Switch,
    Tooltip,
    Divider,
    Collapse,
    Modal,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => {
  const UploadOutlined = () => null;
  const SaveOutlined = () => null;
  const ReloadOutlined = () => null;
  const EyeOutlined = () => null;
  const DeleteOutlined = () => null;
  const InfoCircleOutlined = () => null;

  UploadOutlined.displayName = 'UploadOutlined';
  SaveOutlined.displayName = 'SaveOutlined';
  ReloadOutlined.displayName = 'ReloadOutlined';
  EyeOutlined.displayName = 'EyeOutlined';
  DeleteOutlined.displayName = 'DeleteOutlined';
  InfoCircleOutlined.displayName = 'InfoCircleOutlined';

  return {
    UploadOutlined,
    SaveOutlined,
    ReloadOutlined,
    EyeOutlined,
    DeleteOutlined,
    InfoCircleOutlined,
  };
});

describe('AssetForm - 核心行为测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useDictionariesMock.mockClear();
    rentContractServiceMock.getAssetContracts.mockClear();
    formInstance.setFieldsValue.mockClear();
    messageErrorMock.mockClear();
  });

  it('应调用useDictionaries加载字典', () => {
    render(<AssetForm />);

    expect(useDictionariesMock).toHaveBeenCalledWith([
      'property_nature',
      'usage_status',
      'ownership_status',
      'ownership_category',
      'business_category',
      'certificated_usage',
      'actual_usage',
      'tenant_type',
      'business_model',
    ]);
  });

  it('初始数据应设置表单并触发合同加载', async () => {
    render(
      <AssetForm
        initialData={{
          id: 'asset-123',
          property_name: '测试物业',
          contract_start_date: '2024-01-01',
          operation_agreement_start_date: '2024-02-01',
        }}
      />
    );

    await waitFor(() => {
      expect(formInstance.setFieldsValue).toHaveBeenCalled();
      expect(rentContractServiceMock.getAssetContracts).toHaveBeenCalledWith('asset-123');
    });
  });

  it('提交时必填字段齐全应调用onSubmit', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<AssetForm onSubmit={onSubmit} />);

    const onFinish = formMock.mock.calls[0][0].onFinish as (
      values: Record<string, unknown>
    ) => Promise<void>;

    await onFinish({
      property_name: '物业A',
      ownership_entity: '权属方A',
      address: '地址A',
      ownership_status: '已确权',
      property_nature: '经营性',
      usage_status: '出租',
    });

    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it('提交时缺少必填字段应提示错误', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<AssetForm onSubmit={onSubmit} />);

    const onFinish = formMock.mock.calls[0][0].onFinish as (
      values: Record<string, unknown>
    ) => Promise<void>;

    await onFinish({
      property_name: '物业A',
    });

    expect(onSubmit).not.toHaveBeenCalled();
    expect(messageErrorMock).toHaveBeenCalledWith('表单数据不完整，请检查必填字段');
  });
});
