/**
 * AssetDetailInfo 组件测试
 * 测试资产详情信息展示
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
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
  Card.displayName = 'MockCard';

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
  Descriptions.displayName = 'MockDescriptions';

  const DescriptionsItem = ({
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
  DescriptionsItem.displayName = 'MockDescriptionsItem';
  Descriptions.Item = DescriptionsItem;

  const Tag = ({ children, color }: { children: React.ReactNode; color?: string }) => (
    <span data-testid="tag" data-color={color}>
      {children}
    </span>
  );
  Tag.displayName = 'MockTag';

  const Progress = ({ percent, strokeColor }: { percent: number; strokeColor?: string }) => (
    <div
      data-testid="progress"
      data-percent={percent}
      data-color={strokeColor}
      role="progressbar"
    />
  );
  Progress.displayName = 'MockProgress';

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

  const Statistic = ({
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
  );
  Statistic.displayName = 'MockStatistic';

  const Divider = ({
    children,
    titlePlacement,
  }: {
    children: React.ReactNode;
    titlePlacement?: string;
  }) => (
    <div data-testid="divider" data-placement={titlePlacement}>
      {children}
    </div>
  );
  Divider.displayName = 'MockDivider';

  const ConfigProvider = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="config-provider">{children}</div>
  );
  ConfigProvider.displayName = 'MockConfigProvider';
  const theme = { defaultAlgorithm: 'default' };

  return {
    Card,
    Descriptions,
    Tag,
    Progress,
    Row,
    Col,
    Statistic,
    Divider,
    ConfigProvider,
    theme,
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => {
  const HomeOutlined = () => <span data-testid="icon-home">HomeIcon</span>;
  const EnvironmentOutlined = () => <span data-testid="icon-environment">EnvIcon</span>;
  const UserOutlined = () => <span data-testid="icon-user">UserIcon</span>;
  const CalendarOutlined = () => <span data-testid="icon-calendar">CalendarIcon</span>;
  const PercentageOutlined = () => <span data-testid="icon-percentage">PercentIcon</span>;
  const InfoCircleOutlined = () => <span data-testid="icon-info">InfoIcon</span>;

  HomeOutlined.displayName = 'HomeOutlined';
  EnvironmentOutlined.displayName = 'EnvironmentOutlined';
  UserOutlined.displayName = 'UserOutlined';
  CalendarOutlined.displayName = 'CalendarOutlined';
  PercentageOutlined.displayName = 'PercentageOutlined';
  InfoCircleOutlined.displayName = 'InfoCircleOutlined';

  return {
    HomeOutlined,
    EnvironmentOutlined,
    UserOutlined,
    CalendarOutlined,
    PercentageOutlined,
    InfoCircleOutlined,
  };
});

import AssetDetailInfo from '../AssetDetailInfo';

describe('AssetDetailInfo', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('基本渲染', () => {
    it('应该正确渲染组件', () => {
      const asset = createMockAsset({ asset_name: '测试物业' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
    });

    it('应该显示基本信息卡片标题', () => {
      const asset = createMockAsset();
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('基本信息')).toBeInTheDocument();
    });

    it('应该显示面积信息卡片', () => {
      const asset = createMockAsset();
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('面积信息')).toBeInTheDocument();
    });

    it('应该显示接收信息卡片', () => {
      const asset = createMockAsset();
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('接收信息')).toBeInTheDocument();
    });
  });

  describe('基本信息显示', () => {
    it('应该显示物业名称', () => {
      const asset = createMockAsset({ asset_name: '测试物业A栋' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('测试物业A栋')).toBeInTheDocument();
    });

    it('应该显示项目名称', () => {
      const asset = createMockAsset({ project_name: '测试项目' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('测试项目')).toBeInTheDocument();
    });

    it('应该显示权属方', () => {
      const asset = createMockAsset({ owner_party_name: '测试集团有限公司' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('测试集团有限公司')).toBeInTheDocument();
    });

    it('应该显示地址', () => {
      const asset = createMockAsset({ address: '深圳市南山区科技园' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('深圳市南山区科技园')).toBeInTheDocument();
    });

    it('应该显示确权状态标签', () => {
      const asset = createMockAsset({ ownership_status: '已确权' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('已确权')).toBeInTheDocument();
    });

    it('应该显示使用状态标签', () => {
      const asset = createMockAsset({ usage_status: '出租' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('出租')).toBeInTheDocument();
    });

    it('应该显示物业性质标签', () => {
      const asset = createMockAsset({ property_nature: '经营性' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('经营性')).toBeInTheDocument();
    });

    it('应该显示是否涉诉', () => {
      const asset = createMockAsset({ is_litigated: true });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      const yesElements = screen.getAllByText('是');
      expect(yesElements.length).toBeGreaterThan(0);
    });
  });

  describe('面积信息显示', () => {
    it('应该显示土地面积', () => {
      const asset = createMockAsset({ land_area: 1000 });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-土地面积')).toBeInTheDocument();
    });

    it('应该显示实际房产面积', () => {
      const asset = createMockAsset({ actual_property_area: 800 });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-实际房产面积')).toBeInTheDocument();
    });

    it('经营性资产应该显示可出租面积', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rentable_area: 600,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-可出租面积')).toBeInTheDocument();
    });

    it('经营性资产应该显示已出租面积', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rented_area: 300,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-已出租面积')).toBeInTheDocument();
    });

    it('经营性资产应该显示未出租面积', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        unrented_area: 100,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-未出租面积')).toBeInTheDocument();
    });

    it('非经营性资产不应该显示出租面积', () => {
      const asset = createMockAsset({
        property_nature: '非经营性',
        rentable_area: 600,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

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
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      const rateElements = screen.getAllByText(/出租率/);
      expect(rateElements.length).toBeGreaterThan(0);
    });

    it('有可出租面积时应该显示进度条', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rentable_area: 100,
        rented_area: 80,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('progress')).toBeInTheDocument();
    });

    it('rentable_area为0时不应该显示进度条', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rentable_area: 0,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByTestId('progress')).not.toBeInTheDocument();
    });
  });

  describe('接收信息显示', () => {
    it('应该显示经营模式', () => {
      const asset = createMockAsset({ revenue_mode: '委托经营' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('委托经营')).toBeInTheDocument();
    });

    it('应该显示是否计入出租率', () => {
      const asset = createMockAsset({ include_in_occupancy_rate: true });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      // 检查标签存在
      const tags = screen.getAllByTestId('tag');
      const includeTag = tags.find(tag => tag.textContent === '是');
      expect(includeTag).toBeInTheDocument();
    });

    it('应该显示权属类别', () => {
      const asset = createMockAsset({ ownership_category: '自有物业' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('自有物业')).toBeInTheDocument();
    });
  });

  describe('合同信息显示', () => {
    it('出租状态应该显示合同信息卡片', () => {
      const asset = createMockAsset({
        usage_status: '出租',
        tenant_name: '租户A',
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('合同信息')).toBeInTheDocument();
    });

    it('应该显示承租方名称', () => {
      const asset = createMockAsset({
        usage_status: '出租',
        tenant_name: '测试租户公司',
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('测试租户公司')).toBeInTheDocument();
    });

    it('应该显示租赁合同编号', () => {
      const asset = createMockAsset({
        usage_status: '出租',
        lease_contract_number: 'LC-2024-001',
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('LC-2024-001')).toBeInTheDocument();
    });

    it('非出租状态不应该显示合同信息卡片', () => {
      const asset = createMockAsset({ usage_status: '空置' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByText('合同信息')).not.toBeInTheDocument();
    });
  });

  describe('备注信息显示', () => {
    it('有备注时应该显示备注卡片', () => {
      const asset = createMockAsset({ notes: '这是备注内容' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('备注信息')).toBeInTheDocument();
      expect(screen.getByText('这是备注内容')).toBeInTheDocument();
    });

    it('无备注时不应该显示备注卡片', () => {
      const asset = createMockAsset({ notes: '' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByText('备注信息')).not.toBeInTheDocument();
    });

    it('备注为undefined时不应该显示备注卡片', () => {
      const asset = createMockAsset({ notes: undefined });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByText('备注信息')).not.toBeInTheDocument();
    });
  });

  describe('图标显示', () => {
    it('应该显示基本信息图标', () => {
      const asset = createMockAsset();
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('icon-info')).toBeInTheDocument();
    });

    it('应该显示位置图标', () => {
      const asset = createMockAsset();
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('icon-environment')).toBeInTheDocument();
    });

    it('应该显示用户图标', () => {
      const asset = createMockAsset();
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('icon-user')).toBeInTheDocument();
    });
  });

  describe('空值处理', () => {
    it('应该处理缺失的物业名称', () => {
      const asset = createMockAsset({ asset_name: undefined });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      const dashElements = screen.queryAllByText('-');
      expect(dashElements.length).toBeGreaterThan(0);
    });

    it('应该处理缺失的地址', () => {
      const asset = createMockAsset({ address: undefined });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      const dashElements = screen.getAllByText('-');
      expect(dashElements.length).toBeGreaterThan(0);
    });

    it('应该处理缺失的权属方', () => {
      const asset = createMockAsset({ owner_party_name: undefined });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      const dashElements = screen.getAllByText('-');
      expect(dashElements.length).toBeGreaterThan(0);
    });

    it('应该处理0值面积', () => {
      const asset = createMockAsset({
        land_area: 0,
        actual_property_area: 0,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-土地面积')).toBeInTheDocument();
    });

    it('应该处理null面积值', () => {
      const asset = createMockAsset({
        land_area: null as unknown as number,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('statistic-土地面积')).toBeInTheDocument();
    });
  });

  describe('时间信息', () => {
    it('应该显示创建时间', () => {
      const asset = createMockAsset({ created_at: '2024-01-01T00:00:00.000Z' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText(/创建时间/)).toBeInTheDocument();
    });

    it('应该显示更新时间', () => {
      const asset = createMockAsset({ updated_at: '2024-01-15T00:00:00.000Z' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText(/更新时间/)).toBeInTheDocument();
    });
  });

  describe('接收协议详情', () => {
    it('有协议日期时应该显示接收协议详情卡片', () => {
      const asset = createMockAsset({
        operation_agreement_start_date: '2024-01-01',
        operation_agreement_end_date: '2025-01-01',
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByText('接收协议详情')).toBeInTheDocument();
    });

    it('无协议日期时不应该显示接收协议详情卡片', () => {
      const asset = createMockAsset({
        operation_agreement_start_date: undefined,
        operation_agreement_end_date: undefined,
        operation_agreement_attachments: undefined,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByText('接收协议详情')).not.toBeInTheDocument();
    });
  });

  describe('经营性 vs 非经营性', () => {
    it('经营性资产应该显示出租率信息', () => {
      const asset = createMockAsset({
        property_nature: '经营性',
        rentable_area: 100,
      });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.getByTestId('icon-percentage')).toBeInTheDocument();
    });

    it('非经营性资产不应该显示出租率信息', () => {
      const asset = createMockAsset({ property_nature: '非经营性' });
      renderWithProviders(<AssetDetailInfo asset={asset} />);

      expect(screen.queryByTestId('icon-percentage')).not.toBeInTheDocument();
    });
  });
});
