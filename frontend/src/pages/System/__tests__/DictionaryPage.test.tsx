/**
 * DictionaryPage 页面测试
 * 覆盖枚举概览与详情加载行为
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderWithProviders, screen, waitFor, within, fireEvent } from '@/test/utils/test-helpers';
import DictionaryPage from '../DictionaryPage';
import { dictionaryService } from '@/services/dictionary';

vi.mock('@/services/dictionary', () => ({
  dictionaryService: {
    getTypes: vi.fn(),
    getEnumFieldTypes: vi.fn(),
    getEnumFieldData: vi.fn(),
    getEnumFieldValuesByTypeCode: vi.fn(),
    deleteEnumValue: vi.fn(),
    updateEnumValue: vi.fn(),
    createEnumValue: vi.fn(),
    toggleEnumValueActive: vi.fn(),
  },
}));

vi.mock('@/components/Dictionary/EnumValuePreview', () => ({
  default: () => <div data-testid="enum-preview" />,
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('@ant-design/icons', () => ({
  SearchOutlined: () => <span data-testid="icon-search" />,
}));

vi.mock('@/components/Common/TableWithPagination', () => ({
  TableWithPagination: ({ columns = [], dataSource = [], rowKey }: {
    columns?: Array<{
      key?: string | number;
      dataIndex?: string | string[];
      render?: (value: unknown, record: Record<string, unknown>) => React.ReactNode;
    }>;
    dataSource?: Array<Record<string, unknown>>;
    rowKey?: string | ((record: Record<string, unknown>) => string | number);
  }) => (
    <div data-testid="table">
      {dataSource.map((record, index) => {
        const key =
          typeof rowKey === 'function'
            ? rowKey(record)
            : rowKey
              ? record[rowKey]
              : index;
        return (
          <div key={String(key)} data-testid="table-row">
            {columns.map((column, colIndex) => {
              const columnKey = String(column.key ?? column.dataIndex ?? colIndex);
              if (column.render) {
                let value: unknown;
                if (Array.isArray(column.dataIndex)) {
                  value = column.dataIndex.reduce<unknown>((acc, dataKey) => {
                    if (acc != null && typeof acc === 'object') {
                      return (acc as Record<string, unknown>)[dataKey];
                    }
                    return undefined;
                  }, record);
                } else if (typeof column.dataIndex === 'string') {
                  value = record[column.dataIndex];
                }
                return <div key={columnKey}>{column.render(value, record)}</div>;
              }
              if (column.dataIndex) {
                if (Array.isArray(column.dataIndex)) {
                  const nestedValue = column.dataIndex.reduce<unknown>((acc, dataKey) => {
                    if (acc != null && typeof acc === 'object') {
                      return (acc as Record<string, unknown>)[dataKey];
                    }
                    return undefined;
                  }, record);
                  return <div key={columnKey}>{nestedValue as React.ReactNode}</div>;
                }
                return <div key={columnKey}>{record[column.dataIndex]}</div>;
              }
              return <div key={columnKey} />;
            })}
          </div>
        );
      })}
    </div>
  ),
}));

vi.mock('antd', () => {
  const formInstance = {
    resetFields: vi.fn(),
    setFieldsValue: vi.fn(),
    validateFields: vi.fn(() => Promise.resolve({})),
  };

  const Form = vi.fn(({ children }) => <form data-testid="form">{children}</form>);
  Form.Item = vi.fn(({ children }) => <div data-testid="form-item">{children}</div>);
  Form.useForm = vi.fn(() => [formInstance]);

  const Select = (({ children, onChange, placeholder, value }: {
    children?: React.ReactNode;
    onChange?: (value: string) => void;
    placeholder?: string;
    value?: string;
  }) => (
    <select
      data-testid={`select-${placeholder ?? 'default'}`}
      value={value ?? ''}
      onChange={event => onChange?.((event.target as HTMLSelectElement).value)}
    >
      <option value="">{placeholder}</option>
      {children}
    </select>
  )) as React.FC<{
    children?: React.ReactNode;
    onChange?: (value: string) => void;
    placeholder?: string;
    value?: string;
  }> & { Option?: React.FC<{ children?: React.ReactNode; value?: string }> };

  const Option = ({ children, value }: { children?: React.ReactNode; value?: string }) => (
    <option value={value}>{children}</option>
  );
  Option.displayName = 'MockSelectOption';
  Select.Option = Option;
  Select.displayName = 'MockSelect';

  return {
    Button: ({ children, onClick }: { children?: React.ReactNode; onClick?: () => void }) => (
      <button data-testid="button" onClick={onClick}>
        {children}
      </button>
    ),
    Card: ({ children, title, extra }: { children?: React.ReactNode; title?: React.ReactNode; extra?: React.ReactNode }) => (
      <div data-testid="card">
        <div>{title}</div>
        <div>{extra}</div>
        {children}
      </div>
    ),
    Form,
    Input: Object.assign(
      ({ placeholder, value, onChange }: { placeholder?: string; value?: string; onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void }) => (
        <input data-testid="input" placeholder={placeholder} value={value} onChange={onChange} />
      ),
      {
        TextArea: ({ rows }: { rows?: number }) => <textarea data-testid="textarea" rows={rows} />,
        Search: ({ placeholder, value, onChange }: { placeholder?: string; value?: string; onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void }) => (
          <input
            data-testid="search-input"
            placeholder={placeholder}
            value={value}
            onChange={onChange}
          />
        ),
      }
    ),
    Modal: ({ open, title, children }: { open?: boolean; title?: React.ReactNode; children?: React.ReactNode }) =>
      open ? (
        <div data-testid="modal">
          <div>{title}</div>
          {children}
        </div>
      ) : null,
    Popconfirm: ({ children, onConfirm }: { children?: React.ReactNode; onConfirm?: () => void }) => (
      <span data-testid="popconfirm" onClick={onConfirm}>
        {children}
      </span>
    ),
    Row: ({ children }: { children?: React.ReactNode }) => <div data-testid="row">{children}</div>,
    Col: ({ children }: { children?: React.ReactNode }) => <div data-testid="col">{children}</div>,
    Select,
    Space: ({ children }: { children?: React.ReactNode }) => <div data-testid="space">{children}</div>,
    Switch: ({ checked, onChange }: { checked?: boolean; onChange?: (checked: boolean) => void }) => (
      <button data-testid="switch" onClick={() => onChange?.(!checked)}>
        {checked ? 'on' : 'off'}
      </button>
    ),
    Tag: ({ children }: { children?: React.ReactNode }) => <span data-testid="tag">{children}</span>,
    Badge: ({ count }: { count?: number }) => <span data-testid="badge">{count}</span>,
  };
});

const enumTypes = [
  {
    id: 'type-1',
    name: '状态',
    code: 'status',
    category: '系统',
    description: '状态类型',
    is_system: false,
    is_multiple: false,
    is_hierarchical: false,
    status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const overviewData = [
  {
    type: enumTypes[0],
    values: [],
  },
];

const detailRows = [
  {
    id: 'value-1',
    dict_type: 'status',
    dict_code: 'detail',
    dict_label: '仅详情',
    dict_value: 'DETAIL',
    sort_order: 1,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const renderDictionaryPage = async () => {
  renderWithProviders(<DictionaryPage />);
  await waitFor(() => {
    expect(dictionaryService.getEnumFieldData).toHaveBeenCalled();
  });
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(dictionaryService.getTypes).mockResolvedValue(['status']);
  vi.mocked(dictionaryService.getEnumFieldTypes).mockResolvedValue(enumTypes);
  vi.mocked(dictionaryService.getEnumFieldData).mockResolvedValue(overviewData);
  vi.mocked(dictionaryService.getEnumFieldValuesByTypeCode).mockResolvedValue(detailRows);
});

describe('DictionaryPage - 概览加载', () => {
  it('应该加载并展示枚举类型概览', async () => {
    await renderDictionaryPage();

    await waitFor(() => {
      expect(dictionaryService.getEnumFieldData).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row').length).toBeGreaterThan(0);
    });

    const rows = screen.getAllByTestId('table-row');
    const firstRow = rows[0];
    expect(within(firstRow).getByText('状态')).toBeInTheDocument();
    expect(within(firstRow).getByText('status')).toBeInTheDocument();
  });
});

describe('DictionaryPage - 详情加载', () => {
  it('点击查看详情应加载枚举值列表', async () => {
    await renderDictionaryPage();

    await waitFor(() => {
      expect(screen.getByText('查看详情')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('查看详情'));

    await waitFor(() => {
      expect(dictionaryService.getEnumFieldValuesByTypeCode).toHaveBeenCalledWith('status');
    });

    expect(await screen.findByText('仅详情')).toBeInTheDocument();
  });
});
