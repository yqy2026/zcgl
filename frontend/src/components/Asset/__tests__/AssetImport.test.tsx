/**
 * AssetImport 组件测试
 * 测试资产导入功能（Excel文件上传和处理）
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { QueryClient } from '@tanstack/react-query';
import { screen, fireEvent, waitFor, act, renderWithProviders } from '@/test/utils/test-helpers';
import AssetImport from '../AssetImport';

interface UploadDraggerMockProps {
  children?: React.ReactNode;
  beforeUpload?: (file: File) => boolean;
}

interface StepsMockProps {
  current?: number;
  items?: Array<{ title: React.ReactNode }>;
}

interface ProgressMockProps {
  percent?: number;
}

interface AlertMockProps {
  message?: React.ReactNode;
  description?: React.ReactNode;
  type?: string;
}

interface CardMockProps {
  children?: React.ReactNode;
  title?: React.ReactNode;
  size?: string;
  style?: React.CSSProperties;
  extra?: React.ReactNode;
}

interface ButtonMockProps {
  children?: React.ReactNode;
  onClick?: () => void;
  loading?: boolean;
}

interface StatisticMockProps {
  title?: React.ReactNode;
  value?: number;
}

interface TableMockProps {
  dataSource?: unknown[];
}

const {
  uploadDraggerMock,
  messageSuccessMock,
  messageErrorMock,
  importAssetsMock,
  downloadTemplateMock,
} = vi.hoisted(() => ({
  uploadDraggerMock: vi.fn(),
  messageSuccessMock: vi.fn(),
  messageErrorMock: vi.fn(),
  importAssetsMock: vi.fn(),
  downloadTemplateMock: vi.fn(),
}));

vi.mock('@/services/assetImportService', () => ({
  assetImportService: {
    importAssets: (...args: unknown[]) => importAssetsMock(...args),
    downloadTemplate: (...args: unknown[]) => downloadTemplateMock(...args),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: (...args: unknown[]) => messageSuccessMock(...args),
    error: (...args: unknown[]) => messageErrorMock(...args),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock Ant Design components
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');

  uploadDraggerMock.mockImplementation(({ children }: UploadDraggerMockProps) => (
    <div data-testid="upload-dragger">{children}</div>
  ));

  const mockUpload = {
    Dragger: uploadDraggerMock,
  };

  const mockSteps = vi.fn(({ current, items }: StepsMockProps) => (
    <div data-testid="steps" data-current={current} data-steps-count={items?.length ?? 0}>
      Step {current}
    </div>
  ));

  const mockProgress = vi.fn(({ percent }: ProgressMockProps) => (
    <div data-testid="progress" data-percent={percent} />
  ));

  const mockAlert = vi.fn(({ message, description, type }: AlertMockProps) => (
    <div data-testid="alert" data-type={type}>
      {message}
      {description}
    </div>
  ));

  const mockCard = vi.fn(({ children, title, extra }: CardMockProps) => (
    <div data-testid="card">
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      {children}
    </div>
  ));

  const mockButton = vi.fn(({ children, onClick, loading }: ButtonMockProps) => (
    <button data-testid="button" onClick={onClick} data-loading={loading}>
      {children}
    </button>
  ));

  const mockTitle = vi.fn(({ children }: { children?: React.ReactNode }) => (
    <div data-testid="title">{children}</div>
  ));

  const mockText = vi.fn(({ children }: { children?: React.ReactNode }) => (
    <span data-testid="text">{children}</span>
  ));

  const mockSpace = vi.fn(({ children }: { children?: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  ));

  const mockRow = vi.fn(({ children }: { children?: React.ReactNode }) => (
    <div data-testid="row">{children}</div>
  ));

  const mockCol = vi.fn(({ children }: { children?: React.ReactNode }) => (
    <div data-testid="col">{children}</div>
  ));

  const mockDivider = vi.fn(() => <div data-testid="divider" />);

  const mockFormItem = vi.fn(({ children }: { children?: React.ReactNode }) => (
    <div data-testid="form-item">{children}</div>
  ));

  const mockSwitch = vi.fn(({ checked }: { checked?: boolean }) => (
    <input type="checkbox" data-testid="switch" checked={checked} readOnly />
  ));

  const mockInputNumber = vi.fn(({ value }: { value?: number }) => (
    <input type="number" data-testid="input-number" value={value} readOnly />
  ));

  const mockSelect = vi.fn(({ children }: { children?: React.ReactNode }) => (
    <select data-testid="select">{children}</select>
  ));

  const mockSelectOption = vi.fn(
    ({ children, value }: { children?: React.ReactNode; value?: number }) => (
      <option value={value}>{children}</option>
    )
  );

  const mockStatistic = vi.fn(({ title, value }: StatisticMockProps) => (
    <div data-testid="statistic">
      <span>{title}</span>
      <span>{value}</span>
    </div>
  ));

  const mockTable = vi.fn(({ dataSource }: TableMockProps) => (
    <div data-testid="error-table" data-row-count={dataSource?.length ?? 0} />
  ));

  return {
    ...actual,
    Upload: mockUpload,
    Steps: mockSteps,
    Progress: mockProgress,
    Alert: mockAlert,
    Card: mockCard,
    Button: mockButton,
    Typography: {
      Title: mockTitle,
      Text: mockText,
    },
    Space: mockSpace,
    Row: mockRow,
    Col: mockCol,
    Divider: mockDivider,
    Form: {
      Item: mockFormItem,
    },
    Switch: mockSwitch,
    InputNumber: mockInputNumber,
    Select: Object.assign(mockSelect, { Option: mockSelectOption }),
    Statistic: mockStatistic,
    Table: mockTable,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  UploadOutlined: () => 'UploadOutlined',
  DownloadOutlined: () => 'DownloadOutlined',
  FileExcelOutlined: () => 'FileExcelOutlined',
  CheckCircleOutlined: () => 'CheckCircleOutlined',
  CheckCircleFilled: () => 'CheckCircleFilled',
  FileTextFilled: () => 'FileTextFilled',
  ExclamationCircleOutlined: () => 'ExclamationCircleOutlined',
  SettingOutlined: () => 'SettingOutlined',
}));

const createUploadFile = () => {
  if (typeof File !== 'undefined') {
    const file = new File(['data'], 'assets.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    return Object.assign(file, {
      uid: '1',
      originFileObj: file,
    });
  }

  const fallbackFile = {
    uid: '1',
    name: 'assets.xlsx',
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    size: 1024,
  } as File;

  return Object.assign(fallbackFile, {
    originFileObj: fallbackFile,
  });
};

describe('AssetImport - 渲染与交互测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    uploadDraggerMock.mockClear();
    messageSuccessMock.mockClear();
    messageErrorMock.mockClear();
    importAssetsMock.mockClear();
    downloadTemplateMock.mockClear();

    if (typeof URL !== 'undefined') {
      URL.createObjectURL = vi.fn(() => 'blob:mock');
      URL.revokeObjectURL = vi.fn();
    }
  });

  it('应该渲染初始步骤与上传区域', () => {
    renderWithProviders(<AssetImport />);

    expect(screen.getByTestId('steps')).toHaveAttribute('data-current', '0');
    expect(screen.getByText('下载Excel模板')).toBeInTheDocument();
    expect(screen.getByTestId('upload-dragger')).toBeInTheDocument();
    expect(screen.getByText('第一步：下载模板')).toBeInTheDocument();
  });

  it('上传无效类型文件应提示错误且不前进', () => {
    renderWithProviders(<AssetImport />);
    const draggerProps = uploadDraggerMock.mock.calls[0][0] as UploadDraggerMockProps;

    const invalidFile = { type: 'text/plain', size: 1024 } as File;
    act(() => {
      expect(draggerProps.beforeUpload?.(invalidFile)).toBe(false);
    });
    expect(messageErrorMock).toHaveBeenCalledWith('只能上传Excel文件(.xlsx, .xls)');
    expect(screen.getByTestId('steps')).toHaveAttribute('data-current', '0');
  });

  it('上传有效文件应进入步骤1并显示文件名', async () => {
    renderWithProviders(<AssetImport />);
    const draggerProps = uploadDraggerMock.mock.calls[0][0] as UploadDraggerMockProps;

    act(() => {
      draggerProps.beforeUpload?.(createUploadFile());
    });

    await waitFor(() => {
      expect(screen.getByTestId('steps')).toHaveAttribute('data-current', '1');
    });
    expect(screen.getByText('文件已选择')).toBeInTheDocument();
    expect(screen.getByText(/assets\.xlsx/)).toBeInTheDocument();
  });

  it('导入成功应显示结果摘要', async () => {
    importAssetsMock.mockResolvedValue({
      success: 2,
      failed: 0,
      total: 2,
      errors: [],
      message: 'ok',
      processing_time: 5,
    });

    renderWithProviders(<AssetImport />);
    const draggerProps = uploadDraggerMock.mock.calls[0][0] as UploadDraggerMockProps;
    act(() => {
      draggerProps.beforeUpload?.(createUploadFile());
    });

    await waitFor(() => {
      expect(screen.getByTestId('steps')).toHaveAttribute('data-current', '1');
    });

    await act(async () => {
      fireEvent.click(screen.getByText('开始导入'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('steps')).toHaveAttribute('data-current', '2');
    });

    expect(importAssetsMock).toHaveBeenCalledWith(
      expect.any(File),
      expect.objectContaining({
        sheetName: '土地物业资产数据',
        skipErrors: true,
        useOptimized: true,
        timeoutSeconds: 600,
      })
    );
    expect(screen.getByText(/导入成功/)).toBeInTheDocument();
  });

  it('导入成功后应失效资产列表、资产统计与分析查询前缀', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0,
        },
        mutations: {
          retry: false,
        },
      },
    });
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

    importAssetsMock.mockResolvedValue({
      success: 3,
      failed: 0,
      total: 3,
      errors: [],
      message: 'ok',
      processing_time: 8,
    });

    renderWithProviders(<AssetImport />, { queryClient });
    const draggerProps = uploadDraggerMock.mock.calls[0][0] as UploadDraggerMockProps;

    act(() => {
      draggerProps.beforeUpload?.(createUploadFile());
    });

    await waitFor(() => {
      expect(screen.getByTestId('steps')).toHaveAttribute('data-current', '1');
    });

    await act(async () => {
      fireEvent.click(screen.getByText('开始导入'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('steps')).toHaveAttribute('data-current', '2');
    });

    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['assets-list'] });
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['asset-stats'] });
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['analytics'] });
  });

  it('导入失败应提示错误并显示失败摘要', async () => {
    importAssetsMock.mockRejectedValue(new Error('Network error'));

    renderWithProviders(<AssetImport />);
    const draggerProps = uploadDraggerMock.mock.calls[0][0] as UploadDraggerMockProps;
    act(() => {
      draggerProps.beforeUpload?.(createUploadFile());
    });

    await waitFor(() => {
      expect(screen.getByTestId('steps')).toHaveAttribute('data-current', '1');
    });

    await act(async () => {
      fireEvent.click(screen.getByText('开始导入'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('steps')).toHaveAttribute('data-current', '2');
    });

    expect(messageErrorMock).toHaveBeenCalledWith(expect.stringContaining('导入失败'));
    expect(screen.getByText(/没有数据被导入/)).toBeInTheDocument();
  });
});
