/**
 * AssetForm 组件测试
 * 保留关键交互：渲染与取消操作
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderWithProviders, screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import AssetForm from '../AssetForm';

const setFieldsValueMock = vi.fn();
const getFieldValueMock = vi.fn(() => 0);
const getFieldsValueMock = vi.fn(() => ({}));
const resetFieldsMock = vi.fn();
const setCompletionRateMock = vi.fn();
const setFileListMock = vi.fn();
const setTerminalContractFileListMock = vi.fn();
let mockSubmitValues: Record<string, unknown> = {};

vi.mock('antd', async importOriginal => {
  const actual = await importOriginal<typeof import('antd')>();
  const Form = ({
    children,
    onFinish,
  }: {
    children: React.ReactNode;
    onFinish?: (values: Record<string, unknown>) => void;
  }) => (
    <form
      onSubmit={event => {
        event.preventDefault();
        onFinish?.(mockSubmitValues);
      }}
    >
      {children}
    </form>
  );
  (Form as unknown as { useForm: () => [Record<string, unknown>] }).useForm = () => [{}];

  return {
    ...actual,
    Form,
    Button: ({
      children,
      onClick,
      htmlType,
    }: {
      children: React.ReactNode;
      onClick?: () => void;
      htmlType?: 'button' | 'submit' | 'reset';
    }) => (
      <button type={htmlType ?? 'button'} onClick={onClick}>
        {children}
      </button>
    ),
    Space: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Card: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Row: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Col: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Progress: () => <div data-testid="progress" />,
    Typography: {
      Text: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
    },
  };
});

vi.mock('@/hooks/useDictionary', () => ({
  useDictionaries: vi.fn(),
}));

vi.mock('../Asset', () => ({
  AssetFormProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAssetFormContext: () => ({
    form: {
      setFieldsValue: setFieldsValueMock,
      getFieldValue: getFieldValueMock,
      getFieldsValue: getFieldsValueMock,
      resetFields: resetFieldsMock,
    },
    completionRate: 0,
    setCompletionRate: setCompletionRateMock,
    fileList: [],
    setFileList: setFileListMock,
    terminalContractFileList: [],
    setTerminalContractFileList: setTerminalContractFileListMock,
  }),
  AssetBasicInfoSection: () => <div data-testid="asset-basic-section" />,
  AssetAreaSection: () => <div data-testid="asset-area-section" />,
  AssetStatusSection: () => <div data-testid="asset-status-section" />,
  AssetReceptionSection: () => <div data-testid="asset-reception-section" />,
  AssetDetailedSection: () => <div data-testid="asset-detailed-section" />,
}));

describe('AssetForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmitValues = {};
  });

  it('应该渲染资产表单与操作按钮', () => {
    renderWithProviders(<AssetForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByTestId('asset-basic-section')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重置' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '取消' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '创建资产' })).toBeInTheDocument();
  });

  it('点击取消应触发回调', () => {
    const handleCancel = vi.fn();
    renderWithProviders(<AssetForm onSubmit={vi.fn()} onCancel={handleCancel} />);

    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });

  it('编辑态应回填 owner_party_id', async () => {
    renderWithProviders(
      <AssetForm
        mode="edit"
        initialData={{ owner_party_id: 'party-owner' }}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(setFieldsValueMock).toHaveBeenCalledWith(
        expect.objectContaining({
          owner_party_id: 'party-owner',
        })
      );
    });
  });

  it('提交时应包含 address_detail 字段', async () => {
    const handleSubmit = vi.fn(async () => undefined);
    mockSubmitValues = {
      asset_name: '测试资产',
      owner_party_id: 'party-owner',
      address: '天河区体育西路 100 号',
      ownership_status: '已确权',
      property_nature: '经营性',
      usage_status: '出租',
    };

    renderWithProviders(<AssetForm onSubmit={handleSubmit} onCancel={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: '创建资产' }));

    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          address_detail: '天河区体育西路 100 号',
          address: '天河区体育西路 100 号',
        })
      );
    });
  });
});
