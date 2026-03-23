import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { fireEvent, render, screen, waitFor } from '@/test/utils/test-helpers';

import AssetBatchActions from '../AssetBatchActions';

const mockInvalidateQueries = vi.fn();
const mockValidateFields = vi.fn();
const mockResetFields = vi.fn();
const mockSuccess = vi.fn();
const mockError = vi.fn();
const deleteAssetsMock = vi.fn();
const updateAssetMock = vi.fn();
const exportExcelMock = vi.fn();
const downloadExportFileMock = vi.fn();

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: (...args: unknown[]) => mockSuccess(...args),
    error: (...args: unknown[]) => mockError(...args),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('@/services/assetService', () => ({
  assetService: {
    deleteAssets: (...args: unknown[]) => deleteAssetsMock(...args),
    updateAsset: (...args: unknown[]) => updateAssetMock(...args),
  },
}));

vi.mock('@/services/excelService', () => ({
  excelService: {
    exportExcel: (...args: unknown[]) => exportExcelMock(...args),
    downloadExportFile: (...args: unknown[]) => downloadExportFileMock(...args),
  },
}));

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    invalidateQueries: mockInvalidateQueries,
  }),
  useMutation: ({ mutationFn, onSuccess, onError }: Record<string, unknown>) => ({
    mutate: async (payload: unknown) => {
      try {
        const result = await (mutationFn as (value: unknown) => Promise<unknown>)(payload);
        await (onSuccess as ((value: unknown) => Promise<void> | void) | undefined)?.(result);
      } catch (error) {
        await (onError as ((value: unknown) => Promise<void> | void) | undefined)?.(error);
      }
    },
    isPending: false,
  }),
}));

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');

  const Button = ({ children, onClick }: { children?: React.ReactNode; onClick?: () => void }) => (
    <button onClick={onClick}>{children}</button>
  );

  const Modal = ({
    open,
    children,
    onOk,
    onCancel,
  }: {
    open?: boolean;
    children?: React.ReactNode;
    onOk?: () => void;
    onCancel?: () => void;
  }) =>
    open ? (
      <div data-testid="modal">
        {children}
        <button data-testid="modal-ok" onClick={onOk}>
          ok
        </button>
        <button data-testid="modal-cancel" onClick={onCancel}>
          cancel
        </button>
      </div>
    ) : null;

  const Popconfirm = ({
    children,
    onConfirm,
  }: {
    children?: React.ReactNode;
    onConfirm?: () => void;
  }) => {
    if (!React.isValidElement(children)) {
      return null;
    }

    return React.cloneElement(children, {
      onClick: onConfirm,
    });
  };

  const Input = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  const TextArea = ({ children }: { children?: React.ReactNode }) => (
    <textarea>{children}</textarea>
  );
  const Select = ({ children }: { children?: React.ReactNode }) => <select>{children}</select>;
  const Option = ({
    children,
    value,
  }: {
    children?: React.ReactNode;
    value?: string | boolean;
  }) => <option value={String(value)}>{children}</option>;
  const Form = ({ children }: { children?: React.ReactNode }) => <form>{children}</form>;

  return {
    ...actual,
    Card: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
    Button,
    Space: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
    Dropdown: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
    Modal,
    Form: Object.assign(Form, {
      useForm: () => [
        {
          validateFields: mockValidateFields,
          resetFields: mockResetFields,
        },
      ],
      Item: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
    }),
    Select: Object.assign(Select, { Option }),
    Input: Object.assign(Input, { TextArea }),
    Popconfirm,
    Typography: {
      Text: ({ children }: { children?: React.ReactNode }) => <span>{children}</span>,
    },
    Alert: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  };
});

vi.mock('@ant-design/icons', () => ({
  DeleteOutlined: () => null,
  EditOutlined: () => null,
  ExportOutlined: () => null,
  DownOutlined: () => null,
  TagOutlined: () => null,
}));

describe('AssetBatchActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockValidateFields.mockResolvedValue({ usage_status: '出租' });
    deleteAssetsMock.mockResolvedValue({ success: true, deleted: 2 });
    updateAssetMock.mockResolvedValue({ success: true });
    exportExcelMock.mockResolvedValue({ file_name: 'assets.xlsx' });
  });

  it('批量删除成功后应失效资产列表与分析查询前缀', async () => {
    render(
      <AssetBatchActions
        selectedAssets={[]}
        selectedRowKeys={['asset-1', 'asset-2']}
        onClearSelection={vi.fn()}
        onRefresh={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '批量删除' }));

    await waitFor(() => {
      expect(deleteAssetsMock).toHaveBeenCalledWith(['asset-1', 'asset-2']);
    });

    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['assets-list'] });
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['analytics'] });
  });

  it('批量编辑成功后应失效资产列表与分析查询前缀', async () => {
    render(
      <AssetBatchActions
        selectedAssets={[]}
        selectedRowKeys={['asset-1', 'asset-2']}
        onClearSelection={vi.fn()}
        onRefresh={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '批量编辑' }));
    fireEvent.click(screen.getByTestId('modal-ok'));

    await waitFor(() => {
      expect(updateAssetMock).toHaveBeenCalledWith('asset-1', { usage_status: '出租' });
    });

    expect(updateAssetMock).toHaveBeenCalledWith('asset-2', { usage_status: '出租' });
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['assets-list'] });
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ['analytics'] });
    expect(mockResetFields).toHaveBeenCalled();
  });
});
