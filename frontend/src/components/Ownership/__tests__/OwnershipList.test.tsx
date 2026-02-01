/**
 * OwnershipList 组件测试
 *
 * 测试覆盖范围:
 * - 组件基本渲染
 * - 统计卡片显示
 * - 搜索功能
 * - 表格渲染
 * - 操作按钮
 * - 模态框交互
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';

import { useListData } from '@/hooks/useListData';
import { ownershipService } from '@/services/ownershipService';

vi.mock('@/hooks/useListData', () => ({
  useListData: vi.fn(),
}));

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnershipStatistics: vi.fn(() =>
      Promise.resolve({
        total_count: 10,
        active_count: 8,
        inactive_count: 2,
      })
    ),
    deleteOwnership: vi.fn(() => Promise.resolve({ success: true })),
    toggleOwnershipStatus: vi.fn(() => Promise.resolve({ success: true })),
  },
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

// Mock messageManager
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

// Mock OwnershipForm
vi.mock('../../Forms', () => ({
  OwnershipForm: ({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) => (
    <div data-testid="ownership-form">
      <button data-testid="form-submit" onClick={onSuccess}>
        提交
      </button>
      <button data-testid="form-cancel" onClick={onCancel}>
        取消
      </button>
    </div>
  ),
}));

// Mock OwnershipDetail
vi.mock('../OwnershipDetail', () => ({
  default: ({ ownership, onEdit }: { ownership: { name: string }; onEdit: () => void }) => (
    <div data-testid="ownership-detail">
      <span data-testid="detail-name">{ownership.name}</span>
      <button data-testid="detail-edit" onClick={onEdit}>
        编辑
      </button>
    </div>
  ),
}));

vi.mock('@/components/Common/TableWithPagination', () => ({
  TableWithPagination: ({
    dataSource,
  }: {
    dataSource?: Array<{ id: string; name: string; code: string; is_active: boolean }>;
  }) => (
    <div data-testid="table">
      {dataSource?.map(item => (
        <div key={item.id} data-testid={`row-${item.id}`}>
          <span data-testid={`name-${item.id}`}>{item.name}</span>
          <span data-testid={`code-${item.id}`}>{item.code}</span>
          <span data-testid={`status-${item.id}`}>{item.is_active ? '启用' : '禁用'}</span>
        </div>
      ))}
    </div>
  ),
}));

// Mock Ant Design
vi.mock('antd', () => ({
  Button: ({
    children,
    onClick,
    icon,
    type,
    loading,
    danger,
  }: {
    children?: React.ReactNode;
    onClick?: () => void;
    icon?: React.ReactNode;
    type?: string;
    loading?: boolean;
    danger?: boolean;
  }) => (
    <button
      data-testid="button"
      data-type={type}
      data-loading={loading}
      data-danger={danger}
      onClick={onClick}
    >
      {icon}
      {children}
    </button>
  ),
  Space: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  ),
  Tooltip: ({ children, title }: { children?: React.ReactNode; title?: string }) => (
    <div data-testid="tooltip" data-title={title}>
      {children}
    </div>
  ),
  Modal: ({
    children,
    open,
    title,
    onCancel,
  }: {
    children?: React.ReactNode;
    open?: boolean;
    title?: string;
    onCancel?: () => void;
  }) => (
    <div data-testid="modal" data-open={open} data-title={title}>
      {open && (
        <>
          <div data-testid="modal-title">{title}</div>
          <div data-testid="modal-content">{children}</div>
          <button data-testid="modal-close" onClick={onCancel}>
            关闭
          </button>
        </>
      )}
    </div>
  ),
  Card: ({ children, title }: { children?: React.ReactNode; title?: string }) => (
    <div data-testid="card" data-title={title}>
      {title && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  ),
  Row: ({
    children,
    gutter,
  }: {
    children?: React.ReactNode;
    gutter?: number | [number, number];
  }) => (
    <div data-testid="row" data-gutter={JSON.stringify(gutter)}>
      {children}
    </div>
  ),
  Col: ({ children, span }: { children?: React.ReactNode; span?: number }) => (
    <div data-testid="col" data-span={span}>
      {children}
    </div>
  ),
  Statistic: ({ title, value }: { title?: string; value?: number }) => (
    <div data-testid="statistic" data-title={title}>
      <span data-testid="statistic-title">{title}</span>
      <span data-testid="statistic-value">{value}</span>
    </div>
  ),
  Badge: ({ status, text }: { status?: string; text?: string }) => (
    <span data-testid="badge" data-status={status}>
      {text}
    </span>
  ),
  Input: {
    Search: ({
      placeholder,
      value,
      onChange,
      onSearch,
    }: {
      placeholder?: string;
      value?: string;
      onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
      onSearch?: (value: string) => void;
    }) => (
      <div data-testid="input-search">
        <input
          data-testid="search-input"
          placeholder={placeholder}
          value={value || ''}
          onChange={onChange}
          onKeyDown={event => {
            if (event.key === 'Enter') {
              onSearch?.((event.target as HTMLInputElement).value);
            }
          }}
        />
        <button
          data-testid="search-button"
          onClick={() => onSearch?.(value ?? '')}
        >
          搜索
        </button>
      </div>
    ),
  },
  Select: (() => {
    const Select = ({
      children,
      placeholder,
      value,
      onChange,
    }: {
      children?: React.ReactNode;
      placeholder?: string;
      value?: boolean;
      onChange?: (value: boolean | undefined) => void;
    }) => (
      <div data-testid="select" data-placeholder={placeholder}>
        <select
          data-testid="select-input"
          value={value === undefined ? '' : String(value)}
          onChange={e => {
            const val = e.target.value;
            onChange?.(val === '' ? undefined : val === 'true');
          }}
        >
          <option value="">{placeholder}</option>
          {children}
        </select>
      </div>
    );
    Select.displayName = 'MockSelect';
    const Option = ({
      children,
      value,
    }: {
      children?: React.ReactNode;
      value?: string | boolean;
    }) => <option value={String(value ?? '')}>{children}</option>;
    Option.displayName = 'MockSelectOption';
    Select.Option = Option;
    return Select;
  })(),
  Switch: ({
    checked,
    onChange,
    size,
  }: {
    checked?: boolean;
    onChange?: () => void;
    size?: string;
  }) => (
    <button data-testid="switch" data-checked={checked} data-size={size} onClick={onChange}>
      {checked ? '启用' : '禁用'}
    </button>
  ),
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span data-testid="icon-plus">+</span>,
  EditOutlined: () => <span data-testid="icon-edit">Edit</span>,
  DeleteOutlined: () => <span data-testid="icon-delete">Delete</span>,
  EyeOutlined: () => <span data-testid="icon-eye">Eye</span>,
  SearchOutlined: () => <span data-testid="icon-search">Search</span>,
  ReloadOutlined: () => <span data-testid="icon-reload">Reload</span>,
  ExclamationCircleOutlined: () => <span data-testid="icon-exclamation">!</span>,
}));

import OwnershipList from '../OwnershipList';

const flushPromises = () =>
  new Promise<void>(resolve => {
    setTimeout(resolve, 0);
  });

const renderOwnershipList = async (
  props?: React.ComponentProps<typeof OwnershipList>
) => {
  await act(async () => {
    render(<OwnershipList {...props} />);
    await flushPromises();
  });
};

const mockLoadList = vi.fn();
const mockApplyFilters = vi.fn();
const mockResetFilters = vi.fn();
const mockUpdatePagination = vi.fn();

describe('OwnershipList 组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useListData).mockReturnValue({
      data: [
        {
          id: '1',
          name: '权属方1',
          code: 'OWN-001',
          short_name: '权属1',
          is_active: true,
          asset_count: 10,
          project_count: 5,
        },
        {
          id: '2',
          name: '权属方2',
          code: 'OWN-002',
          short_name: '权属2',
          is_active: false,
          asset_count: 5,
          project_count: 2,
        },
      ],
      loading: false,
      pagination: { current: 1, pageSize: 10, total: 2 },
      filters: { keyword: '', isActive: null },
      loadList: mockLoadList,
      applyFilters: mockApplyFilters,
      resetFilters: mockResetFilters,
      updatePagination: mockUpdatePagination,
    });
  });

  describe('基本渲染', () => {
    it('应该正确渲染组件', async () => {
      await renderOwnershipList();

      expect(screen.getByTestId('input-search')).toBeInTheDocument();
      expect(screen.getByTestId('table')).toBeInTheDocument();
    });

    it('应该渲染搜索输入框', async () => {
      await renderOwnershipList();

      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toBeInTheDocument();
      expect(searchInput).toHaveAttribute('placeholder', '搜索权属方名称、简称等');
    });

    it('应该渲染状态筛选下拉框', async () => {
      await renderOwnershipList();

      const select = screen.getByTestId('select');
      expect(select).toBeInTheDocument();
      expect(select).toHaveAttribute('data-placeholder', '状态');
    });

    it('应该渲染新建按钮', async () => {
      await renderOwnershipList();

      const buttons = screen.getAllByTestId('button');
      const createButton = buttons.find(btn => btn.textContent?.includes('新建权属方'));
      expect(createButton).toBeInTheDocument();
    });

    it('应该渲染刷新按钮', async () => {
      await renderOwnershipList();

      const buttons = screen.getAllByTestId('button');
      const refreshButton = buttons.find(btn => btn.textContent?.includes('刷新'));
      expect(refreshButton).toBeInTheDocument();
    });
  });

  describe('搜索功能', () => {
    it('应该能输入搜索关键字', async () => {
      await renderOwnershipList();

      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: '测试权属方' } });

      expect(mockApplyFilters).toHaveBeenCalledWith({
        keyword: '测试权属方',
        isActive: null,
      });
    });

    it('应该能点击搜索按钮', async () => {
      await renderOwnershipList();

      const searchButton = screen.getByTestId('search-button');
      fireEvent.click(searchButton);

      expect(searchButton).toBeInTheDocument();
    });

    it('应该能重置筛选条件', async () => {
      await renderOwnershipList();

      const buttons = screen.getAllByTestId('button');
      const resetButton = buttons.find(btn => btn.textContent === '重置');
      expect(resetButton).toBeInTheDocument();

      if (resetButton) {
        fireEvent.click(resetButton);
      }

      expect(mockResetFilters).toHaveBeenCalled();
    });
  });

  describe('表格渲染', () => {
    it('应该渲染表格组件', async () => {
      await renderOwnershipList();

      expect(screen.getByTestId('table')).toBeInTheDocument();
    });
  });

  describe('模态框交互', () => {
    it('点击新建按钮应该打开表单模态框', async () => {
      await renderOwnershipList();

      const buttons = screen.getAllByTestId('button');
      const createButton = buttons.find(btn => btn.textContent?.includes('新建权属方'));

      if (createButton) {
        fireEvent.click(createButton);
      }

      const modals = screen.getAllByTestId('modal');
      const formModal = modals.find(modal => modal.getAttribute('data-title') === '新建权属方');
      expect(formModal).toHaveAttribute('data-open', 'true');
    });

    it('应该能关闭模态框', async () => {
      await renderOwnershipList();

      // 打开模态框
      const buttons = screen.getAllByTestId('button');
      const createButton = buttons.find(btn => btn.textContent?.includes('新建权属方'));
      if (createButton) {
        fireEvent.click(createButton);
      }

      // 关闭模态框
      const closeButtons = screen.getAllByTestId('modal-close');
      if (closeButtons.length > 0) {
        fireEvent.click(closeButtons[0]);
      }

      const modals = screen.getAllByTestId('modal');
      const formModal = modals.find(modal => modal.getAttribute('data-title') === '新建权属方');
      expect(formModal).toHaveAttribute('data-open', 'false');
    });
  });

  describe('选择模式', () => {
    it('应该支持选择模式', async () => {
      const handleSelect = vi.fn();
      await renderOwnershipList({ mode: 'select', onSelectOwnership: handleSelect });

      expect(screen.getByTestId('table')).toBeInTheDocument();
    });

    it('列表模式不显示统计卡片', async () => {
      await renderOwnershipList({ mode: 'select' });

      const statistics = screen.queryAllByTestId('statistic');
      // 选择模式下不显示统计卡片
      expect(statistics.length).toBe(0);
    });
  });

  describe('刷新功能', () => {
    it('点击刷新按钮应该刷新列表', async () => {
      await renderOwnershipList();

      const buttons = screen.getAllByTestId('button');
      const refreshButton = buttons.find(btn => btn.textContent?.includes('刷新'));

      if (refreshButton) {
        await act(async () => {
          fireEvent.click(refreshButton);
          await flushPromises();
        });
      }

      expect(mockLoadList).toHaveBeenCalled();
      expect(ownershipService.getOwnershipStatistics).toHaveBeenCalled();
    });
  });

  it('初始化时会加载列表与统计信息', async () => {
    await renderOwnershipList();

    expect(mockLoadList).toHaveBeenCalled();
    expect(ownershipService.getOwnershipStatistics).toHaveBeenCalled();
  });
});
