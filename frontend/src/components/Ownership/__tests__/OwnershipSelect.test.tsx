/**
 * OwnershipSelect 组件测试
 *
 * 测试覆盖范围:
 * - 组件基本渲染
 * - 选择功能
 * - 搜索功能
 * - 多选模式
 * - 禁用状态
 * - 按钮功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';
import { useOwnershipOptions } from '@/hooks/useOwnership';

// Mock useOwnership hook
vi.mock('@/hooks/useOwnership', () => ({
  useOwnershipOptions: vi.fn(() => ({
    ownerships: [
      {
        id: '1',
        name: '权属方1',
        code: 'OWN-001',
        short_name: '权属1',
        is_active: true,
      },
      {
        id: '2',
        name: '权属方2',
        code: 'OWN-002',
        short_name: '权属2',
        is_active: true,
      },
      {
        id: '3',
        name: '权属方3',
        code: 'OWN-003',
        short_name: null,
        is_active: false,
      },
    ],
    loading: false,
    refresh: vi.fn(),
  })),
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

// Mock OwnershipList
vi.mock('../OwnershipList', () => ({
  default: (() => {
    const OwnershipList = ({
      mode,
      onSelectOwnership,
    }: {
      mode: string;
      onSelectOwnership: (ownership: { id: string; name: string }) => void;
    }) => (
      <div data-testid="ownership-list" data-mode={mode}>
        <button
          data-testid="select-ownership-btn"
          onClick={() => onSelectOwnership({ id: '1', name: '权属方1' })}
        >
          选择权属方1
        </button>
      </div>
    );
    OwnershipList.displayName = 'MockOwnershipList';
    return OwnershipList;
  })(),
}));

// Mock Ant Design
vi.mock('antd', () => {
  const Select = ({
    children,
    value,
    onChange,
    placeholder,
    disabled,
    allowClear,
    loading,
    showSearch,
    onSearch,
    mode,
    onClear,
  }: {
    children?: React.ReactNode;
    value?: string | string[];
    onChange?: (value: string | string[]) => void;
    placeholder?: string;
    disabled?: boolean;
    allowClear?: boolean;
    loading?: boolean;
    showSearch?: boolean;
    onSearch?: (value: string) => void;
    mode?: string;
    onClear?: () => void;
  }) => (
    <div
      data-testid="select"
      data-value={Array.isArray(value) ? value.join(',') : value}
      data-placeholder={placeholder}
      data-disabled={disabled}
      data-allow-clear={allowClear}
      data-loading={loading}
      data-show-search={showSearch}
      data-mode={mode}
    >
      <select
        data-testid="select-input"
        value={Array.isArray(value) ? value[0] : value || ''}
        onChange={e => {
          if (mode === 'multiple') {
            onChange?.([e.target.value]);
          } else {
            onChange?.(e.target.value);
          }
        }}
        disabled={disabled}
      >
        <option value="">{placeholder}</option>
        {children}
      </select>
      {showSearch && (
        <input
          data-testid="search-input"
          placeholder="搜索"
          onChange={e => onSearch?.(e.target.value)}
        />
      )}
      {allowClear && value && (
        <button data-testid="clear-btn" onClick={onClear}>
          清除
        </button>
      )}
    </div>
  );
  const Option = ({ children, value }: { children?: React.ReactNode; value?: string }) => (
    <option value={value}>{children}</option>
  );
  Option.displayName = 'MockSelectOption';

  Select.displayName = 'MockSelect';
  Select.Option = Option;

  const Button = ({
    children,
    onClick,
    icon,
    disabled,
    loading,
    size,
  }: {
    children?: React.ReactNode;
    onClick?: () => void;
    icon?: React.ReactNode;
    disabled?: boolean;
    loading?: boolean;
    size?: string;
  }) => (
    <button
      data-testid="button"
      data-disabled={disabled}
      data-loading={loading}
      data-size={size}
      onClick={onClick}
      disabled={disabled}
    >
      {icon}
      {children}
    </button>
  );
  Button.displayName = 'MockButton';

  const Modal = ({
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
  );
  Modal.displayName = 'MockModal';

  const SpaceCompact = ({
    children,
    style,
  }: {
    children?: React.ReactNode;
    style?: React.CSSProperties;
  }) => (
    <div data-testid="space-compact" style={style}>
      {children}
    </div>
  );
  SpaceCompact.displayName = 'MockSpaceCompact';

  const Tooltip = ({ children, title }: { children?: React.ReactNode; title?: string }) => (
    <div data-testid="tooltip" data-title={title}>
      {children}
    </div>
  );
  Tooltip.displayName = 'MockTooltip';

  const Tag = ({
    children,
    color,
    closable,
    onClose,
  }: {
    children?: React.ReactNode;
    color?: string;
    closable?: boolean;
    onClose?: () => void;
  }) => (
    <span data-testid="tag" data-color={color} data-closable={closable} onClick={onClose}>
      {children}
    </span>
  );
  Tag.displayName = 'MockTag';

  const Space = ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  );
  Space.displayName = 'MockSpace';
  Space.Compact = SpaceCompact;

  return {
    Select,
    Button,
    Modal,
    Space,
    Tooltip,
    Tag,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => {
  const PlusOutlined = () => <span data-testid="icon-plus">+</span>;
  const ReloadOutlined = () => <span data-testid="icon-reload">Reload</span>;
  const UnorderedListOutlined = () => <span data-testid="icon-list">List</span>;
  const SearchOutlined = () => <span data-testid="icon-search">Search</span>;

  PlusOutlined.displayName = 'PlusOutlined';
  ReloadOutlined.displayName = 'ReloadOutlined';
  UnorderedListOutlined.displayName = 'UnorderedListOutlined';
  SearchOutlined.displayName = 'SearchOutlined';

  return {
    PlusOutlined,
    ReloadOutlined,
    UnorderedListOutlined,
    SearchOutlined,
  };
});

import OwnershipSelect from '../OwnershipSelect';

describe('OwnershipSelect 组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染组件', () => {
      renderWithProviders(<OwnershipSelect />);

      expect(screen.getByTestId('select')).toBeInTheDocument();
    });

    it('应该显示默认占位符', () => {
      renderWithProviders(<OwnershipSelect />);

      const select = screen.getByTestId('select');
      expect(select).toHaveAttribute('data-placeholder', '请选择权属方');
    });

    it('应该支持自定义占位符', () => {
      renderWithProviders(<OwnershipSelect placeholder="自定义占位符" />);

      const select = screen.getByTestId('select');
      expect(select).toHaveAttribute('data-placeholder', '自定义占位符');
    });

    it('应该渲染 Space.Compact 容器', () => {
      renderWithProviders(<OwnershipSelect />);

      expect(screen.getByTestId('space-compact')).toBeInTheDocument();
    });
  });

  describe('value 属性', () => {
    it('应该接受 value 属性', () => {
      renderWithProviders(<OwnershipSelect value="1" />);

      const select = screen.getByTestId('select');
      expect(select).toHaveAttribute('data-value', '1');
    });

    it('多选模式应该接受数组 value', () => {
      renderWithProviders(<OwnershipSelect value={['1', '2']} mode="multiple" />);

      const select = screen.getByTestId('select');
      expect(select).toHaveAttribute('data-value', '1,2');
    });
  });

  describe('onChange 回调', () => {
    it('选择权属方应该触发 onChange', () => {
      const handleChange = vi.fn();
      renderWithProviders(<OwnershipSelect onChange={handleChange} />);

      const selectInput = screen.getByTestId('select-input');
      fireEvent.change(selectInput, { target: { value: '1' } });

      expect(handleChange).toHaveBeenCalled();
    });

    it('多选模式 onChange 应该返回数组', () => {
      const handleChange = vi.fn();
      renderWithProviders(<OwnershipSelect onChange={handleChange} mode="multiple" />);

      const selectInput = screen.getByTestId('select-input');
      fireEvent.change(selectInput, { target: { value: '1' } });

      expect(handleChange).toHaveBeenCalled();
    });
  });

  describe('disabled 状态', () => {
    it('disabled 时应该不可交互', () => {
      renderWithProviders(<OwnershipSelect disabled={true} />);

      const select = screen.getByTestId('select');
      expect(select).toHaveAttribute('data-disabled', 'true');
    });

    it('disabled 时 select 应该被禁用', () => {
      renderWithProviders(<OwnershipSelect disabled={true} />);

      const selectInput = screen.getByTestId('select-input');
      expect(selectInput).toBeDisabled();
    });

    it('disabled 时按钮应该被禁用', () => {
      renderWithProviders(<OwnershipSelect disabled={true} />);

      const buttons = screen.getAllByTestId('button');
      buttons.forEach(button => {
        expect(button).toBeDisabled();
      });
    });
  });

  describe('allowClear 属性', () => {
    it('allowClear 为 true 时应该显示清除功能', () => {
      renderWithProviders(<OwnershipSelect allowClear={true} value="1" />);

      const select = screen.getByTestId('select');
      expect(select).toHaveAttribute('data-allow-clear', 'true');
    });

    it('点击清除应该清空值', () => {
      const handleChange = vi.fn();
      renderWithProviders(<OwnershipSelect allowClear={true} value="1" onChange={handleChange} />);

      const clearBtn = screen.getByTestId('clear-btn');
      fireEvent.click(clearBtn);

      expect(handleChange).toHaveBeenCalled();
    });
  });

  describe('搜索功能', () => {
    it('showSearch 为 true 时应该支持搜索', () => {
      renderWithProviders(<OwnershipSelect showSearch={true} />);

      const select = screen.getByTestId('select');
      expect(select).toHaveAttribute('data-show-search', 'true');
    });

    it('应该能输入搜索文本', () => {
      renderWithProviders(<OwnershipSelect showSearch={true} />);

      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: '权属方1' } });

      expect(searchInput).toHaveValue('权属方1');
    });
  });

  describe('多选模式', () => {
    it('mode 为 multiple 时应该支持多选', () => {
      renderWithProviders(<OwnershipSelect mode="multiple" />);

      const select = screen.getByTestId('select');
      expect(select).toHaveAttribute('data-mode', 'multiple');
    });
  });

  describe('按钮功能', () => {
    it('应该显示搜索按钮', () => {
      renderWithProviders(<OwnershipSelect />);

      expect(screen.getByTestId('icon-search')).toBeInTheDocument();
    });

    it('showAdvancedSelect 为 true 时应该显示列表选择按钮', () => {
      renderWithProviders(<OwnershipSelect showAdvancedSelect={true} />);

      expect(screen.getByTestId('icon-list')).toBeInTheDocument();
    });

    it('showCreateButton 为 true 时应该显示创建按钮', () => {
      renderWithProviders(<OwnershipSelect showCreateButton={true} />);

      expect(screen.getByTestId('icon-plus')).toBeInTheDocument();
    });

    it('应该显示刷新按钮', () => {
      renderWithProviders(<OwnershipSelect />);

      expect(screen.getByTestId('icon-reload')).toBeInTheDocument();
    });

    it('点击刷新按钮应该刷新数据', () => {
      const mockRefresh = vi.fn();
      vi.mocked(useOwnershipOptions).mockReturnValue({
        ownerships: [],
        loading: false,
        refresh: mockRefresh,
      });

      renderWithProviders(<OwnershipSelect />);

      const buttons = screen.getAllByTestId('button');
      const refreshButton = buttons.find(btn => btn.querySelector('[data-testid="icon-reload"]'));

      if (refreshButton) {
        fireEvent.click(refreshButton);
      }

      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  describe('模态框交互', () => {
    it('点击搜索按钮应该打开选择弹窗', () => {
      renderWithProviders(<OwnershipSelect />);

      const buttons = screen.getAllByTestId('button');
      const searchButton = buttons.find(btn => btn.querySelector('[data-testid="icon-search"]'));

      if (searchButton) {
        fireEvent.click(searchButton);
      }

      const modal = screen.getByTestId('modal');
      expect(modal).toHaveAttribute('data-open', 'true');
    });

    it('应该能关闭选择弹窗', () => {
      renderWithProviders(<OwnershipSelect />);

      // 打开弹窗
      const buttons = screen.getAllByTestId('button');
      const searchButton = buttons.find(btn => btn.querySelector('[data-testid="icon-search"]'));
      if (searchButton) {
        fireEvent.click(searchButton);
      }

      // 关闭弹窗
      const closeButton = screen.getByTestId('modal-close');
      fireEvent.click(closeButton);

      const modal = screen.getByTestId('modal');
      expect(modal).toHaveAttribute('data-open', 'false');
    });

    it('从弹窗中选择权属方应该触发 onChange 并关闭弹窗', () => {
      const handleChange = vi.fn();
      renderWithProviders(<OwnershipSelect onChange={handleChange} />);

      // 打开弹窗
      const buttons = screen.getAllByTestId('button');
      const searchButton = buttons.find(btn => btn.querySelector('[data-testid="icon-search"]'));
      if (searchButton) {
        fireEvent.click(searchButton);
      }

      // 选择权属方
      const selectBtn = screen.getByTestId('select-ownership-btn');
      fireEvent.click(selectBtn);

      expect(handleChange).toHaveBeenCalled();

      const modal = screen.getByTestId('modal');
      expect(modal).toHaveAttribute('data-open', 'false');
    });
  });

  describe('loading 状态', () => {
    it('加载时应该显示 loading 状态', () => {
      vi.mocked(useOwnershipOptions).mockReturnValue({
        ownerships: [],
        loading: true,
        refresh: vi.fn(),
      });

      renderWithProviders(<OwnershipSelect />);

      const select = screen.getByTestId('select');
      expect(select).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('size 属性', () => {
    it('应该支持 large 尺寸', () => {
      renderWithProviders(<OwnershipSelect size="large" />);

      const buttons = screen.getAllByTestId('button');
      buttons.forEach(button => {
        expect(button).toHaveAttribute('data-size', 'large');
      });
    });

    it('应该支持 small 尺寸', () => {
      renderWithProviders(<OwnershipSelect size="small" />);

      const buttons = screen.getAllByTestId('button');
      buttons.forEach(button => {
        expect(button).toHaveAttribute('data-size', 'small');
      });
    });
  });
});
