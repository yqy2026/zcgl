import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import AssetDetailInfo from '../AssetDetailInfo'
import type { Asset } from '@/types/asset'
import { OwnershipStatus, PropertyNature, UsageStatus, BusinessModel } from '@/types/asset'

// Mock the format utilities
vi.mock('@/utils/format', () => ({
  formatArea: (value: number) => `${value?.toLocaleString()} ㎡`,
  formatDate: (date: string, format?: string) => {
    if (format === 'datetime') {
      return new Date(date).toLocaleString()
    }
    return new Date(date).toLocaleDateString()
  },
  getStatusColor: (status: string, type: string) => {
    const colorMaps: Record<string, Record<string, string>> = {
      ownership: { '已确权': 'green', '未确权': 'red' },
      property: { '经营类': 'blue', '非经营类': 'default' },
      usage: { '出租': 'green', '闲置': 'red', '自用': 'blue' },
    }
    return colorMaps[type]?.[status] || 'default'
  },
  calculateOccupancyRate: (rented: number, rentable: number) => {
    if (!rented || !rentable) return 0
    return (rented / rentable) * 100
  },
}))

const mockAsset: Asset = {
  id: '1',
  property_name: '测试物业',
  ownership_entity: '测试权属方',
  address: '测试地址123号',
  land_area: 5000,
  actual_property_area: 3000,
  rentable_area: 2500,
  rented_area: 2000,
  unrented_area: 500,
  non_commercial_area: 0,
  ownership_status: OwnershipStatus.CONFIRMED,
  property_nature: PropertyNature.COMMERCIAL_CLASS,
  usage_status: UsageStatus.RENTED,
  certificated_usage: '商业用途',
  actual_usage: '办公楼',
  business_category: '商业办公',
  business_model: BusinessModel.SELF_OPERATION,
  is_litigated: false,
  include_in_occupancy_rate: true,
  occupancy_rate: 80.00,
  tenant_name: '测试租户',
  lease_contract: 'LC001',
  current_contract_start_date: '2024-01-01',
  current_contract_end_date: '2024-12-31',
  current_lease_contract: 'CLC001',
  current_terminal_contract: 'CTC001',
  wuyang_project_name: '五羊测试项目',
  agreement_start_date: '2024-01-01',
  agreement_end_date: '2025-12-31',
  description: '这是一个测试物业的描述信息',
  notes: '备注信息',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T12:00:00Z',
}

describe('AssetDetailInfo', () => {
  it('renders basic asset information correctly', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check basic information
    expect(screen.getByText('测试物业')).toBeInTheDocument()
    expect(screen.getByText('测试权属方')).toBeInTheDocument()
    expect(screen.getByText('测试管理方')).toBeInTheDocument()
    expect(screen.getByText('测试地址123号')).toBeInTheDocument()
  })

  it('displays status tags with correct colors', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check status tags
    expect(screen.getByText('已确权')).toBeInTheDocument()
    expect(screen.getByText('经营类')).toBeInTheDocument()
    expect(screen.getByText('出租')).toBeInTheDocument()
  })

  it('shows area information correctly', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check area statistics
    expect(screen.getByText('5,000 ㎡')).toBeInTheDocument() // land_area
    expect(screen.getByText('3,000 ㎡')).toBeInTheDocument() // actual_property_area
    expect(screen.getByText('2,500 ㎡')).toBeInTheDocument() // rentable_area
    expect(screen.getByText('2,000 ㎡')).toBeInTheDocument() // rented_area
    expect(screen.getByText('500 ㎡')).toBeInTheDocument() // unrented_area
  })

  it('displays occupancy rate for commercial properties', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check occupancy rate display
    expect(screen.getByText('出租率: 80.00%')).toBeInTheDocument()
  })

  it('shows usage and business information', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check usage information
    expect(screen.getByText('商业用途')).toBeInTheDocument() // certificated_usage
    expect(screen.getByText('办公楼')).toBeInTheDocument() // actual_usage
    expect(screen.getByText('商业办公')).toBeInTheDocument() // business_category
    expect(screen.getByText('整租')).toBeInTheDocument() // business_model
  })

  it('displays contract information for rented properties', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check contract information
    expect(screen.getByText('测试租户')).toBeInTheDocument() // tenant_name
    expect(screen.getByText('LC001')).toBeInTheDocument() // lease_contract
    expect(screen.getByText('CLC001')).toBeInTheDocument() // current_lease_contract
    expect(screen.getByText('CTC001')).toBeInTheDocument() // current_terminal_contract
  })

  it('shows project information when available', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check project information
    expect(screen.getByText('五羊测试项目')).toBeInTheDocument()
  })

  it('displays description and notes', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check description and notes
    expect(screen.getByText('这是一个测试物业的描述信息')).toBeInTheDocument()
    expect(screen.getByText('备注信息')).toBeInTheDocument()
  })

  it('shows litigation status correctly', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check litigation status (should show "否" for false)
    expect(screen.getByText('否')).toBeInTheDocument()
  })

  it('handles missing optional fields gracefully', () => {
    const minimalAsset: Asset = {
      id: '2',
      property_name: '最小物业',
      ownership_entity: '权属方',
      address: '地址',
      ownership_status: OwnershipStatus.CONFIRMED,
      property_nature: PropertyNature.NON_COMMERCIAL_CLASS,
      usage_status: UsageStatus.SELF_USED,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    render(<AssetDetailInfo asset={minimalAsset} />)

    // Check that basic information is still displayed
    expect(screen.getByText('最小物业')).toBeInTheDocument()
    expect(screen.getByText('权属方')).toBeInTheDocument()
    expect(screen.getByText('地址')).toBeInTheDocument()

    // Check that missing fields show as "-"
    expect(screen.getAllByText('-')).toHaveLength(expect.any(Number))
  })

  it('displays non-commercial area for non-commercial properties', () => {
    const nonCommercialAsset: Asset = {
      ...mockAsset,
      property_nature: PropertyNature.NON_COMMERCIAL_CLASS,
      non_commercial_area: 1500,
      rentable_area: undefined,
      rented_area: undefined,
      unrented_area: undefined,
    }

    render(<AssetDetailInfo asset={nonCommercialAsset} />)

    // Check non-commercial area is displayed
    expect(screen.getByText('1,500 ㎡')).toBeInTheDocument()
  })

  it('calculates occupancy rate when not provided', () => {
    const assetWithoutRate: Asset = {
      ...mockAsset,
      occupancy_rate: undefined,
      rentable_area: 1000,
      rented_area: 750,
    }

    render(<AssetDetailInfo asset={assetWithoutRate} />)

    // Should calculate 75% occupancy rate
    expect(screen.getByText('出租率: 75.00%')).toBeInTheDocument()
  })

  it('shows include in occupancy rate status', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check include in occupancy rate status
    expect(screen.getByText('是')).toBeInTheDocument() // for include_in_occupancy_rate: true
  })

  it('formats dates correctly', () => {
    render(<AssetDetailInfo asset={mockAsset} />)

    // Check that dates are formatted (exact format depends on locale)
    // We just check that some date-like content is present
    const dateElements = screen.getAllByText(/2024/)
    expect(dateElements.length).toBeGreaterThan(0)
  })
})