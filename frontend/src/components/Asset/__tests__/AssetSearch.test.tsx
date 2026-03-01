/**
 * AssetSearch 组件测试
 * 测试资产搜索表单的渲染和交互
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';

// Mock dependencies before imports
vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

vi.mock('@/services/assetService', () => ({
  assetService: {
    getBusinessCategories: vi.fn(() => Promise.resolve(['办公', '商业', '工业'])),
  },
}));

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnershipSelectOptions: vi.fn(() =>
      Promise.resolve([
        { value: 'own-1', label: '政府' },
        { value: 'own-2', label: '企业' },
      ])
    ),
  },
}));

vi.mock('@/hooks/useSearchHistory', () => ({
  useSearchHistory: () => ({
    searchHistory: [
      {
        id: '1',
        name: '我的搜索',
        conditions: { ownership_status: '已确权' },
        createdAt: '2024-01-01T00:00:00.000Z',
      },
    ],
    addSearchHistory: vi.fn(),
    removeSearchHistory: vi.fn(),
    clearSearchHistory: vi.fn(),
    updateSearchHistoryName: vi.fn(),
  }),
}));

vi.mock('@tanstack/react-query', () => ({
  useQueries: () => [
    {
      data: [
        { value: 'own-1', label: '政府' },
        { value: 'own-2', label: '企业' },
      ],
      isLoading: false,
    },
    { data: ['办公', '商业', '工业'], isLoading: false },
  ],
}));

// Mock Form.useForm
const mockFormInstance = {
  getFieldsValue: vi.fn(() => ({})),
  setFieldsValue: vi.fn(),
  resetFields: vi.fn(),
  getFieldValue: vi.fn(),
};

// Mock Ant Design
vi.mock('antd', () => {
  const Card = ({
    children,
    title,
    extra,
  }: {
    children: React.ReactNode;
    title?: React.ReactNode;
    extra?: React.ReactNode;
  }) => (
    <div data-testid="search-card">
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      {children}
    </div>
  );
  Card.displayName = 'MockCard';

  const Form = ({ children, disabled }: { children: React.ReactNode; disabled?: boolean }) => (
    <form data-testid="search-form" data-disabled={disabled}>
      {children}
    </form>
  );
  Form.displayName = 'MockForm';

  const FormItem = ({
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
  FormItem.displayName = 'MockFormItem';

  Form.Item = FormItem;
  Form.useForm = () => [mockFormInstance];

  const Select = ({
    children,
    placeholder,
    loading,
    onChange,
  }: {
    children?: React.ReactNode;
    placeholder?: string;
    loading?: boolean;
    onChange?: (value: string) => void;
  }) => (
    <select
      data-testid="select"
      data-placeholder={placeholder}
      data-loading={loading}
      onChange={e => onChange?.(e.target.value)}
    >
      <option value="">{placeholder}</option>
      {children}
    </select>
  );
  Select.displayName = 'MockSelect';

  const Option = ({ children, value }: { children: React.ReactNode; value: string }) => (
    <option value={value}>{children}</option>
  );
  Option.displayName = 'MockSelectOption';

  Select.Option = Option;

  const Input = ({
    placeholder,
    prefix,
    allowClear,
    value,
    onChange,
    onBlur,
    onPressEnter,
  }: {
    placeholder?: string;
    prefix?: React.ReactNode;
    allowClear?: boolean;
    value?: string;
    onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onBlur?: () => void;
    onPressEnter?: () => void;
  }) => (
    <div data-testid="input-wrapper">
      {prefix}
      <input
        data-testid="input"
        placeholder={placeholder}
        data-allow-clear={allowClear}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        onKeyDown={event => {
          if (event.key === 'Enter') {
            onPressEnter?.();
          }
        }}
      />
    </div>
  );
  Input.displayName = 'MockInput';

  const RangePicker = ({ format }: { format?: string }) => (
    <div data-testid="range-picker" data-format={format}>
      <input data-testid="date-start" />
      <input data-testid="date-end" />
    </div>
  );
  RangePicker.displayName = 'MockRangePicker';

  const DatePicker = {
    RangePicker,
  };

  const InputNumber = ({
    placeholder,
    value,
    onChange,
  }: {
    placeholder?: string;
    value?: number;
    onChange?: (value: number | null) => void;
  }) => (
    <input
      data-testid="input-number"
      type="number"
      placeholder={placeholder}
      value={value}
      onChange={e => onChange?.(parseFloat(e.target.value) || null)}
    />
  );
  InputNumber.displayName = 'MockInputNumber';

  const Button = ({
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
  );
  Button.displayName = 'MockButton';

  const Space = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  );
  Space.displayName = 'MockSpace';
  const SpaceCompact = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="space-compact">{children}</div>
  );
  SpaceCompact.displayName = 'MockSpaceCompact';
  Space.Compact = SpaceCompact;

  const Row = ({ children, gutter }: { children: React.ReactNode; gutter?: number }) => (
    <div data-testid="row" data-gutter={gutter}>
      {children}
    </div>
  );
  Row.displayName = 'MockRow';

  const Col = ({
    children,
    xs,
    sm,
    md,
    lg,
  }: {
    children: React.ReactNode;
    xs?: number;
    sm?: number;
    md?: number;
    lg?: number;
  }) => (
    <div data-testid="col" data-xs={xs} data-sm={sm} data-md={md} data-lg={lg}>
      {children}
    </div>
  );
  Col.displayName = 'MockCol';

  const Modal = ({
    children,
    open,
    title,
    onOk,
    onCancel,
  }: {
    children: React.ReactNode;
    open?: boolean;
    title?: string;
    onOk?: () => void;
    onCancel?: () => void;
  }) =>
    open ? (
      <div data-testid="modal" data-title={title}>
        <div data-testid="modal-title">{title}</div>
        <div data-testid="modal-content">{children}</div>
        <button data-testid="modal-ok" onClick={onOk}>
          确定
        </button>
        <button data-testid="modal-cancel" onClick={onCancel}>
          取消
        </button>
      </div>
    ) : null;
  Modal.displayName = 'MockModal';

  const List = ({
    dataSource,
    renderItem,
    locale,
  }: {
    dataSource: Array<{ id: string; name: string }>;
    renderItem: (item: { id: string; name: string }) => React.ReactNode;
    locale?: { emptyText: string };
  }) => (
    <div data-testid="list">
      {dataSource.length === 0 ? (
        <div data-testid="list-empty">{locale?.emptyText}</div>
      ) : (
        dataSource.map(item => <div key={item.id}>{renderItem(item)}</div>)
      )}
    </div>
  );
  List.displayName = 'MockList';
  const ListItem = ({
    children,
    actions,
  }: {
    children: React.ReactNode;
    actions?: React.ReactNode[];
  }) => (
    <div data-testid="list-item">
      <div data-testid="list-item-content">{children}</div>
      {actions && <div data-testid="list-item-actions">{actions}</div>}
    </div>
  );
  ListItem.displayName = 'MockListItem';

  const ListItemMeta = ({
    title,
    description,
  }: {
    title?: React.ReactNode;
    description?: React.ReactNode;
  }) => (
    <div data-testid="list-item-meta">
      {title && <div data-testid="list-item-meta-title">{title}</div>}
      {description && <div data-testid="list-item-meta-description">{description}</div>}
    </div>
  );
  ListItemMeta.displayName = 'MockListItemMeta';

  List.Item = ListItem;
  List.Item.Meta = ListItemMeta;

  const TypographyText = ({ children }: { children: React.ReactNode }) => (
    <span data-testid="text">{children}</span>
  );
  TypographyText.displayName = 'MockTypographyText';

  const Popconfirm = ({
    children,
    title,
    onConfirm,
  }: {
    children: React.ReactNode;
    title: string;
    onConfirm?: () => void;
  }) => (
    <div data-testid="popconfirm" data-title={title} onClick={onConfirm}>
      {children}
    </div>
  );
  Popconfirm.displayName = 'MockPopconfirm';

  const Tag = ({ children, color }: { children: React.ReactNode; color?: string }) => (
    <span data-testid="tag" data-color={color}>
      {children}
    </span>
  );
  Tag.displayName = 'MockTag';

  return {
    Card,
    Form,
    Input,
    Select,
    DatePicker,
    InputNumber,
    Button,
    Space,
    Row,
    Col,
    Modal,
    List,
    Typography: {
      Text: TypographyText,
    },
    Popconfirm,
    Tag,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => {
  const SearchOutlined = () => <span data-testid="icon-search">SearchIcon</span>;
  const ReloadOutlined = () => <span data-testid="icon-reload">ReloadIcon</span>;
  const DownOutlined = () => <span data-testid="icon-down">DownIcon</span>;
  const UpOutlined = () => <span data-testid="icon-up">UpIcon</span>;
  const SaveOutlined = () => <span data-testid="icon-save">SaveIcon</span>;
  const HistoryOutlined = () => <span data-testid="icon-history">HistoryIcon</span>;

  SearchOutlined.displayName = 'SearchOutlined';
  ReloadOutlined.displayName = 'ReloadOutlined';
  DownOutlined.displayName = 'DownOutlined';
  UpOutlined.displayName = 'UpOutlined';
  SaveOutlined.displayName = 'SaveOutlined';
  HistoryOutlined.displayName = 'HistoryOutlined';

  return {
    SearchOutlined,
    ReloadOutlined,
    DownOutlined,
    UpOutlined,
    SaveOutlined,
    HistoryOutlined,
  };
});

import AssetSearch from '../AssetSearch';
import { MessageManager } from '@/utils/messageManager';

describe('AssetSearch', () => {
  const defaultProps = {
    onSearch: vi.fn(),
    onReset: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockFormInstance.getFieldsValue.mockReturnValue({});
  });

  describe('基本渲染', () => {
    it('应该正确渲染搜索卡片', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByTestId('search-card')).toBeInTheDocument();
    });

    it('应该显示资产搜索标题', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByText('资产搜索')).toBeInTheDocument();
    });

    it('应该显示搜索表单', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByTestId('search-form')).toBeInTheDocument();
    });

    it('应该显示搜索图标', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getAllByTestId('icon-search').length).toBeGreaterThan(0);
    });
  });

  describe('搜索字段', () => {
    it('应该显示关键词搜索输入框', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByTestId('form-item-search')).toBeInTheDocument();
    });

    it('应该显示确权状态下拉框', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByTestId('form-item-ownership_status')).toBeInTheDocument();
    });

    it('应该显示物业性质下拉框', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByTestId('form-item-property_nature')).toBeInTheDocument();
    });

    it('应该显示使用状态下拉框', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByTestId('form-item-usage_status')).toBeInTheDocument();
    });
  });

  describe('操作按钮', () => {
    it('应该显示搜索按钮', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByText('搜索')).toBeInTheDocument();
    });

    it('应该显示重置按钮', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByText('重置')).toBeInTheDocument();
    });

    it('应该显示保存条件按钮', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showSaveButton={true} />);

      expect(screen.getByText('保存条件')).toBeInTheDocument();
    });

    it('应该显示搜索历史按钮', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showHistoryButton={true} />);

      expect(screen.getByText('搜索历史')).toBeInTheDocument();
    });

    it('应该显示展开/收起按钮', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByText('展开')).toBeInTheDocument();
    });

    it('搜索按钮应该是primary类型', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByTestId('btn-primary')).toBeInTheDocument();
    });
  });

  describe('点击事件', () => {
    it('点击搜索按钮应该触发onSearch', () => {
      const handleSearch = vi.fn();
      renderWithProviders(<AssetSearch {...defaultProps} onSearch={handleSearch} />);

      const searchButton = screen.getByText('搜索');
      fireEvent.click(searchButton);

      expect(handleSearch).toHaveBeenCalled();
    });

    it('点击重置按钮应该触发onReset', () => {
      const handleReset = vi.fn();
      renderWithProviders(<AssetSearch {...defaultProps} onReset={handleReset} />);

      const resetButton = screen.getByText('重置');
      fireEvent.click(resetButton);

      expect(handleReset).toHaveBeenCalled();
    });

    it('点击重置按钮应该重置表单', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      const resetButton = screen.getByText('重置');
      fireEvent.click(resetButton);

      expect(mockFormInstance.resetFields).toHaveBeenCalled();
    });

    it('点击展开按钮应该切换状态', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      // 初始状态显示"展开"
      expect(screen.getByText('展开')).toBeInTheDocument();

      // 点击展开
      const expandButton = screen.getByText('展开');
      fireEvent.click(expandButton);

      // 应该显示"收起"
      expect(screen.getByText('收起')).toBeInTheDocument();
    });
  });

  describe('展开/收起高级搜索', () => {
    it('默认不显示高级搜索字段', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      // 高级字段不应该显示
      expect(screen.queryByTestId('form-item-owner_party_id')).not.toBeInTheDocument();
    });

    it('展开后应该显示高级搜索字段', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      // 点击展开
      const expandButton = screen.getByText('展开');
      fireEvent.click(expandButton);

      // 高级字段应该显示
      expect(screen.getByTestId('form-item-owner_party_id')).toBeInTheDocument();
      expect(screen.getByTestId('form-item-business_category')).toBeInTheDocument();
      expect(screen.getByTestId('form-item-is_litigated')).toBeInTheDocument();
    });

    it('展开后应该显示日期范围选择器', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      fireEvent.click(screen.getByText('展开'));

      expect(screen.getByTestId('range-picker')).toBeInTheDocument();
    });

    it('展开后应该显示面积范围输入', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      fireEvent.click(screen.getByText('展开'));

      expect(screen.getByText('面积范围')).toBeInTheDocument();
    });

    it('展开后应该显示排序方式', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      fireEvent.click(screen.getByText('展开'));

      expect(screen.getByText('排序方式')).toBeInTheDocument();
    });
  });

  describe('保存搜索条件', () => {
    it('点击保存按钮应该打开保存弹窗', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showSaveButton={true} />);

      fireEvent.click(screen.getByText('保存条件'));

      expect(screen.getByTestId('modal')).toBeInTheDocument();
      expect(screen.getByText('保存搜索条件')).toBeInTheDocument();
    });

    it('没有搜索条件时保存应该提示警告', () => {
      mockFormInstance.getFieldsValue.mockReturnValue({});
      renderWithProviders(<AssetSearch {...defaultProps} showSaveButton={true} />);

      fireEvent.click(screen.getByText('保存条件'));
      fireEvent.click(screen.getByTestId('modal-ok'));

      expect(MessageManager.warning).toHaveBeenCalledWith('请先设置搜索条件');
    });

    it('点击取消应该关闭保存弹窗', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showSaveButton={true} />);

      fireEvent.click(screen.getByText('保存条件'));
      expect(screen.getByTestId('modal')).toBeInTheDocument();

      fireEvent.click(screen.getByTestId('modal-cancel'));
      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
    });
  });

  describe('搜索历史', () => {
    it('点击历史按钮应该打开历史弹窗', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showHistoryButton={true} />);

      fireEvent.click(screen.getByText('搜索历史'));

      expect(screen.getByTestId('modal')).toBeInTheDocument();
      expect(screen.getByTestId('modal-title')).toHaveTextContent('搜索历史');
    });

    it('历史弹窗应该显示历史列表', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showHistoryButton={true} />);

      fireEvent.click(screen.getByText('搜索历史'));

      expect(screen.getByTestId('list')).toBeInTheDocument();
    });
  });

  describe('loading状态', () => {
    it('loading时搜索按钮应该显示loading状态', () => {
      renderWithProviders(<AssetSearch {...defaultProps} loading={true} />);

      const searchButton = screen.getByTestId('btn-primary');
      expect(searchButton).toHaveAttribute('data-loading', 'true');
    });

    it('loading时重置按钮应该禁用', () => {
      renderWithProviders(<AssetSearch {...defaultProps} loading={true} />);

      const resetButton = screen.getByText('重置').closest('button');
      expect(resetButton).toBeDisabled();
    });

    it('loading时保存按钮应该禁用', () => {
      renderWithProviders(<AssetSearch {...defaultProps} loading={true} showSaveButton={true} />);

      const saveButton = screen.getByText('保存条件').closest('button');
      expect(saveButton).toBeDisabled();
    });

    it('loading时应该显示加载中标签', () => {
      renderWithProviders(<AssetSearch {...defaultProps} loading={true} />);

      expect(screen.getByText('加载中…')).toBeInTheDocument();
    });
  });

  describe('初始值', () => {
    it('应该接受initialValues属性', () => {
      const initialValues = { search: '测试' };
      renderWithProviders(<AssetSearch {...defaultProps} initialValues={initialValues} />);

      expect(mockFormInstance.setFieldsValue).toHaveBeenCalled();
    });

    it('空initialValues不应该调用setFieldsValue', () => {
      renderWithProviders(<AssetSearch {...defaultProps} initialValues={{}} />);

      expect(mockFormInstance.setFieldsValue).not.toHaveBeenCalled();
    });
  });

  describe('可选按钮显示', () => {
    it('showSaveButton为false时不显示保存按钮', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showSaveButton={false} />);

      expect(screen.queryByText('保存条件')).not.toBeInTheDocument();
    });

    it('showHistoryButton为false时不显示历史按钮', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showHistoryButton={false} />);

      expect(screen.queryByText('搜索历史')).not.toBeInTheDocument();
    });

    it('默认显示保存和历史按钮', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByText('保存条件')).toBeInTheDocument();
      expect(screen.getByText('搜索历史')).toBeInTheDocument();
    });
  });

  describe('图标渲染', () => {
    it('应该显示搜索图标', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getAllByTestId('icon-search').length).toBeGreaterThan(0);
    });

    it('应该显示重置图标', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByTestId('icon-reload')).toBeInTheDocument();
    });

    it('应该显示保存图标', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showSaveButton={true} />);

      expect(screen.getByTestId('icon-save')).toBeInTheDocument();
    });

    it('应该显示历史图标', () => {
      renderWithProviders(<AssetSearch {...defaultProps} showHistoryButton={true} />);

      expect(screen.getByTestId('icon-history')).toBeInTheDocument();
    });

    it('初始应该显示展开图标', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByTestId('icon-down')).toBeInTheDocument();
    });

    it('展开后应该显示收起图标', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      fireEvent.click(screen.getByText('展开'));

      expect(screen.getByTestId('icon-up')).toBeInTheDocument();
    });
  });

  describe('布局验证', () => {
    it('应该使用Row和Col布局', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getAllByTestId('row').length).toBeGreaterThan(0);
      expect(screen.getAllByTestId('col').length).toBeGreaterThan(0);
    });

    it('应该使用Space组件', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getAllByTestId('space').length).toBeGreaterThan(0);
    });
  });

  describe('下拉选项', () => {
    it('确权状态应该有正确的选项', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByText('已确权')).toBeInTheDocument();
      expect(screen.getByText('未确权')).toBeInTheDocument();
    });

    it('物业性质应该有正确的选项', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByText('经营性')).toBeInTheDocument();
      expect(screen.getByText('非经营性')).toBeInTheDocument();
    });

    it('使用状态应该有正确的选项', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      expect(screen.getByText('出租')).toBeInTheDocument();
      expect(screen.getByText('空置')).toBeInTheDocument();
      expect(screen.getByText('自用')).toBeInTheDocument();
    });
  });

  describe('表单验证', () => {
    it('表单应该使用垂直布局', () => {
      renderWithProviders(<AssetSearch {...defaultProps} />);

      const form = screen.getByTestId('search-form');
      expect(form).toBeInTheDocument();
    });
  });
});
