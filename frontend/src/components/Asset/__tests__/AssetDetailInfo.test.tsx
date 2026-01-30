/**
 * AssetDetailInfo 组件测试
 * 测试资产详情信息展示
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { createMockAsset } from '@/test-utils/factories';

// Mock format utilities
vi.mock('@/utils/format', () => ({
  formatDate: (date: string, format?: string) =>
    date ? (format === 'datetime' ? '2024-01-01 12:00' : '2024-01-01') : '-',
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
    success: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f',
    textTertiary: '#999',
  },
}));

// Mock Ant Design components
vi.mock('antd', () => {
  const Card = ({
    children,
    title,
    extra,
    style,
  }: {
    children: React.ReactNode;
    title?: React.ReactNode;
    extra?: React.ReactNode;
    style?: React.CSSProperties;
  }) => (
    <div data-testid="card" style={style}>
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      {children}
    </div>
  );

  const Descriptions = ({
    children,
    bordered,
    column,
  }: {
    children: React.ReactNode;
    bordered?: boolean;
    column?: number | object;
  }) => (
    <div
      data-testid="descriptions"
      data-bordered={bordered}
      data-column={typeof column === 'object' ? JSON.stringify(column) : column}
    >
      {children}
    </div>
  );

  Descriptions.Item = ({
    children,
    label,
    span,
  }: {
    children: React.ReactNode;
    label?: React.ReactNode;
    span?: number;
  }) => (
    <div data-testid="descriptions-item" data-span={span}>
      <span data-testid="item-label">{label}</span>
      <span data-testid="item-content">{children}</span>
    </div>
  );

  return {
    Card,
    Descriptions,
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
      />
    ),
    Row: ({ children, gutter }: { children: React.ReactNode; gutter?: number }) => (
      <div data-testid="row" data-gutter={gutter}>
        {children}
      </div>
    ),
    Col: ({
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
    ),
    Statistic: ({
      title,
      value,
      suffix,
      valueStyle,
    }: {
      title: string;
      value: number;
      suffix?: string;
      valueStyle?: React.CSSProperties;
    }) => (
      <div data-testid={`statistic-${title}`} style={valueStyle}>
        <span>{title}</span>
        <span data-testid="statistic-value">
          {value}
          {suffix}
        </span>
      </div>
    ),
    Divider: ({
      children,
      titlePlacement,
    }: {
      children: React.ReactNode;
      titlePlacement?: string;
    }) => (
      <div data-testid="divider" data-placement={titlePlacement}>
        {children}
      </div>
    ),
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  HomeOutlined: () => <span data-testid="icon-home">HomeIcon</span>,
  EnvironmentOutlined: () => <span data-testid="icon-environment">EnvIcon</span>,
  UserOutlined: () => <span data-testid="icon-user">UserIcon</span>,
  CalendarOutlined: () => <span data-testid="icon-calendar">CalendarIcon</span>,
  PercentageOutlined: () => <span data-testid="icon-percentage">PercentIcon</span>,
  InfoCircleOutlined: () => <span data-testid="icon-info">InfoIcon</span>,
}));

import AssetDetailInfo from '../AssetDetailInfo';

describe('AssetDetailInfo', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染组件', () => {
      const asset = createMockAsset({ property_name: '测试物业' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('应该显示基本信息卡片标题', () => {
      const asset = createMockAsset();
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('基本信息')).toBeInTheDocument();
    });

    it('应该显示面积信息卡片', () => {
      const asset = createMockAsset();
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('面积信息')).toBeInTheDocument();
    });

    it('应该显示接收信息卡片', () => {
      const asset = createMockAsset();
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('接收信息')).toBeInTheDocument();
    });
  });

  describe('基本信息显示', () => {
    it('应该显示物业名称', () => {
      const asset = createMockAsset({ property_name: '测试物业A栋' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('测试物业A栋')).toBeInTheDocument();
    });

    it('应该显示项目名称', () => {
      const asset = createMockAsset({ project_name: '测试项目' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('测试项目')).toBeInTheDocument();
    });

    it('应该显示权属方', () => {
      const asset = createMockAsset({ ownership_entity: '测试集团有限公司' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('测试集团有限公司')).toBeInTheDocument();
    });

    it('应该显示地址', () => {
      const asset = createMockAsset({ address: '深圳市南山区科技园' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('深圳市南山区科技园')).toBeInTheDocument();
    });

    it('应该显示确权状态标签', () => {
      const asset = createMockAsset({ ownership_status: '已确权' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('已确权')).toBeInTheDocument();
    });

    it('应该显示使用状态标签', () => {
      const asset = createMockAsset({ usage_status: '出租' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('出租')).toBeInTheDocument();
    });

    it('应该显示物业性质标签', () => {
      const asset = createMockAsset({ property_nature: '经营性' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('经营性')).toBeInTheDocument();
    });

    it('应该显示是否涉诉', () => {
      const asset = createMockAsset({ is_litigated: true });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('是')).toBeInTheDocument();
    });
  });

  describe('面积信息显示', () => {
    it('应该显示土地面积', () => {
      const asset = createMockAsset({ land_area: 1000 });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-土地面积')).toBeInTheDocument();
    });

    it('应该显示实际房产面积', () => {
      const asset = createMockAsset({ actual_property_area: 800 });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-实际房产面积')).toBeInTheDocument();
    });

    it('经营性资产应该显示可出租面积', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rentable_area: 600,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-可出租面积')).toBeInTheDocument();
    });

    it('经营性资产应该显示已出租面积', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rented_area: 300,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-已出租面积')).toBeInTheDocument();
    });

    it('经营性资产应该显示未出租面积', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        unrented_area: 100,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-未出租面积')).toBeInTheDocument();
    });

    it('非经营性资产不应该显示出租面积', () => {
      const asset = createMockAsset({
        property_nature: '非经营性',
        rentable_area: 600,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByTestId('statistic-可出租面积')).not.toBeInTheDocument();
    });
  });

  describe('出租率显示', () => {
    it('经营性资产应该显示出租率', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rentable_area: 100,
        rented_area: 80,
        occupancy_rate: 80,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText(/出租率/)).toBeInTheDocument();
    });

    it('有可出租面积时应该显示进度条', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rentable_area: 100,
        rented_area: 80,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('progress')).toBeInTheDocument();
    });

    it('rentable_area为0时不应该显示进度条', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rentable_area: 0,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByTestId('progress')).not.toBeInTheDocument();
    });
  });

  describe('接收信息显示', () => {
    it('应该显示接收模式', () => {
      const asset = createMockAsset({ business_model: '委托经营' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('委托经营')).toBeInTheDocument();
    });

    it('应该显示是否计入出租率', () => {
      const asset = createMockAsset({ include_in_occupancy_rate: true });
      render(<AssetDetailInfo asset={asset} />);

      // 检查标签存在
      const tags = screen.getAllByTestId('tag');
      const includeTag = tags.find(tag => tag.textContent === '是');
      expect(includeTag).toBeInTheDocument();
    });

    it('应该显示权属类别', () => {
      const asset = createMockAsset({ ownership_category: '自有物业' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('自有物业')).toBeInTheDocument();
    });
  });

  describe('合同信息显示', () => {
    it('出租状态应该显示合同信息卡片', () => {
      const asset = createMockAsset({
        usage_status: '出租',
        tenant_name: '租户A',
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('合同信息')).toBeInTheDocument();
    });

    it('应该显示租户名称', () => {
      const asset = createMockAsset({
        usage_status: '出租',
        tenant_name: '测试租户公司',
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('测试租户公司')).toBeInTheDocument();
    });

    it('应该显示租赁合同编号', () => {
      const asset = createMockAsset({
        usage_status: '出租',
        lease_contract_number: 'LC-2024-001',
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('LC-2024-001')).toBeInTheDocument();
    });

    it('非出租状态不应该显示合同信息卡片', () => {
      const asset = createMockAsset({ usage_status: '空置' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByText('合同信息')).not.toBeInTheDocument();
    });
  });

  describe('备注信息显示', () => {
    it('有备注时应该显示备注卡片', () => {
      const asset = createMockAsset({ notes: '这是备注内容' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('备注信息')).toBeInTheDocument();
      expect(screen.getByText('这是备注内容')).toBeInTheDocument();
    });

    it('无备注时不应该显示备注卡片', () => {
      const asset = createMockAsset({ notes: '' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByText('备注信息')).not.toBeInTheDocument();
    });

    it('备注为undefined时不应该显示备注卡片', () => {
      const asset = createMockAsset({ notes: undefined });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByText('备注信息')).not.toBeInTheDocument();
    });
  });

  describe('图标显示', () => {
    it('应该显示基本信息图标', () => {
      const asset = createMockAsset();
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('icon-info')).toBeInTheDocument();
    });

    it('应该显示位置图标', () => {
      const asset = createMockAsset();
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('icon-environment')).toBeInTheDocument();
    });

    it('应该显示用户图标', () => {
      const asset = createMockAsset();
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('icon-user')).toBeInTheDocument();
    });
  });

  describe('空值处理', () => {
    it('应该处理缺失的物业名称', () => {
      const asset = createMockAsset({ property_name: undefined });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('-')).toBeInTheDocument();
    });

    it('应该处理缺失的地址', () => {
      const asset = createMockAsset({ address: undefined });
      render(<AssetDetailInfo asset={asset} />);

      const dashElements = screen.getAllByText('-');
      expect(dashElements.length).toBeGreaterThan(0);
    });

    it('应该处理缺失的权属方', () => {
      const asset = createMockAsset({ ownership_entity: undefined });
      render(<AssetDetailInfo asset={asset} />);

      const dashElements = screen.getAllByText('-');
      expect(dashElements.length).toBeGreaterThan(0);
    });

    it('应该处理0值面积', () => {
      const asset = createMockAsset({
        land_area: 0,
        actual_property_area: 0,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-土地面积')).toBeInTheDocument();
    });

    it('应该处理null面积值', () => {
      const asset = createMockAsset({
        land_area: null as unknown as number,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-土地面积')).toBeInTheDocument();
    });
  });

  describe('时间信息', () => {
    it('应该显示创建时间', () => {
      const asset = createMockAsset({ created_at: '2024-01-01T00:00:00.000Z' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText(/创建时间/)).toBeInTheDocument();
    });

    it('应该显示更新时间', () => {
      const asset = createMockAsset({ updated_at: '2024-01-15T00:00:00.000Z' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText(/更新时间/)).toBeInTheDocument();
    });
  });

  describe('接收协议详情', () => {
    it('有协议日期时应该显示接收协议详情卡片', () => {
      const asset = createMockAsset({
        operation_agreement_start_date: '2024-01-01',
        operation_agreement_end_date: '2025-01-01',
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('接收协议详情')).toBeInTheDocument();
    });

    it('无协议日期时不应该显示接收协议详情卡片', () => {
      const asset = createMockAsset({
        operation_agreement_start_date: undefined,
        operation_agreement_end_date: undefined,
        operation_agreement_attachments: undefined,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByText('接收协议详情')).not.toBeInTheDocument();
    });
  });

  describe('经营性 vs 非经营性', () => {
    it('经营性资产应该显示出租率信息', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rentable_area: 100,
      });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('icon-percentage')).toBeInTheDocument();
    });

    it('非经营性资产不应该显示出租率信息', () => {
      const asset = createMockAsset({ property_nature: '非经营性' });
      render(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByTestId('icon-percentage')).not.toBeInTheDocument();
    });
  });
});
