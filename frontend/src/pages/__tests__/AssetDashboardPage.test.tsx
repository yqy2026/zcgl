import React from 'react'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/__tests__/utils/testUtils'
import AssetDashboardPage from '../AssetDashboardPage'
import { assetService } from '@/services/assetService'

// Mock the asset service
jest.mock('@/services/assetService')
const mockedAssetService = assetService as jest.Mocked<typeof assetService>

// Mock Chart.js components
jest.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="line-chart">Line Chart</div>,
  Bar: () => <div data-testid="bar-chart">Bar Chart</div>,
  Doughnut: () => <div data-testid="doughnut-chart">Doughnut Chart</div>,
}))

jest.mock('chart.js', () => ({
  Chart: {
    register: jest.fn(),
  },
  CategoryScale: {},
  LinearScale: {},
  PointElement: {},
  LineElement: {},
  BarElement: {},
  Title: {},
  Tooltip: {},
  Legend: {},
  ArcElement: {},
}))

const mockDashboardData = {
  totalAssets: 150,
  totalArea: 500000,
  totalRentedArea: 425000,
  overallOccupancyRate: 85.0,
  recentAssets: [
    {
      id: '1',
      property_name: '最新资产1',
      ownership_entity: '公司A',
      created_at: '2024-01-15T00:00:00Z',
    },
    {
      id: '2',
      property_name: '最新资产2',
      ownership_entity: '公司B',
      created_at: '2024-01-14T00:00:00Z',
    },
  ],
}

const mockOccupancyData = {
  overall_rate: 85.5,
  trend: 'up' as const,
  trend_percentage: 2.3,
  by_property_nature: [
    {
      property_nature: '经营类',
      rate: 88.2,
      total_area: 50000,
      rented_area: 44100,
    },
  ],
  by_ownership_entity: [
    {
      ownership_entity: '公司A',
      rate: 90.0,
      asset_count: 15,
    },
  ],
  monthly_trend: [
    {
      month: '2024-01',
      rate: 82.0,
      total_area: 70000,
      rented_area: 57400,
    },
  ],
  top_performers: [],
  low_performers: [],
}

const mockAreaData = {
  total_area: 500000,
  rented_area: 425000,
  vacant_area: 75000,
  by_property_nature: [
    {
      property_nature: '经营类',
      total_area: 300000,
      rented_area: 270000,
      vacant_area: 30000,
    },
    {
      property_nature: '非经营类',
      total_area: 200000,
      rented_area: 155000,
      vacant_area: 45000,
    },
  ],
  by_ownership_entity: [
    {
      ownership_entity: '公司A',
      total_area: 250000,
      asset_count: 75,
    },
    {
      ownership_entity: '公司B',
      total_area: 250000,
      asset_count: 75,
    },
  ],
}

const mockDistributionData = {
  by_property_nature: [
    { property_nature: '经营类', count: 90, percentage: 60.0 },
    { property_nature: '非经营类', count: 60, percentage: 40.0 },
  ],
  by_ownership_status: [
    { ownership_status: '已确权', count: 120, percentage: 80.0 },
    { ownership_status: '未确权', count: 30, percentage: 20.0 },
  ],
  by_usage_status: [
    { usage_status: '出租', count: 100, percentage: 66.7 },
    { usage_status: '自用', count: 30, percentage: 20.0 },
    { usage_status: '空置', count: 20, percentage: 13.3 },
  ],
  by_ownership_entity: [
    { ownership_entity: '公司A', count: 75, percentage: 50.0 },
    { ownership_entity: '公司B', count: 45, percentage: 30.0 },
    { ownership_entity: '公司C', count: 30, percentage: 20.0 },
  ],
}

describe('AssetDashboardPage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    
    // Setup default mock responses
    mockedAssetService.getDashboardStats.mockResolvedValue(mockDashboardData)
    mockedAssetService.getOccupancyRateStats.mockResolvedValue(mockOccupancyData)
    mockedAssetService.getAreaStats.mockResolvedValue(mockAreaData)
    mockedAssetService.getAssetDistribution.mockResolvedValue(mockDistributionData)
  })

  it('renders dashboard page with all components', async () => {
    renderWithProviders(<AssetDashboardPage />)

    // Check page title
    expect(screen.getByText('资产概览')).toBeInTheDocument()

    // Wait for data to load and check statistics cards
    await waitFor(() => {
      expect(screen.getByText('总资产数量')).toBeInTheDocument()
    })

    expect(screen.getByText('150')).toBeInTheDocument() // totalAssets
    expect(screen.getByText('500,000 ㎡')).toBeInTheDocument() // totalArea
    expect(screen.getByText('425,000 ㎡')).toBeInTheDocument() // totalRentedArea
    expect(screen.getByText('85.00%')).toBeInTheDocument() // overallOccupancyRate
  })

  it('displays recent assets list', async () => {
    renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('最新资产')).toBeInTheDocument()
    })

    expect(screen.getByText('最新资产1')).toBeInTheDocument()
    expect(screen.getByText('最新资产2')).toBeInTheDocument()
    expect(screen.getByText('公司A')).toBeInTheDocument()
    expect(screen.getByText('公司B')).toBeInTheDocument()
  })

  it('renders all chart components', async () => {
    renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })

    expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
    expect(screen.getByTestId('doughnut-chart')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    // Mock services to never resolve
    mockedAssetService.getDashboardStats.mockImplementation(
      () => new Promise(() => {})
    )
    mockedAssetService.getOccupancyRateStats.mockImplementation(
      () => new Promise(() => {})
    )
    mockedAssetService.getAreaStats.mockImplementation(
      () => new Promise(() => {})
    )
    mockedAssetService.getAssetDistribution.mockImplementation(
      () => new Promise(() => {})
    )

    renderWithProviders(<AssetDashboardPage />)

    // Should show loading skeletons
    expect(screen.getAllByTestId('skeleton-loader')).toHaveLength(4)
  })

  it('handles API errors gracefully', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {})
    
    mockedAssetService.getDashboardStats.mockRejectedValue(
      new Error('Dashboard API Error')
    )
    mockedAssetService.getOccupancyRateStats.mockRejectedValue(
      new Error('Occupancy API Error')
    )
    mockedAssetService.getAreaStats.mockRejectedValue(
      new Error('Area API Error')
    )
    mockedAssetService.getAssetDistribution.mockRejectedValue(
      new Error('Distribution API Error')
    )

    renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(screen.getAllByText('数据加载失败')).toHaveLength(4)
    })

    expect(screen.getAllByText(/请稍后重试/)).toHaveLength(4)
    
    consoleError.mockRestore()
  })

  it('refreshes data when refresh button is clicked', async () => {
    renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('总资产数量')).toBeInTheDocument()
    })

    // Initial API calls
    expect(mockedAssetService.getDashboardStats).toHaveBeenCalledTimes(1)
    expect(mockedAssetService.getOccupancyRateStats).toHaveBeenCalledTimes(1)
    expect(mockedAssetService.getAreaStats).toHaveBeenCalledTimes(1)
    expect(mockedAssetService.getAssetDistribution).toHaveBeenCalledTimes(1)

    // Click refresh button
    const refreshButton = screen.getByRole('button', { name: /刷新/ })
    refreshButton.click()

    await waitFor(() => {
      expect(mockedAssetService.getDashboardStats).toHaveBeenCalledTimes(2)
    })

    expect(mockedAssetService.getOccupancyRateStats).toHaveBeenCalledTimes(2)
    expect(mockedAssetService.getAreaStats).toHaveBeenCalledTimes(2)
    expect(mockedAssetService.getAssetDistribution).toHaveBeenCalledTimes(2)
  })

  it('applies date range filter correctly', async () => {
    renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('总资产数量')).toBeInTheDocument()
    })

    // Find and interact with date range picker
    const dateRangePicker = screen.getByPlaceholderText('选择日期范围')
    dateRangePicker.click()

    // Simulate selecting a date range
    const startDate = '2024-01-01'
    const endDate = '2024-01-31'
    
    // This would trigger a re-fetch with date filters
    await waitFor(() => {
      expect(mockedAssetService.getDashboardStats).toHaveBeenCalledWith({
        start_date: startDate,
        end_date: endDate,
      })
    })
  })

  it('navigates to asset list when view all button is clicked', async () => {
    const mockNavigate = jest.fn()
    jest.doMock('react-router-dom', () => ({
      ...jest.requireActual('react-router-dom'),
      useNavigate: () => mockNavigate,
    }))

    renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('最新资产')).toBeInTheDocument()
    })

    const viewAllButton = screen.getByRole('button', { name: /查看全部/ })
    viewAllButton.click()

    expect(mockNavigate).toHaveBeenCalledWith('/assets')
  })

  it('displays correct trend indicators', async () => {
    renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId('trending-up-icon')).toBeInTheDocument()
    })

    expect(screen.getByText('2.30%')).toBeInTheDocument()
  })

  it('handles empty data gracefully', async () => {
    mockedAssetService.getDashboardStats.mockResolvedValue({
      totalAssets: 0,
      totalArea: 0,
      totalRentedArea: 0,
      overallOccupancyRate: 0,
      recentAssets: [],
    })

    renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('0')).toBeInTheDocument()
    })

    expect(screen.getByText('暂无最新资产')).toBeInTheDocument()
  })

  it('auto-refreshes data every 5 minutes', async () => {
    jest.useFakeTimers()
    
    renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(mockedAssetService.getDashboardStats).toHaveBeenCalledTimes(1)
    })

    // Fast forward 5 minutes
    jest.advanceTimersByTime(5 * 60 * 1000)

    await waitFor(() => {
      expect(mockedAssetService.getDashboardStats).toHaveBeenCalledTimes(2)
    })

    jest.useRealTimers()
  })

  it('stops auto-refresh when component unmounts', async () => {
    jest.useFakeTimers()
    
    const { unmount } = renderWithProviders(<AssetDashboardPage />)

    await waitFor(() => {
      expect(mockedAssetService.getDashboardStats).toHaveBeenCalledTimes(1)
    })

    unmount()

    // Fast forward 5 minutes
    jest.advanceTimersByTime(5 * 60 * 1000)

    // Should not call API again after unmount
    expect(mockedAssetService.getDashboardStats).toHaveBeenCalledTimes(1)

    jest.useRealTimers()
  })
})