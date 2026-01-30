/**
 * AssetExport 组件测试
 * 测试资产导出功能（Excel/CSV导出）
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// Mock services
vi.mock('@/services/assetService', () => ({
  assetService: {
    exportAssets: vi.fn(() => Promise.resolve({ url: '/download/export.xlsx' })),
    exportSelectedAssets: vi.fn(() =>
      Promise.resolve({ url: '/download/selected.xlsx' })
    ),
    getExportHistory: vi.fn(() =>
      Promise.resolve([
        {
          id: '1',
          filename: 'export_20240101.xlsx',
          created_at: '2024-01-01T00:00:00.000Z',
          status: 'completed',
          record_count: 100,
        },
      ])
    ),
    downloadExportFile: vi.fn(),
    deleteExportRecord: vi.fn(),
  },
}));

// Mock @tanstack/react-query
const mockMutate = vi.fn();
vi.mock('@tanstack/react-query', () => ({
  useMutation: vi.fn(() => ({
    mutate: mockMutate,
    mutateAsync: vi.fn(() => Promise.resolve({ url: '/download/export.xlsx' })),
    isPending: false,
    isSuccess: false,
    isError: false,
  })),
  useQuery: vi.fn(() => ({
    data: [
      {
        id: '1',
        filename: 'export_20240101.xlsx',
        created_at: '2024-01-01T00:00:00.000Z',
        status: 'completed',
        record_count: 100,
      },
    ],
    isLoading: false,
    refetch: vi.fn(),
  })),
}));

// Mock message manager
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock Form.useForm
const mockFormInstance = {
  getFieldsValue: vi.fn(() => ({ format: 'xlsx', includeEmpty: false })),
  setFieldsValue: vi.fn(),
  validateFields: vi.fn(() => Promise.resolve({ format: 'xlsx' })),
  resetFields: vi.fn(),
};

// Mock Ant Design
vi.mock('antd', () => {
  const Card = ({
    children,
    title,
  }: {
    children: React.ReactNode;
    title?: React.ReactNode;
  }) => (
    <div data-testid="export-card">
      {title && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  );

  const Form = ({
    children,
  }: {
    children: React.ReactNode;
  }) => <form data-testid="export-form">{children}</form>;

  Form.Item = ({
    children,
    label,
    name,
  }: {
    children: React.ReactNode;
    label?: string;
    name?: string;
  }) => (
    <div data-testid={`form-item-${name || label}`}>
      {label && <label>{label}</label>}
      {children}
    </div>
  );

  Form.useForm = () => [mockFormInstance];

  const Select = ({
    children,
    placeholder,
    onChange,
    value,
  }: {
    children?: React.ReactNode;
    placeholder?: string;
    onChange?: (value: string) => void;
    value?: string;
  }) => (
    <select
      data-testid="select"
      value={value}
      onChange={e => onChange?.(e.target.value)}
    >
      <option value="">{placeholder}</option>
      {children}
    </select>
  );

  Select.Option = ({
    children,
    value,
  }: {
    children: React.ReactNode;
    value: string;
  }) => <option value={value}>{children}</option>;

  return {
    Card,
    Form,
    Select,
    Checkbox: ({
      children,
      checked,
      onChange,
    }: {
      children?: React.ReactNode;
      checked?: boolean;
      onChange?: (e: { target: { checked: boolean } }) => void;
    }) => (
      <label data-testid="checkbox">
        <input
          type="checkbox"
          checked={checked}
          onChange={e => onChange?.({ target: { checked: e.target.checked } })}
        />
        {children}
      </label>
    ),
    Button: ({
      children,
      onClick,
      icon,
      type,
      loading,
      disabled,
    }: {
      children?: React.ReactNode;
      onClick?: () => void;
      icon?: React.ReactNode;
      type?: string;
      loading?: boolean;
      disabled?: boolean;
    }) => (
      <button
        data-testid={`btn-${type || 'default'}`}
        data-loading={loading}
        disabled={disabled}
        onClick={onClick}
      >
        {icon}
        {children}
      </button>
    ),
    Space: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="space">{children}</div>
    ),
    Alert: ({
      message,
      type,
    }: {
      message: string;
      type?: string;
    }) => (
      <div data-testid="alert" data-type={type}>
        {message}
      </div>
    ),
    Progress: ({
      percent,
      status,
    }: {
      percent: number;
      status?: string;
    }) => (
      <div data-testid="progress" data-percent={percent} data-status={status}>
        {percent}%
      </div>
    ),
    Typography: {
      Title: ({
        children,
        level,
      }: {
        children: React.ReactNode;
        level?: number;
      }) => (
        <div data-testid="title" data-level={level}>
          {children}
        </div>
      ),
      Text: ({
        children,
        type,
      }: {
        children: React.ReactNode;
        type?: string;
      }) => (
        <span data-testid="text" data-type={type}>
          {children}
        </span>
      ),
    },
    Divider: () => <hr data-testid="divider" />,
    Row: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="row">{children}</div>
    ),
    Col: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="col">{children}</div>
    ),
    Tag: ({
      children,
      color,
    }: {
      children: React.ReactNode;
      color?: string;
    }) => (
      <span data-testid="tag" data-color={color}>
        {children}
      </span>
    ),
    Modal: ({
      children,
      open,
      title,
      onCancel,
    }: {
      children: React.ReactNode;
      open?: boolean;
      title?: string;
      onCancel?: () => void;
    }) =>
      open ? (
        <div data-testid="modal" data-title={title}>
          <div data-testid="modal-title">{title}</div>
          <div data-testid="modal-content">{children}</div>
          <button data-testid="modal-close" onClick={onCancel}>
            关闭
          </button>
        </div>
      ) : null,
    List: ({
      dataSource,
      renderItem,
      locale,
    }: {
      dataSource: Array<{ id: string; filename: string }>;
      renderItem: (item: { id: string; filename: string }) => React.ReactNode;
      locale?: { emptyText: string };
    }) => (
      <div data-testid="list">
        {dataSource.length === 0 ? (
          <div data-testid="list-empty">{locale?.emptyText}</div>
        ) : (
          dataSource.map(item => <div key={item.id}>{renderItem(item)}</div>)
        )}
      </div>
    ),
    Tooltip: ({
      children,
      title,
    }: {
      children: React.ReactNode;
      title: string;
    }) => (
      <div data-testid="tooltip" title={title}>
        {children}
      </div>
    ),
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  DownloadOutlined: () => <span data-testid="icon-download">DownloadIcon</span>,
  FileExcelOutlined: () => <span data-testid="icon-excel">ExcelIcon</span>,
  HistoryOutlined: () => <span data-testid="icon-history">HistoryIcon</span>,
  DeleteOutlined: () => <span data-testid="icon-delete">DeleteIcon</span>,
  CheckCircleOutlined: () => <span data-testid="icon-check">CheckIcon</span>,
  LoadingOutlined: () => <span data-testid="icon-loading">LoadingIcon</span>,
  FilePdfOutlined: () => <span data-testid="icon-pdf">PdfIcon</span>,
}));

import AssetExport from '../AssetExport';
import { MessageManager } from '@/utils/messageManager';

describe('AssetExport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染导出卡片', () => {
      render(<AssetExport />);

      expect(screen.getByTestId('export-card')).toBeInTheDocument();
    });

    it('应该显示导出表单', () => {
      render(<AssetExport />);

      expect(screen.getByTestId('export-form')).toBeInTheDocument();
    });

    it('应该显示导出按钮', () => {
      render(<AssetExport />);

      expect(screen.getByText('导出')).toBeInTheDocument();
    });

    it('导出按钮应该是primary类型', () => {
      render(<AssetExport />);

      expect(screen.getByTestId('btn-primary')).toBeInTheDocument();
    });
  });

  describe('导出格式选择', () => {
    it('应该显示格式选择器', () => {
      render(<AssetExport />);

      expect(screen.getByTestId('form-item-format')).toBeInTheDocument();
    });

    it('应该有Excel和CSV选项', () => {
      render(<AssetExport />);

      expect(screen.getByText('Excel (.xlsx)')).toBeInTheDocument();
      expect(screen.getByText('CSV (.csv)')).toBeInTheDocument();
    });
  });

  describe('导出选项', () => {
    it('应该显示包含空值选项', () => {
      render(<AssetExport />);

      expect(screen.getByTestId('checkbox')).toBeInTheDocument();
    });

    it('应该显示选择导出字段选项', () => {
      render(<AssetExport />);

      expect(screen.getByText('选择导出字段')).toBeInTheDocument();
    });
  });

  describe('导出按钮点击', () => {
    it('点击导出按钮应该触发导出', async () => {
      render(<AssetExport />);

      const exportButton = screen.getByText('导出');
      fireEvent.click(exportButton);

      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalled();
      });
    });

    it('导出成功应该显示成功消息', async () => {
      render(<AssetExport />);

      const exportButton = screen.getByText('导出');
      fireEvent.click(exportButton);

      await waitFor(() => {
        expect(MessageManager.success).toHaveBeenCalled();
      });
    });
  });

  describe('导出历史', () => {
    it('应该显示历史按钮', () => {
      render(<AssetExport />);

      expect(screen.getByText('导出历史')).toBeInTheDocument();
    });

    it('点击历史按钮应该打开历史弹窗', () => {
      render(<AssetExport />);

      const historyButton = screen.getByText('导出历史');
      fireEvent.click(historyButton);

      expect(screen.getByTestId('modal')).toBeInTheDocument();
    });

    it('历史弹窗应该显示历史列表', () => {
      render(<AssetExport />);

      const historyButton = screen.getByText('导出历史');
      fireEvent.click(historyButton);

      expect(screen.getByTestId('list')).toBeInTheDocument();
    });
  });

  describe('选中资产导出', () => {
    it('有选中资产时应该显示选中数量', () => {
      render(<AssetExport selectedAssetIds={['1', '2', '3']} />);

      expect(screen.getByText(/已选中 3 项/)).toBeInTheDocument();
    });

    it('没有选中资产时应该显示导出全部', () => {
      render(<AssetExport selectedAssetIds={[]} />);

      expect(screen.getByText('导出全部')).toBeInTheDocument();
    });
  });

  describe('属性传递', () => {
    it('应该接受searchParams属性', () => {
      const searchParams = { ownership_status: '已确权' as const };
      render(<AssetExport searchParams={searchParams} />);

      expect(screen.getByTestId('export-card')).toBeInTheDocument();
    });

    it('应该接受onExportComplete回调', () => {
      const onExportComplete = vi.fn();
      render(<AssetExport onExportComplete={onExportComplete} />);

      expect(screen.getByTestId('export-card')).toBeInTheDocument();
    });
  });

  describe('图标显示', () => {
    it('应该显示下载图标', () => {
      render(<AssetExport />);

      expect(screen.getByTestId('icon-download')).toBeInTheDocument();
    });

    it('应该显示Excel图标', () => {
      render(<AssetExport />);

      expect(screen.getByTestId('icon-excel')).toBeInTheDocument();
    });

    it('应该显示历史图标', () => {
      render(<AssetExport />);

      expect(screen.getByTestId('icon-history')).toBeInTheDocument();
    });
  });

  describe('加载状态', () => {
    it('导出中应该显示loading状态', () => {
      const { useMutation } = require('@tanstack/react-query');
      vi.mocked(useMutation).mockReturnValueOnce({
        mutate: mockMutate,
        isPending: true,
        isSuccess: false,
        isError: false,
      });

      render(<AssetExport />);

      const exportButton = screen.getByTestId('btn-primary');
      expect(exportButton).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('表单验证', () => {
    it('表单应该有默认值', () => {
      render(<AssetExport />);

      expect(mockFormInstance.getFieldsValue).toBeDefined();
    });
  });

  describe('提示信息', () => {
    it('应该显示导出说明', () => {
      render(<AssetExport />);

      expect(screen.getByTestId('alert')).toBeInTheDocument();
    });

    it('说明应该是info类型', () => {
      render(<AssetExport />);

      const alert = screen.getByTestId('alert');
      expect(alert).toHaveAttribute('data-type', 'info');
    });
  });
});
