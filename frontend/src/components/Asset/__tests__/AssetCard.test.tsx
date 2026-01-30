/**
 * AssetCard 组件测试
 * 测试资产卡片组件的渲染和交互
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { createMockAsset } from '@/test-utils/factories';

// Mock format utilities
vi.mock('@/utils/format', () => ({
  formatPercentage: (value: number) => `${value.toFixed(2)}%`,
  formatDate: (date: string) => date ? '2024-01-01' : '-',
  getStatusColor: (status: string, type: string) => {
    if (type === 'ownership') return 'blue';
    if (type === 'property') return 'green';
    if (type === 'usage') return 'cyan';
    return 'default';
  },
  calculateOccupancyRate: (rented: number, rentable: number) =>
    rentable > 0 ? (rented / rentable) * 100 : 0,
}));

// Mock colorMap
vi.mock('@/styles/colorMap', () => ({
  getOccupancyRateColor: (rate: number) => {
    if (rate >= 80) return '#52c41a';
    if (rate >= 60) return '#faad14';
    return '#ff4d4f';
  },
  COLORS: {
    primary: '#1890ff',
    border: '#d9d9d9',
    textTertiary: '#999',
  },
}));

// Mock Ant Design components
vi.mock('antd', () => {
  const Card = ({
    children,
    onClick,
    className,
    style,
    actions,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    className?: string;
    style?: React.CSSProperties;
    actions?: React.ReactNode[];
  }) => (
    <div
      data-testid="asset-card"
      className={className}
      style={style}
      onClick={onClick}
    >
      {children}
      {actions && (
        <div data-testid="card-actions">
          {actions.map((action, index) => (
            <span key={index}>{action}</span>
          ))}
        </div>
      )}
    </div>
  );
  Card.Meta = ({
    title,
    description,
  }: {
    title: React.ReactNode;
    description: React.ReactNode;
  }) => (
    <div data-testid="card-meta">
      <div data-testid="card-title">{title}</div>
      <div data-testid="card-description">{description}</div>
    </div>
  );

  return {
    Card,
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
    Button: ({
      children,
      onClick,
      danger,
      icon,
      type,
    }: {
      children?: React.ReactNode;
      onClick?: (e: React.MouseEvent) => void;
      danger?: boolean;
      icon?: React.ReactNode;
      type?: string;
    }) => (
      <button
        data-testid={danger ? 'btn-danger' : 'btn-normal'}
        data-type={type}
        onClick={onClick}
      >
        {icon}
        {children}
      </button>
    ),
    Space: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="space">{children}</div>
    ),
    Tooltip: ({
      children,
      title,
    }: {
      children: React.ReactNode;
      title: string;
    }) => (
      <div data-testid={`tooltip-${title}`} title={title}>
        {children}
      </div>
    ),
    Row: ({
      children,
      gutter,
    }: {
      children: React.ReactNode;
      gutter?: number;
    }) => (
      <div data-testid="row" data-gutter={gutter}>
        {children}
      </div>
    ),
    Col: ({
      children,
      span,
    }: {
      children: React.ReactNode;
      span?: number;
    }) => (
      <div data-testid="col" data-span={span}>
        {children}
      </div>
    ),
    Statistic: ({
      title,
      value,
      suffix,
    }: {
      title: string;
      value: number;
      suffix?: string;
    }) => (
      <div data-testid={`statistic-${title}`}>
        <span>{title}</span>
        <span data-testid="statistic-value">
          {value}
          {suffix}
        </span>
      </div>
    ),
    Progress: ({
      percent,
      strokeColor,
    }: {
      percent: number;
      strokeColor?: string;
    }) => (
      <div
        data-testid="progress"
        data-percent={percent}
        data-color={strokeColor}
        role="progressbar"
        aria-valuenow={percent}
      />
    ),
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  EditOutlined: () => <span data-testid="icon-edit">EditIcon</span>,
  DeleteOutlined: () => <span data-testid="icon-delete">DeleteIcon</span>,
  EyeOutlined: () => <span data-testid="icon-eye">EyeIcon</span>,
  HistoryOutlined: () => <span data-testid="icon-history">HistoryIcon</span>,
  EnvironmentOutlined: () => (
    <span data-testid="icon-environment">EnvIcon</span>
  ),
  UserOutlined: () => <span data-testid="icon-user">UserIcon</span>,
}));

import AssetCard from '../AssetCard';

describe('AssetCard', () => {
  const defaultProps = {
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onView: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('渲染测试', () => {
    it('应该正确渲染卡片', () => {
      const asset = createMockAsset({ property_name: '测试物业' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('asset-card')).toBeInTheDocument();
    });

    it('应该显示物业名称', () => {
      const asset = createMockAsset({ property_name: '测试物业A栋' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText('测试物业A栋')).toBeInTheDocument();
    });

    it('应该显示地址', () => {
      const asset = createMockAsset({ address: '深圳市南山区科技园' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText('深圳市南山区科技园')).toBeInTheDocument();
    });

    it('应该显示权属方', () => {
      const asset = createMockAsset({ ownership_entity: '测试集团有限公司' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText(/权属方：测试集团有限公司/)).toBeInTheDocument();
    });

    it('应该显示权属状态标签', () => {
      const asset = createMockAsset({ ownership_status: '自有' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText('自有')).toBeInTheDocument();
    });

    it('应该显示物业性质标签', () => {
      const asset = createMockAsset({ property_nature: '商业' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText('商业')).toBeInTheDocument();
    });

    it('应该显示使用状态标签', () => {
      const asset = createMockAsset({ usage_status: '在用' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText('在用')).toBeInTheDocument();
    });
  });

  describe('面积信息显示', () => {
    it('应该显示土地面积', () => {
      const asset = createMockAsset({ land_area: 1000 });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('statistic-土地面积')).toBeInTheDocument();
      expect(screen.getByText('1000㎡')).toBeInTheDocument();
    });

    it('应该显示实际面积', () => {
      const asset = createMockAsset({ actual_property_area: 800 });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('statistic-实际面积')).toBeInTheDocument();
    });

    it('应该显示可出租面积', () => {
      const asset = createMockAsset({ rentable_area: 600 });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('statistic-可出租面积')).toBeInTheDocument();
    });

    it('应该显示已出租面积', () => {
      const asset = createMockAsset({ rented_area: 300 });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('statistic-已出租面积')).toBeInTheDocument();
    });

    it('面积为0时应该显示0', () => {
      const asset = createMockAsset({
        land_area: 0,
        actual_property_area: 0,
        rentable_area: 0,
        rented_area: 0,
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      const values = screen.getAllByText('0㎡');
      expect(values.length).toBe(4);
    });
  });

  describe('出租率进度条', () => {
    it('rentable_area > 0 时应该显示进度条', () => {
      const asset = createMockAsset({ rentable_area: 100, rented_area: 50 });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('progress')).toBeInTheDocument();
    });

    it('rentable_area = 0 时不应该显示进度条', () => {
      const asset = createMockAsset({ rentable_area: 0 });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.queryByTestId('progress')).not.toBeInTheDocument();
    });

    it('出租率>=80%应该使用绿色', () => {
      const asset = createMockAsset({
        rentable_area: 100,
        rented_area: 90,
        occupancy_rate: 90,
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      const progress = screen.getByTestId('progress');
      expect(progress).toHaveAttribute('data-color', '#52c41a');
    });

    it('出租率>=60%应该使用黄色', () => {
      const asset = createMockAsset({
        rentable_area: 100,
        rented_area: 65,
        occupancy_rate: 65,
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      const progress = screen.getByTestId('progress');
      expect(progress).toHaveAttribute('data-color', '#faad14');
    });

    it('出租率<60%应该使用红色', () => {
      const asset = createMockAsset({
        rentable_area: 100,
        rented_area: 30,
        occupancy_rate: 30,
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      const progress = screen.getByTestId('progress');
      expect(progress).toHaveAttribute('data-color', '#ff4d4f');
    });

    it('应该显示出租率百分比', () => {
      const asset = createMockAsset({
        rentable_area: 100,
        rented_area: 75,
        occupancy_rate: 75,
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText('75.00%')).toBeInTheDocument();
    });
  });

  describe('条件渲染标签', () => {
    it('is_litigated为true时应该显示涉诉标签', () => {
      const asset = createMockAsset({ is_litigated: true });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText('涉诉')).toBeInTheDocument();
    });

    it('is_litigated为false时不应该显示涉诉标签', () => {
      const asset = createMockAsset({ is_litigated: false });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.queryByText('涉诉')).not.toBeInTheDocument();
    });

    it('有证载用途时应该显示证载用途标签', () => {
      const asset = createMockAsset({ certificated_usage: '商业' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText('证载：商业')).toBeInTheDocument();
    });

    it('证载用途为空时不应该显示证载用途标签', () => {
      const asset = createMockAsset({ certificated_usage: '' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.queryByText(/证载：/)).not.toBeInTheDocument();
    });

    it('实际用途与证载用途不同时应该显示实际用途标签', () => {
      const asset = createMockAsset({
        certificated_usage: '商业',
        actual_usage: '办公',
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText('实际：办公')).toBeInTheDocument();
    });

    it('实际用途与证载用途相同时不应该显示实际用途标签', () => {
      const asset = createMockAsset({
        certificated_usage: '商业',
        actual_usage: '商业',
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.queryByText(/实际：/)).not.toBeInTheDocument();
    });
  });

  describe('操作按钮', () => {
    it('应该渲染查看按钮', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('tooltip-查看详情')).toBeInTheDocument();
      expect(screen.getByTestId('icon-eye')).toBeInTheDocument();
    });

    it('应该渲染编辑按钮', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('tooltip-编辑')).toBeInTheDocument();
      expect(screen.getByTestId('icon-edit')).toBeInTheDocument();
    });

    it('应该渲染历史按钮', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('tooltip-查看历史')).toBeInTheDocument();
      expect(screen.getByTestId('icon-history')).toBeInTheDocument();
    });

    it('应该渲染删除按钮', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('tooltip-删除')).toBeInTheDocument();
      expect(screen.getByTestId('icon-delete')).toBeInTheDocument();
    });

    it('删除按钮应该是danger类型', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('btn-danger')).toBeInTheDocument();
    });
  });

  describe('点击事件', () => {
    it('点击查看按钮应该触发onView', () => {
      const handleView = vi.fn();
      const asset = createMockAsset({ id: 'test-id' });
      render(<AssetCard asset={asset} {...defaultProps} onView={handleView} />);

      const viewTooltip = screen.getByTestId('tooltip-查看详情');
      const viewButton = viewTooltip.querySelector('button');
      fireEvent.click(viewButton!);

      expect(handleView).toHaveBeenCalledWith(asset);
    });

    it('点击编辑按钮应该触发onEdit', () => {
      const handleEdit = vi.fn();
      const asset = createMockAsset({ id: 'test-id' });
      render(<AssetCard asset={asset} {...defaultProps} onEdit={handleEdit} />);

      const editTooltip = screen.getByTestId('tooltip-编辑');
      const editButton = editTooltip.querySelector('button');
      fireEvent.click(editButton!);

      expect(handleEdit).toHaveBeenCalledWith(asset);
    });

    it('点击删除按钮应该触发onDelete', () => {
      const handleDelete = vi.fn();
      const asset = createMockAsset({ id: 'test-id' });
      render(
        <AssetCard asset={asset} {...defaultProps} onDelete={handleDelete} />
      );

      const deleteButton = screen.getByTestId('btn-danger');
      fireEvent.click(deleteButton);

      expect(handleDelete).toHaveBeenCalledWith('test-id');
    });

    it('点击卡片应该触发onSelect', () => {
      const handleSelect = vi.fn();
      const asset = createMockAsset({ id: 'test-id' });
      render(
        <AssetCard asset={asset} {...defaultProps} onSelect={handleSelect} />
      );

      const card = screen.getByTestId('asset-card');
      fireEvent.click(card);

      expect(handleSelect).toHaveBeenCalledWith(asset, true);
    });

    it('已选中状态下点击卡片应该取消选中', () => {
      const handleSelect = vi.fn();
      const asset = createMockAsset({ id: 'test-id' });
      render(
        <AssetCard
          asset={asset}
          {...defaultProps}
          selected={true}
          onSelect={handleSelect}
        />
      );

      const card = screen.getByTestId('asset-card');
      fireEvent.click(card);

      expect(handleSelect).toHaveBeenCalledWith(asset, false);
    });

    it('操作按钮点击应该阻止冒泡', () => {
      const handleSelect = vi.fn();
      const handleView = vi.fn();
      const asset = createMockAsset();
      render(
        <AssetCard
          asset={asset}
          {...defaultProps}
          onView={handleView}
          onSelect={handleSelect}
        />
      );

      const viewTooltip = screen.getByTestId('tooltip-查看详情');
      const viewButton = viewTooltip.querySelector('button');
      fireEvent.click(viewButton!);

      expect(handleView).toHaveBeenCalled();
      // onSelect should not be called because stopPropagation
    });
  });

  describe('选中状态', () => {
    it('selected为true时应该有selected类名', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} selected={true} />);

      const card = screen.getByTestId('asset-card');
      expect(card).toHaveClass('selected');
    });

    it('selected为false时不应该有selected类名', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} selected={false} />);

      const card = screen.getByTestId('asset-card');
      expect(card).not.toHaveClass('selected');
    });

    it('默认selected应该是false', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      const card = screen.getByTestId('asset-card');
      expect(card).not.toHaveClass('selected');
    });
  });

  describe('图标渲染', () => {
    it('地址应该有EnvironmentOutlined图标', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('icon-environment')).toBeInTheDocument();
    });

    it('权属方应该有UserOutlined图标', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('icon-user')).toBeInTheDocument();
    });
  });

  describe('时间信息', () => {
    it('应该显示创建时间', () => {
      const asset = createMockAsset({ created_at: '2024-01-01T00:00:00.000Z' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText(/创建时间：/)).toBeInTheDocument();
    });

    it('应该显示更新时间', () => {
      const asset = createMockAsset({ updated_at: '2024-01-01T00:00:00.000Z' });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByText(/更新时间：/)).toBeInTheDocument();
    });
  });

  describe('边界情况', () => {
    it('应该处理空字符串属性', () => {
      const asset = createMockAsset({
        property_name: '',
        address: '',
        ownership_entity: '',
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      expect(screen.getByTestId('asset-card')).toBeInTheDocument();
    });

    it('应该处理undefined的occupancy_rate', () => {
      const asset = createMockAsset({
        rented_area: 300,
        rentable_area: 600,
        occupancy_rate: undefined,
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      // 应该使用 calculateOccupancyRate 计算
      expect(screen.getByTestId('progress')).toBeInTheDocument();
    });

    it('应该处理null面积值', () => {
      const asset = createMockAsset({
        land_area: null as unknown as number,
        actual_property_area: null as unknown as number,
      });
      render(<AssetCard asset={asset} {...defaultProps} />);

      // 应该显示0
      expect(screen.getByTestId('asset-card')).toBeInTheDocument();
    });
  });

  describe('布局验证', () => {
    it('面积统计应该使用4列布局', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      const cols = screen.getAllByTestId('col');
      expect(cols.length).toBe(4);
    });

    it('每列应该是span=6', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      const cols = screen.getAllByTestId('col');
      cols.forEach(col => {
        expect(col).toHaveAttribute('data-span', '6');
      });
    });

    it('应该有16的gutter', () => {
      const asset = createMockAsset();
      render(<AssetCard asset={asset} {...defaultProps} />);

      const row = screen.getByTestId('row');
      expect(row).toHaveAttribute('data-gutter', '16');
    });
  });
});
