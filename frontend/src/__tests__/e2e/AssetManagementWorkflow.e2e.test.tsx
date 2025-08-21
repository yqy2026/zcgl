import React from 'react'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, mockAssetData } from '@/__tests__/utils/testUtils'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { message } from 'antd'

// Import all pages for full workflow testing
import AssetDashboardPage from '@/pages/AssetDashboardPage'
import AssetFormPage from '@/pages/AssetFormPage'
import AssetDetailPage from '@/pages/AssetDetailPage'
import { AppLayout } from '@/components/Layout'
import { assetService } from '@/services/assetService'

// Mock the asset service
jest.mock('@/services/assetService')
const mockedAssetService = assetService as jest.Mocked<typeof assetService>

// Mock antd message
jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  message: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  },
}))

// Mock Chart.js
jest.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="line-chart">Line Chart</div>,
  Bar: () => <div data-testid="bar-chart">Bar Chart</div>,
  Doughnut: () => <div data-testid="doughnut-chart">Doughnut Chart</div>,
}))

jest.mock('chart.js', () => ({
  Chart: { register: jest.fn() },
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

// Full application component for E2E testing
const TestApp: React.FC = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, cacheTime: 0 },
      mutations: { retry: false },
    },
  })

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppLayout>
          <Routes>
            <Route path="/" element={<AssetDashboardPage />} />
            <Route path="/dashboard" element={<AssetDashboardPage />} />
            <Route path="/assets/new" element={<AssetFormPage />} />
            <Route path="/assets/:id" element={<AssetDetailPage />} />
            <Route path="/assets/:id/edit" element={<AssetFormPage />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

const mockDashboardData = {
  totalAssets: 150,
  totalArea: 500000,
  totalRentedArea: 425000,
  overallOccupancyRate: 85.0,
  recentAssets: [
    {
      id: '1',
      property_name: '测试资产1',
      ownership_entity: '测试公司1',
      created_at: '2024-01-15T00:00:00Z',
    },
    {
      id: '2',
      property_name: '测试资产2',
      ownership_entity: '测试公司2',
      created_at: '2024-01-14T00:00:00Z',
    },
  ],
}

const mockOccupancyData = {
  overall_rate: 85.5,
  trend: 'up' as const,
  trend_percentage: 2.3,
  by_property_nature: [],
  by_ownership_entity: [],
  monthly_trend: [],
  top_performers: [],
  low_performers: [],
}

const mockAreaData = {
  total_area: 500000,
  rented_area: 425000,
  vacant_area: 75000,
  by_property_nature: [],
  by_ownership_entity: [],
}

const mockDistributionData = {
  by_property_nature: [],
  by_ownership_status: [],
  by_usage_status: [],
  by_ownership_entity: [],
}

describe('Asset Management E2E Workflow', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
    
    // Setup default mock responses
    mockedAssetService.getDashboardStats.mockResolvedValue(mockDashboardData)
    mockedAssetService.getOccupancyRateStats.mockResolvedValue(mockOccupancyData)
    mockedAssetService.getAreaStats.mockResolvedValue(mockAreaData)
    mockedAssetService.getAssetDistribution.mockResolvedValue(mockDistributionData)
  })

  describe('Complete Asset Creation Workflow', () => {
    it('allows user to create a new asset from dashboard', async () => {
      // Mock successful asset creation
      const newAsset = {
        ...mockAssetData.basic,
        id: '999',
        property_name: '新创建的资产',
        ownership_entity: '新公司',
        address: '新地址123号',
      }
      mockedAssetService.createAsset.mockResolvedValue(newAsset)

      render(<TestApp />)

      // 1. Start from dashboard
      await waitFor(() => {
        expect(screen.getByText('资产概览')).toBeInTheDocument()
      })

      // 2. Navigate to create asset page
      const createButton = screen.getByRole('button', { name: /新增资产/ })
      await user.click(createButton)

      // 3. Fill out the asset form
      await waitFor(() => {
        expect(screen.getByText('新增资产')).toBeInTheDocument()
      })

      // Fill required fields
      await user.type(screen.getByLabelText(/物业名称/), '新创建的资产')
      await user.type(screen.getByLabelText(/权属方/), '新公司')
      await user.type(screen.getByLabelText(/所在地址/), '新地址123号')

      // Select dropdown values
      const ownershipStatusSelect = screen.getByLabelText(/确权状态/)
      await user.click(ownershipStatusSelect)
      await user.click(screen.getByText('已确权'))

      const propertyNatureSelect = screen.getByLabelText(/物业性质/)
      await user.click(propertyNatureSelect)
      await user.click(screen.getByText('经营类'))

      const usageStatusSelect = screen.getByLabelText(/使用状态/)
      await user.click(usageStatusSelect)
      await user.click(screen.getByText('出租'))

      // Fill optional fields
      await user.type(screen.getByLabelText(/实际物业面积/), '1000')
      await user.type(screen.getByLabelText(/可出租面积/), '800')
      await user.type(screen.getByLabelText(/已出租面积/), '600')

      // 4. Submit the form
      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      // 5. Verify API call and success message
      await waitFor(() => {
        expect(mockedAssetService.createAsset).toHaveBeenCalledWith(
          expect.objectContaining({
            property_name: '新创建的资产',
            ownership_entity: '新公司',
            address: '新地址123号',
            ownership_status: '已确权',
            property_nature: '经营类',
            usage_status: '出租',
            actual_property_area: 1000,
            rentable_area: 800,
            rented_area: 600,
          })
        )
      })

      expect(message.success).toHaveBeenCalledWith('资产创建成功')

      // 6. Should navigate back to asset list
      expect(window.location.pathname).toBe('/assets')
    })
  })

  describe('Asset View and Edit Workflow', () => {
    it('allows user to view and edit an existing asset', async () => {
      const existingAsset = mockAssetData.basic
      const updatedAsset = { ...existingAsset, property_name: '更新后的资产名称' }

      mockedAssetService.getAsset.mockResolvedValue(existingAsset)
      mockedAssetService.updateAsset.mockResolvedValue(updatedAsset)
      mockedAssetService.getAssetHistory.mockResolvedValue({
        data: mockAssetData.history,
        total: 2,
      })

      render(<TestApp />)

      // 1. Navigate to asset detail page
      window.history.pushState({}, '', '/assets/1')

      await waitFor(() => {
        expect(screen.getByText('测试资产')).toBeInTheDocument()
      })

      // 2. Verify asset details are displayed
      expect(screen.getByText('测试公司')).toBeInTheDocument()
      expect(screen.getByText('测试地址123号')).toBeInTheDocument()
      expect(screen.getByText('已确权')).toBeInTheDocument()
      expect(screen.getByText('经营类')).toBeInTheDocument()

      // 3. Click edit button
      const editButton = screen.getByRole('button', { name: /编辑资产/ })
      await user.click(editButton)

      // 4. Should navigate to edit page
      await waitFor(() => {
        expect(screen.getByText('编辑资产')).toBeInTheDocument()
      })

      // 5. Form should be pre-populated
      expect(screen.getByDisplayValue('测试资产')).toBeInTheDocument()
      expect(screen.getByDisplayValue('测试公司')).toBeInTheDocument()

      // 6. Make changes
      const propertyNameInput = screen.getByDisplayValue('测试资产')
      await user.clear(propertyNameInput)
      await user.type(propertyNameInput, '更新后的资产名称')

      // 7. Submit changes
      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      // 8. Verify update API call
      await waitFor(() => {
        expect(mockedAssetService.updateAsset).toHaveBeenCalledWith(
          '1',
          expect.objectContaining({
            property_name: '更新后的资产名称',
          })
        )
      })

      expect(message.success).toHaveBeenCalledWith('资产更新成功')

      // 9. Should navigate back to detail page
      expect(window.location.pathname).toBe('/assets/1')
    })
  })

  describe('Asset Search and Filter Workflow', () => {
    it('allows user to search and filter assets', async () => {
      const searchResults = {
        data: mockAssetData.list(3),
        total: 3,
        page: 1,
        limit: 20,
      }

      mockedAssetService.searchAssets.mockResolvedValue(searchResults)

      render(<TestApp />)

      // Navigate to asset list page (assuming it exists)
      window.history.pushState({}, '', '/assets')

      // 1. Enter search term
      const searchInput = screen.getByPlaceholderText(/搜索资产/)
      await user.type(searchInput, '测试资产')

      // 2. Apply filters
      const propertyNatureFilter = screen.getByLabelText(/物业性质/)
      await user.click(propertyNatureFilter)
      await user.click(screen.getByText('经营类'))

      const ownershipStatusFilter = screen.getByLabelText(/确权状态/)
      await user.click(ownershipStatusFilter)
      await user.click(screen.getByText('已确权'))

      // 3. Execute search
      const searchButton = screen.getByRole('button', { name: /搜索/ })
      await user.click(searchButton)

      // 4. Verify search API call
      await waitFor(() => {
        expect(mockedAssetService.searchAssets).toHaveBeenCalledWith(
          expect.objectContaining({
            keyword: '测试资产',
            property_nature: '经营类',
            ownership_status: '已确权',
          })
        )
      })

      // 5. Verify search results are displayed
      expect(screen.getByText('测试资产1')).toBeInTheDocument()
      expect(screen.getByText('测试资产2')).toBeInTheDocument()
      expect(screen.getByText('测试资产3')).toBeInTheDocument()
    })
  })

  describe('Asset Deletion Workflow', () => {
    it('allows user to delete an asset with confirmation', async () => {
      const existingAsset = mockAssetData.basic

      mockedAssetService.getAsset.mockResolvedValue(existingAsset)
      mockedAssetService.deleteAsset.mockResolvedValue(undefined)
      mockedAssetService.getAssetHistory.mockResolvedValue({
        data: [],
        total: 0,
      })

      render(<TestApp />)

      // 1. Navigate to asset detail page
      window.history.pushState({}, '', '/assets/1')

      await waitFor(() => {
        expect(screen.getByText('测试资产')).toBeInTheDocument()
      })

      // 2. Click more actions dropdown
      const moreButton = screen.getByRole('button', { name: /更多操作/ })
      await user.click(moreButton)

      // 3. Click delete option
      const deleteOption = screen.getByText('删除资产')
      await user.click(deleteOption)

      // 4. Confirm deletion in modal
      await waitFor(() => {
        expect(screen.getByText('确认删除')).toBeInTheDocument()
      })

      expect(screen.getByText('确定要删除这个资产吗？此操作不可撤销。')).toBeInTheDocument()

      const confirmButton = screen.getByRole('button', { name: /确认删除/ })
      await user.click(confirmButton)

      // 5. Verify deletion API call
      await waitFor(() => {
        expect(mockedAssetService.deleteAsset).toHaveBeenCalledWith('1')
      })

      expect(message.success).toHaveBeenCalledWith('资产删除成功')

      // 6. Should navigate back to asset list
      expect(window.location.pathname).toBe('/assets')
    })

    it('allows user to cancel deletion', async () => {
      const existingAsset = mockAssetData.basic

      mockedAssetService.getAsset.mockResolvedValue(existingAsset)
      mockedAssetService.getAssetHistory.mockResolvedValue({
        data: [],
        total: 0,
      })

      render(<TestApp />)

      // Navigate to asset detail page
      window.history.pushState({}, '', '/assets/1')

      await waitFor(() => {
        expect(screen.getByText('测试资产')).toBeInTheDocument()
      })

      // Click more actions and delete
      const moreButton = screen.getByRole('button', { name: /更多操作/ })
      await user.click(moreButton)

      const deleteOption = screen.getByText('删除资产')
      await user.click(deleteOption)

      // Cancel deletion
      await waitFor(() => {
        expect(screen.getByText('确认删除')).toBeInTheDocument()
      })

      const cancelButton = screen.getByRole('button', { name: /取消/ })
      await user.click(cancelButton)

      // Should not call delete API
      expect(mockedAssetService.deleteAsset).not.toHaveBeenCalled()

      // Should remain on detail page
      expect(screen.getByText('测试资产')).toBeInTheDocument()
    })
  })

  describe('Error Handling Workflows', () => {
    it('handles network errors gracefully throughout the workflow', async () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {})

      // Mock API failures
      mockedAssetService.getDashboardStats.mockRejectedValue(new Error('Network Error'))
      mockedAssetService.createAsset.mockRejectedValue(new Error('Creation Failed'))

      render(<TestApp />)

      // 1. Dashboard should show error state
      await waitFor(() => {
        expect(screen.getByText('数据加载失败')).toBeInTheDocument()
      })

      // 2. Try to create asset
      const createButton = screen.getByRole('button', { name: /新增资产/ })
      await user.click(createButton)

      await waitFor(() => {
        expect(screen.getByText('新增资产')).toBeInTheDocument()
      })

      // Fill form and submit
      await user.type(screen.getByLabelText(/物业名称/), '测试资产')
      await user.type(screen.getByLabelText(/权属方/), '测试公司')
      await user.type(screen.getByLabelText(/所在地址/), '测试地址')

      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      // 3. Should show error message
      await waitFor(() => {
        expect(message.error).toHaveBeenCalledWith(
          expect.stringContaining('创建失败')
        )
      })

      consoleError.mockRestore()
    })

    it('handles validation errors in forms', async () => {
      render(<TestApp />)

      // Navigate to create asset page
      const createButton = screen.getByRole('button', { name: /新增资产/ })
      await user.click(createButton)

      await waitFor(() => {
        expect(screen.getByText('新增资产')).toBeInTheDocument()
      })

      // Try to submit empty form
      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText('请输入物业名称')).toBeInTheDocument()
        expect(screen.getByText('请输入权属方')).toBeInTheDocument()
        expect(screen.getByText('请输入所在地址')).toBeInTheDocument()
      })

      // Should not call API
      expect(mockedAssetService.createAsset).not.toHaveBeenCalled()
    })
  })

  describe('Responsive Design and Accessibility', () => {
    it('works correctly on mobile devices', async () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })

      render(<TestApp />)

      await waitFor(() => {
        expect(screen.getByText('资产概览')).toBeInTheDocument()
      })

      // Mobile menu should be available
      const mobileMenuButton = screen.getByRole('button', { name: /菜单/ })
      expect(mobileMenuButton).toBeInTheDocument()

      await user.click(mobileMenuButton)

      // Mobile navigation should appear
      expect(screen.getByRole('navigation')).toBeInTheDocument()
    })

    it('supports keyboard navigation throughout the workflow', async () => {
      render(<TestApp />)

      await waitFor(() => {
        expect(screen.getByText('资产概览')).toBeInTheDocument()
      })

      // Tab through dashboard elements
      await user.tab()
      expect(screen.getByRole('button', { name: /新增资产/ })).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('button', { name: /刷新/ })).toHaveFocus()

      // Enter key should activate buttons
      await user.keyboard('{Enter}')
      
      // Should navigate to create page
      await waitFor(() => {
        expect(screen.getByText('新增资产')).toBeInTheDocument()
      })
    })
  })
})

// Helper function to render the test app
function render(component: React.ReactElement) {
  return renderWithProviders(component)
}