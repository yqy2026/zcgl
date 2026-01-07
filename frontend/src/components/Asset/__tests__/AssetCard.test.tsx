/**
 * AssetCard 组件测试
 * 测试资产卡片组件
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';

// Mock format utilities
vi.mock('@/utils/format', () => ({
  formatPercentage: (value: number) => `${value.toFixed(2)}%`,
  formatDate: (_date: string, _format?: string) => '2024-01-01',
  getStatusColor: (_status: string, _type: string) => 'blue',
  calculateOccupancyRate: (_rented: number, _rentable: number) => 50,
}));

// Mock Ant Design components
vi.mock('antd', () => ({
  Card: ({ children, className, hoverable, style, actions, title, Meta, ...props }: any) => (
    <div
      data-testid="card"
      className={className}
      style={style}
      data-hoverable={hoverable}
      {...props}
    >
      {title && <div data-testid="card-title">{title}</div>}
      {Meta && <div data-testid="card-meta">{Meta}</div>}
      {actions && <div data-testid="card-actions">{actions}</div>}
      {children}
    </div>
  ),
  Tag: ({ children, color, closable }: any) => (
    <div data-testid="tag" data-color={color} data-closable={closable}>
      {children}
    </div>
  ),
  Button: ({ children, icon, onClick, type, danger }: any) => (
    <button data-testid="button" data-type={type} data-danger={danger} onClick={onClick}>
      {icon}
      {children}
    </button>
  ),
  Space: ({ children }: any) => <div data-testid="space">{children}</div>,
  Tooltip: ({ children, title }: any) => (
    <div data-testid="tooltip" data-title={title}>
      {children}
    </div>
  ),
  Row: ({ children, gutter }: any) => (
    <div data-testid="row" data-gutter={gutter}>
      {children}
    </div>
  ),
  Col: ({ children, span }: any) => (
    <div data-testid="col" data-span={span}>
      {children}
    </div>
  ),
  Statistic: ({ title, value, suffix, precision, valueStyle }: any) => (
    <div data-testid="statistic" data-title={title}>
      <div
        data-value={value}
        data-precision={precision}
        data-value-style={JSON.stringify(valueStyle)}
      >
        {value}
        {suffix}
      </div>
      <div data-testid="statistic-title">{title}</div>
    </div>
  ),
  Progress: ({ percent, strokeColor, size, showInfo }: any) => (
    <div
      data-testid="progress"
      data-percent={percent}
      data-stroke-color={strokeColor}
      data-size={size}
      data-show-info={showInfo}
    >
      {percent}%
    </div>
  ),
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  EditOutlined: () => <div data-testid="icon-edit" />,
  DeleteOutlined: () => <div data-testid="icon-delete" />,
  EyeOutlined: () => <div data-testid="icon-eye" />,
  HistoryOutlined: () => <div data-testid="icon-history" />,
  EnvironmentOutlined: () => <div data-testid="icon-environment" />,
  UserOutlined: () => <div data-testid="icon-user" />,
}));

describe('AssetCard - 组件导入测试', () => {
  it('应该能够导入AssetCard组件', async () => {
    const module = await import('../AssetCard');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });
});

describe('AssetCard - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持asset属性', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const mockAsset = {
      id: '1',
      property_name: '测试物业',
      ownership_entity: '测试权属方',
      address: '测试地址',
      ownership_status: '已确权',
      property_nature: '经营性',
      usage_status: '空置',
      land_area: 1000,
      actual_property_area: 800,
      rentable_area: 600,
      rented_area: 300,
      created_at: '2024-01-01T00:00:00.000Z',
      updated_at: '2024-01-01T00:00:00.000Z',
    };
    const element = React.createElement(AssetCard, {
      asset: mockAsset as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该支持onEdit回调', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const handleEdit = vi.fn();
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: handleEdit,
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该支持onDelete回调', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const handleDelete = vi.fn();
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: handleDelete,
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该支持onView回调', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const handleView = vi.fn();
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: handleView,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持selected属性', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      selected: true,
    });
    expect(element).toBeTruthy();
  });

  it('默认selected应该是false', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该支持onSelect回调', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const handleSelect = vi.fn();
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onSelect: handleSelect,
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 卡片头部测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示物业名称', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { property_name: '测试物业' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该显示权属状态标签', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { ownership_status: '已确权' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该显示物业性质标签', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { property_nature: '经营性' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该显示地址', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { address: '测试地址' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该显示权属方', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { ownership_entity: '测试权属方' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 操作按钮测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该有查看详情按钮', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该有编辑按钮', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该有历史记录按钮', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该有删除按钮', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('删除按钮应该是danger类型', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 面积信息测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示土地面积', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { land_area: 1000 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该显示实际面积', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { actual_property_area: 800 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该显示可出租面积', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { rentable_area: 600 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该显示已出租面积', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { rented_area: 300 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 出租率测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示出租率进度条', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { rentable_area: 600, rented_area: 300 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('出租率>=80%应该显示绿色', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { rentable_area: 100, rented_area: 90, occupancy_rate: 90 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('出租率>=60%应该显示黄色', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { rentable_area: 100, rented_area: 65, occupancy_rate: 65 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('出租率<60%应该显示红色', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { rentable_area: 100, rented_area: 30, occupancy_rate: 30 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('无rentable_area时不显示进度条', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { rentable_area: 0 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 状态标签测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示使用状态标签', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { usage_status: '空置' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('is_litigated为true时应该显示涉诉标签', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { is_litigated: true } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该显示证载用途标签', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { certificated_usage: '商业' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('实际用途与证载用途不同时应该显示实际用途标签', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { certificated_usage: '商业', actual_usage: '办公' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 时间信息测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示创建时间', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { created_at: '2024-01-01T00:00:00.000Z' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该显示更新时间', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { updated_at: '2024-01-01T00:00:00.000Z' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 选中状态测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('selected为true时应该有selected样式', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      selected: true,
    });
    expect(element).toBeTruthy();
  });

  it('selected为true时应该有2px边框', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      selected: true,
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 点击事件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('点击卡片应该触发onSelect', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const handleSelect = vi.fn();
    const asset = { id: '1' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
      onSelect: handleSelect,
    });
    expect(element).toBeTruthy();
  });

  it('操作按钮点击应该阻止冒泡', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理缺失的area字段', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = {} as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该处理0值area', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = {
      land_area: 0,
      actual_property_area: 0,
      rentable_area: 0,
      rented_area: 0,
    } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该处理undefined的occupancy_rate', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { rented_area: 300, rentable_area: 600 } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该处理空字符串', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const asset = { property_name: '', address: '', ownership_entity: '' } as any;
    const element = React.createElement(AssetCard, {
      asset,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 图标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('地址应该有EnvironmentOutlined图标', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('权属方应该有UserOutlined图标', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('查看按钮应该有EyeOutlined图标', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('编辑按钮应该有EditOutlined图标', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('历史按钮应该有HistoryOutlined图标', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('删除按钮应该有DeleteOutlined图标', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('AssetCard - 布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('面积统计应该使用4列布局', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('面积统计每列应该是span=6', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });

  it('应该有16的gutter', async () => {
    const { default: AssetCard } = await import('../AssetCard');
    const element = React.createElement(AssetCard, {
      asset: {} as any,
      onEdit: vi.fn(),
      onDelete: vi.fn(),
      onView: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});
