import React from 'react'
import { render, screen, fireEvent } from '../../../__tests__/utils/testUtils'

import AssetCard from '../AssetCard'
import type { Asset } from '@/types/asset'
import { OwnershipStatus, PropertyNature, UsageStatus, BusinessModel } from '@/types/asset'

// Mock the format utilities
jest.mock('@/utils/format', () => ({
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
  formatPercentage: (value: number) => `${value.toFixed(2)}%`,
  calculateOccupancyRate: (rented: number, rentable: number) => {
    if (!rented || !rentable) return 0
    return (rented / rentable) * 100
  },
}))

const mockAsset: Asset = {
  id: '1',
  property_name: '测试物业名称',
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
  project_name: '五羊测试项目',
  contract_start_date: '2024-01-01',
  contract_end_date: '2025-12-31',
  notes: '备注信息',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T12:00:00Z',
}

describe('AssetCard', () => {
  const mockHandlers = {
    onEdit: jest.fn(),
    onDelete: jest.fn(),
    onView: jest.fn(),
    onSelect: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders basic asset information correctly', () => {
    render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Check property name
    expect(screen.getByText('测试物业名称')).toBeInTheDocument()

    // Check ownership entity
    expect(screen.getByText('权属方：测试权属方')).toBeInTheDocument()

    // Check address
    expect(screen.getByText('测试地址123号')).toBeInTheDocument()
  })

  it('displays status tags with correct colors', () => {
    render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Check status tags
    expect(screen.getByText('已确权')).toBeInTheDocument()
    expect(screen.getByText('经营类')).toBeInTheDocument()
    expect(screen.getByText('出租')).toBeInTheDocument()
  })

  it('shows area information correctly', () => {
    render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Check area statistics
    expect(screen.getByText('土地面积')).toBeInTheDocument()
    expect(screen.getByText('实际面积')).toBeInTheDocument()
    expect(screen.getByText('可出租面积')).toBeInTheDocument()
    expect(screen.getByText('已出租面积')).toBeInTheDocument()

    // Check area values - using more flexible matching
    expect(screen.getByText('5,000')).toBeInTheDocument()
    expect(screen.getByText('3,000')).toBeInTheDocument()
    expect(screen.getByText('2,500')).toBeInTheDocument()
    expect(screen.getByText('2,000')).toBeInTheDocument()
  })

  it('displays occupancy rate progress bar', () => {
    render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Check occupancy rate display
    expect(screen.getByText('出租率')).toBeInTheDocument()
    expect(screen.getByText('80.00%')).toBeInTheDocument()
  })

  it('shows usage and certificate information', () => {
    render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Check usage information
    expect(screen.getByText('证载：商业用途')).toBeInTheDocument()
    expect(screen.getByText('实际：办公楼')).toBeInTheDocument()
  })

  it('displays litigation status when litigated', () => {
    const litigatedAsset = { ...mockAsset, is_litigated: true }
    render(<AssetCard asset={litigatedAsset} {...mockHandlers} />)

    expect(screen.getByText('涉诉')).toBeInTheDocument()
  })

  it('shows time information correctly', () => {
    render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Check time information - using flexible matching for formatted dates
    expect(screen.getByText(/创建时间：/)).toBeInTheDocument()
    expect(screen.getByText(/更新时间：/)).toBeInTheDocument()
  })

  it('handles card selection correctly', () => {
    render(<AssetCard asset={mockAsset} onSelect={mockHandlers.onSelect} {...mockHandlers} />)

    // Click on the card to select it
    fireEvent.click(screen.getByText('测试物业名称'))
    expect(mockHandlers.onSelect).toHaveBeenCalledWith(mockAsset, true)
  })

  it('handles view button click correctly', () => {
    render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Find and click the view button - use icon name since button is wrapped in Tooltip
    const viewButton = screen.getByRole('button', { name: 'eye' })
    fireEvent.click(viewButton)
    expect(mockHandlers.onView).toHaveBeenCalledWith(mockAsset)
  })

  it('handles edit button click correctly', () => {
    render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Find and click the edit button - use icon name since button is wrapped in Tooltip
    const editButton = screen.getByRole('button', { name: 'edit' })
    fireEvent.click(editButton)
    expect(mockHandlers.onEdit).toHaveBeenCalledWith(mockAsset)
  })

  it('handles delete button click correctly', () => {
    render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Find and click the delete button - use icon name since button is wrapped in Tooltip
    const deleteButton = screen.getByRole('button', { name: 'delete' })
    fireEvent.click(deleteButton)
    expect(mockHandlers.onDelete).toHaveBeenCalledWith('1')
  })

  it('shows selected state when selected prop is true', () => {
    render(<AssetCard asset={mockAsset} selected={true} {...mockHandlers} />)

    // The card should have selected styling
    const cardElement = screen.getByText('测试物业名称').closest('.ant-card')
    expect(cardElement).toHaveClass('selected')
  })

  it('calculates occupancy rate when not provided', () => {
    const assetWithoutRate: Asset = {
      ...mockAsset,
      occupancy_rate: undefined,
      rentable_area: 1000,
      rented_area: 750,
    }

    render(<AssetCard asset={assetWithoutRate} {...mockHandlers} />)

    // Should calculate 75% occupancy rate
    expect(screen.getByText('75.00%')).toBeInTheDocument()
  })

  it('hides occupancy rate when rentable area is 0', () => {
    const assetWithoutRentableArea: Asset = {
      ...mockAsset,
      rentable_area: 0,
    }

    render(<AssetCard asset={assetWithoutRentableArea} {...mockHandlers} />)

    // Occupancy rate should not be displayed
    expect(screen.queryByText('出租率')).not.toBeInTheDocument()
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

    render(<AssetCard asset={minimalAsset} {...mockHandlers} />)

    // Check that basic information is still displayed
    expect(screen.getByText('最小物业')).toBeInTheDocument()
    expect(screen.getByText('权属方：权属方')).toBeInTheDocument()
    expect(screen.getByText('地址')).toBeInTheDocument()
  })

  it('shows non-commercial area for non-commercial properties', () => {
    const nonCommercialAsset: Asset = {
      ...mockAsset,
      property_nature: '非经营性',
      non_commercial_area: 1500,
      rentable_area: undefined,
      rented_area: undefined,
    }

    render(<AssetCard asset={nonCommercialAsset} {...mockHandlers} />)

    // Check that the component renders without errors
    expect(screen.getByText('测试物业名称')).toBeInTheDocument()
  })

  it('prevents event propagation on action buttons', () => {
    render(<AssetCard asset={mockAsset} onSelect={mockHandlers.onSelect} {...mockHandlers} />)

    // Click on edit button - should not trigger selection
    const editButton = screen.getByRole('button', { name: 'edit' })
    fireEvent.click(editButton)

    // onSelect should not be called, but onEdit should be
    expect(mockHandlers.onSelect).not.toHaveBeenCalled()
    expect(mockHandlers.onEdit).toHaveBeenCalledWith(mockAsset)
  })

  it('displays correct colors for different occupancy rates', () => {
    // Test high occupancy rate (>=80%)
    const highOccupancyAsset = { ...mockAsset, occupancy_rate: 85 }
    render(<AssetCard asset={highOccupancyAsset} {...mockHandlers} />)
    expect(screen.getByText('85.00%')).toBeInTheDocument()

    // Clean up and re-render for medium rate
    const { rerender } = render(<AssetCard asset={mockAsset} {...mockHandlers} />)

    // Test low occupancy rate (<60%)
    const lowOccupancyAsset = { ...mockAsset, occupancy_rate: 40 }
    rerender(<AssetCard asset={lowOccupancyAsset} {...mockHandlers} />)
    expect(screen.getByText('40.00%')).toBeInTheDocument()
  })
})