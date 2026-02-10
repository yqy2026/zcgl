/**
 * AssetForm 组件测试
 * 保留关键交互：渲染与取消操作
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';
import AssetForm from '../AssetForm';

vi.mock('antd', () => {
  const Form = ({
    children,
    onFinish,
  }: {
    children: React.ReactNode;
    onFinish?: () => void;
  }) => (
    <form
      onSubmit={event => {
        event.preventDefault();
        onFinish?.();
      }}
    >
      {children}
    </form>
  );
  (Form as unknown as { useForm: () => [Record<string, unknown>] }).useForm = () => [{}];

  return {
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
      setFieldsValue: vi.fn(),
      getFieldValue: vi.fn(() => 0),
      getFieldsValue: vi.fn(() => ({})),
      resetFields: vi.fn(),
    },
    completionRate: 0,
    setCompletionRate: vi.fn(),
    fileList: [],
    setFileList: vi.fn(),
    terminalContractFileList: [],
    setTerminalContractFileList: vi.fn(),
  }),
  AssetBasicInfoSection: () => <div data-testid="asset-basic-section" />,
  AssetAreaSection: () => <div data-testid="asset-area-section" />,
  AssetStatusSection: () => <div data-testid="asset-status-section" />,
  AssetReceptionSection: () => <div data-testid="asset-reception-section" />,
  AssetDetailedSection: () => <div data-testid="asset-detailed-section" />,
}));

describe('AssetForm', () => {
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
});
