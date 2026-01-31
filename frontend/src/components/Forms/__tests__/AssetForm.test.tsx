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
  return {
    ...actual,
    AssetBasicInfoSection: () => <div data-testid="basic-info-section" />,
    AssetAreaSection: () => <div data-testid="area-section" />,
    AssetStatusSection: () => <div data-testid="status-section" />,
    AssetReceptionSection: () => <div data-testid="reception-section" />,
    AssetDetailedSection: () => <div data-testid="detailed-section" />,
  };
});

// Mock Ant Design components
vi.mock('antd', () => {
  formMock.Item = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="form-item">{children}</div>
  );
  formMock.useForm = vi.fn(() => [formInstance]);

  const Collapse = Object.assign(
    ({ children }: { children?: React.ReactNode }) => (
      <div data-testid="collapse">{children}</div>
    ),
    {
      Panel: ({
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
      ),
    }
  );

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

  return {
    Card: ({ children }: { children?: React.ReactNode }) => <div data-testid="card">{children}</div>,
    Form: formMock,
    Input: () => <input data-testid="input" />,
    InputNumber: () => <input data-testid="input-number" />,
    Select: () => <select data-testid="select" />,
    DatePicker: () => <input data-testid="date-picker" />,
    Upload: () => <div data-testid="upload" />,
    Button: ({ children, onClick }: { children?: React.ReactNode; onClick?: () => void }) => (
      <button data-testid="button" onClick={onClick}>
        {children}
      </button>
    ),
    Row: ({ children }: { children?: React.ReactNode }) => <div data-testid="row">{children}</div>,
    Col: ({ children }: { children?: React.ReactNode }) => <div data-testid="col">{children}</div>,
    Space: ({ children }: { children?: React.ReactNode }) => (
      <div data-testid="space">{children}</div>
    ),
    Progress: ({ percent }: { percent?: number }) => (
      <div data-testid="progress" data-percent={percent} />
    ),
    Typography: {
      Title: ({ children }: { children?: React.ReactNode }) => (
        <div data-testid="title">{children}</div>
      ),
      Text: ({ children }: { children?: React.ReactNode }) => (
        <span data-testid="text">{children}</span>
      ),
      Paragraph: ({ children }: { children?: React.ReactNode }) => (
        <p data-testid="paragraph">{children}</p>
      ),
    },
    List: () => <div data-testid="list" />,
    Tag: () => <span data-testid="tag" />,
    Switch: () => <input data-testid="switch" />,
    Tooltip: ({ children }: { children?: React.ReactNode }) => (
      <div data-testid="tooltip">{children}</div>
    ),
    Divider: () => <div data-testid="divider" />,
    Collapse,
    Modal,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  UploadOutlined: () => null,
  SaveOutlined: () => null,
  ReloadOutlined: () => null,
  EyeOutlined: () => null,
  DeleteOutlined: () => null,
  InfoCircleOutlined: () => null,
}));

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
