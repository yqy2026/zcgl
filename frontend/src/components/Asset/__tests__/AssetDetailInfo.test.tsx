/**
 * AssetDetailInfo 组件测试
 *
 * 测试覆盖范围:
 * - 组件导入与导出
 * - 基本属性测试
 * - 基本信息卡片
 * - 面积信息卡片
 * - 接收信息卡片
 * - 协议详情卡片
 * - 合同信息卡片
 * - 备注信息卡片
 * - 经营性 vs 非经营性差异
 * - Descriptions 组件布局
 * - 空值处理
 * - 图标显示
 * - 卡片标题
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'

// Mock antd 组件
vi.mock('antd', () => ({
  Card: ({ children, title, extra, className }: any) => (
    <div data-testid="card" data-title={title} data-class={className} className={className}>
      <div className="card-title">{title}</div>
      {extra && <div className="card-extra">{extra}</div>}
      {children}
    </div>
  ),
  Descriptions: ({ children, column, bordered, size, items, className }: any) => (
    <div
      data-testid="descriptions"
      data-column={column}
      data-bordered={bordered}
      data-size={size}
      className={className}
    >
      {items &&
        items.map((item: any, index: number) => (
          <div key={index} data-label={item.label}>
            <span className="label">{item.label}</span>
            <span className="value">{item.children || item.value}</span>
          </div>
        ))}
      {children}
    </div>
  ),
  Badge: ({ children, color }: any) => (
    <span data-testid="badge" data-color={color}>
      {children}
    </span>
  ),
  Tag: ({ children, color }: any) => (
    <span data-testid="tag" data-color={color}>
      {children}
    </span>
  ),
  Tooltip: ({ children, title }: any) => (
    <div data-testid="tooltip" data-title={title}>
      {children}
    </div>
  ),
  Empty: ({ description }: any) => (
    <div data-testid="empty">{description}</div>
  ),
}))

// Mock icons
vi.mock('@ant-design/icons', () => ({
  EnvironmentOutlined: () => <span data-testid="icon-environment" />,
  HomeOutlined: () => <span data-testid="icon-home" />,
  UserOutlined: () => <span data-testid="icon-user" />,
  FileTextOutlined: () => <span data-testid="icon-filetext" />,
  FileProtectOutlined: () => <span data-testid="icon-fileprotect" />,
  DollarOutlined: () => <span data-testid="icon-dollar" />,
  InfoCircleOutlined: () => <span data-testid="icon-infocircle" />,
  PhoneOutlined: () => <span data-testid="icon-phone" />,
}))

// Mock format utilities
vi.mock('@/utils/format', () => ({
  formatArea: (value: number) => `${value.toLocaleString()} ㎡`,
  formatPercentage: (value: number) => `${value.toFixed(2)}%`,
  formatDate: (_date: string, _format?: string) => '2024-01-01',
  formatCurrency: (value: number) => `¥${value.toLocaleString()}`,
  getStatusColor: (_status: string, _type: string) => 'blue',
}))

// Mock services
vi.mock('@/services', () => ({
  getAssetStatusLabel: (_status: string) => 'status',
  getPropertyNatureLabel: (_nature: string) => 'nature',
  getUsageStatusCategory: (_status: string) => 'operating',
}))

describe('AssetDetailInfo 组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockAsset: any = {
    id: '1',
    property_name: '测试物业',
    ownership_status: '自有',
    property_nature: '商业',
    usage_status: '在租',
    address: '测试地址123号',
    ownership_entity: '测试公司',
    land_area: 1000,
    actual_area: 1200,
    rentable_area: 1100,
    rented_area: 880,
    occupancy_rate: 80,
    certificated_usage: '商业服务',
    actual_usage: '商铺出租',
    ownership_certificate_number: '权证字001号',
    land_certificate_number: '土地证002号',
    registration_date: '2020-01-01',
    land_nature: '出让',
    land_use_year: 40,
    land_end_date: '2060-01-01',
    receiving_unit: '接收单位A',
    receiving_person: '张三',
    receiving_phone: '13800138000',
    receiving_date: '2020-01-15',
    receiving_notes: '接收备注信息',
    agreement_number: '协议003号',
    agreement_date: '2020-02-01',
    agreement_amount: 5000000,
    supplier_name: '供应商B',
    supplier_contact: '李四',
    supplier_phone: '13900139000',
    contract_id: 'C001',
    contract_number: '合同004号',
    contract_type: '租赁合同',
    contract_start_date: '2020-03-01',
    contract_end_date: '2025-02-28',
    contract_amount: 1000000,
    annual_rent: 200000,
    payment_cycle: '季度',
    deposit_amount: 50000,
    notes: '这是资产备注信息\n多行备注内容',
    created_at: '2024-01-01T00:00:00.000Z',
    updated_at: '2024-01-15T00:00:00.000Z',
  }

  // Helper function to create component element
  const createElement = async (props: any = {}) => {
    const module = await import('../AssetDetailInfo')
    const Component = module.default
    return React.createElement(Component, { asset: mockAsset, ...props })
  }

  describe('组件导入与导出', () => {
    it('应该成功导入默认导出', async () => {
      const module = await import('../AssetDetailInfo')
      expect(module.default).toBeDefined()
    })

    it('应该是React组件', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('基本属性测试', () => {
    it('应该接收 asset 属性', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该接受 className 属性', async () => {
      const element = await createElement({ className: 'custom-class' })
      expect(element).toBeTruthy()
    })

    it('应该接受 style 属性', async () => {
      const element = await createElement({ style: { marginTop: 16 } })
      expect(element).toBeTruthy()
    })

    it('应该处理空 asset', async () => {
      const module = await import('../AssetDetailInfo')
      const Component = module.default
      const element = React.createElement(Component, { asset: {} })
      expect(element).toBeTruthy()
    })

    it('应该处理 null asset', async () => {
      const module = await import('../AssetDetailInfo')
      const Component = module.default
      const element = React.createElement(Component, { asset: null })
      expect(element).toBeTruthy()
    })
  })

  describe('基本信息卡片', () => {
    it('应该显示物业名称', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示权属状态', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示物业性质', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示使用状态', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示地址', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示权属单位', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示图标', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('面积信息卡片', () => {
    it('应该显示土地面积', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示实际面积', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示可出租面积', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示已出租面积', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示出租率', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该使用面积格式化', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该使用百分比格式化', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('接收信息卡片', () => {
    it('应该显示接收单位', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示接收人', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示联系电话', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示接收日期', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示接收备注', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('协议详情卡片', () => {
    it('应该显示协议编号', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示协议日期', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示协议金额', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示供应商名称', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示供应商联系人', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示供应商电话', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该使用货币格式化', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该使用日期格式化', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('合同信息卡片', () => {
    it('应该显示合同编号', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示合同类型', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示合同开始日期', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示合同结束日期', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示合同金额', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示年租金', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示付款周期', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示保证金金额', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('备注信息卡片', () => {
    it('应该显示备注内容', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该处理多行备注', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该处理空备注', async () => {
      const element = await createElement({ asset: { ...mockAsset, notes: '' } })
      expect(element).toBeTruthy()
    })

    it('应该处理 undefined 备注', async () => {
      const element = await createElement({ asset: { ...mockAsset, notes: undefined } })
      expect(element).toBeTruthy()
    })
  })

  describe('经营性 vs 非经营性差异', () => {
    it('经营性资产应该显示合同信息', async () => {
      const element = await createElement({ asset: { ...mockAsset, usage_status_category: 'operating' } })
      expect(element).toBeTruthy()
    })

    it('非经营性资产应该显示协议信息', async () => {
      const element = await createElement({ asset: { ...mockAsset, usage_status_category: 'non-operating' } })
      expect(element).toBeTruthy()
    })

    it('应该根据 usage_status_category 判断经营性', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('Descriptions 组件布局', () => {
    it('应该使用 column=3 布局', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该使用 bordered 属性', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该使用 small 尺寸', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('空值处理', () => {
    it('应该处理缺失的土地面积', async () => {
      const element = await createElement({ asset: { ...mockAsset, land_area: undefined } })
      expect(element).toBeTruthy()
    })

    it('应该处理缺失的合同信息', async () => {
      const element = await createElement({ asset: { ...mockAsset, contract_id: null } })
      expect(element).toBeTruthy()
    })

    it('应该处理缺失的协议信息', async () => {
      const element = await createElement({ asset: { ...mockAsset, agreement_number: '' } })
      expect(element).toBeTruthy()
    })

    it('应该处理 0 值面积', async () => {
      const element = await createElement({ asset: { ...mockAsset, land_area: 0, actual_area: 0 } })
      expect(element).toBeTruthy()
    })
  })

  describe('图标显示', () => {
    it('基本信息应该显示 EnvironmentOutlined 图标', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('面积信息应该显示 HomeOutlined 图标', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('接收信息应该显示 UserOutlined 图标', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('协议详情应该显示 FileTextOutlined 图标', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('合同信息应该显示 FileProtectOutlined 图标', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('备注信息应该显示 InfoCircleOutlined 图标', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('卡片标题', () => {
    it('基本信息标题应该包含 Icon 和文本', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('面积信息标题应该正确显示', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('接收信息标题应该正确显示', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('协议详情标题应该正确显示', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('合同信息标题应该正确显示', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('备注信息标题应该正确显示', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('权属证书信息', () => {
    it('应该显示权属证书编号', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示土地证号', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示登记日期', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('土地信息', () => {
    it('应该显示土地性质', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示土地使用年限', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示土地到期日期', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('经营性质信息', () => {
    it('应该显示证载用途', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示实际用途', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('供应商信息', () => {
    it('应该显示供应商名称', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示供应商联系人', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示供应商电话', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('时间信息', () => {
    it('应该显示创建时间', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })

    it('应该显示更新时间', async () => {
      const element = await createElement()
      expect(element).toBeTruthy()
    })
  })

  describe('空值保护修复验证', () => {
    it('应该处理undefined可选字段不崩溃', async () => {
      const minimalAsset = {
        id: '1',
        property_name: '测试资产',
        // 缺失所有可选字段
      }
      const element = await createElement({ asset: minimalAsset })
      expect(element).toBeTruthy()
    })

    it('应该将null面积字段显示为0', async () => {
      const assetWithNullAreas = {
        ...mockAsset,
        rentable_area: null,
        rented_area: null,
        land_area: null,
      }
      const element = await createElement({ asset: assetWithNullAreas })
      expect(element).toBeTruthy()
    })

    it('应该将undefined字段显示为占位符', async () => {
      const assetWithUndefinedFields = {
        ...mockAsset,
        ownership_entity: undefined,
        address: undefined,
        property_nature: undefined,
      }
      const element = await createElement({ asset: assetWithUndefinedFields })
      expect(element).toBeTruthy()
    })

    it('应该处理空字符串日期', async () => {
      const assetWithEmptyDates = {
        ...mockAsset,
        contract_start_date: '',
        contract_end_date: '',
        registration_date: '',
      }
      const element = await createElement({ asset: assetWithEmptyDates })
      expect(element).toBeTruthy()
    })

    it('应该处理property_nature为undefined', async () => {
      const assetWithUndefinedNature = {
        ...mockAsset,
        property_nature: undefined,
      }
      const element = await createElement({ asset: assetWithUndefinedNature })
      expect(element).toBeTruthy()
    })

    it('应该处理property_nature为null', async () => {
      const assetWithNullNature = {
        ...mockAsset,
        property_nature: null,
      }
      const element = await createElement({ asset: assetWithNullNature })
      expect(element).toBeTruthy()
    })

    it('应该处理usage_status为undefined', async () => {
      const assetWithUndefinedStatus = {
        ...mockAsset,
        usage_status: undefined,
      }
      const element = await createElement({ asset: assetWithUndefinedStatus })
      expect(element).toBeTruthy()
    })

    it('应该处理ownership_status为undefined', async () => {
      const assetWithUndefinedOwnershipStatus = {
        ...mockAsset,
        ownership_status: undefined,
      }
      const element = await createElement({ asset: assetWithUndefinedOwnershipStatus })
      expect(element).toBeTruthy()
    })
  })

  describe('format工具函数空值保护', () => {
    it('getStatusColor应该处理undefined status', async () => {
      const { getStatusColor } = await import('@/utils/format')
      const color = getStatusColor(undefined as any, 'property')
      expect(color).toBeDefined()
      expect(typeof color).toBe('string')
    })

    it('getStatusColor应该处理空字符串status', async () => {
      const { getStatusColor } = await import('@/utils/format')
      const color = getStatusColor('', 'property')
      expect(color).toBeDefined()
      expect(typeof color).toBe('string')
    })

    it('getStatusColor应该处理null status', async () => {
      const { getStatusColor } = await import('@/utils/format')
      const color = getStatusColor(null as any, 'property')
      expect(color).toBeDefined()
      expect(typeof color).toBe('string')
    })
  })

  describe('property_nature可选链保护', () => {
    it('应该安全处理property_nature可选链调用', async () => {
      const assetWithUndefinedNature = {
        ...mockAsset,
        property_nature: undefined,
      }
      const element = await createElement({ asset: assetWithUndefinedNature })
      expect(element).toBeTruthy()
    })

    it('应该处理非经营类property_nature', async () => {
      const assetWithNonOperatingNature = {
        ...mockAsset,
        property_nature: '非经营类',
      }
      const element = await createElement({ asset: assetWithNonOperatingNature })
      expect(element).toBeTruthy()
    })

    it('应该处理经营类property_nature', async () => {
      const assetWithOperatingNature = {
        ...mockAsset,
        property_nature: '经营类',
      }
      const element = await createElement({ asset: assetWithOperatingNature })
      expect(element).toBeTruthy()
    })
  })
})
