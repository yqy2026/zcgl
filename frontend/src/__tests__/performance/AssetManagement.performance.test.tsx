import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { renderWithProviders, measurePerformance, mockAssetData } from '@/__tests__/utils/testUtils'
import AssetDashboardPage from '@/pages/AssetDashboardPage'
import AssetFormPage from '@/pages/AssetFormPage'
import AssetDetailPage from '@/pages/AssetDetailPage'
import { AssetSearch } from '@/components/Asset'
import { assetService } from '@/services/assetService'

// Mock the asset service
jest.mock('@/services/assetService')
const mockedAssetService = assetService as jest.Mocked<typeof assetService>

// Mock Chart.js for performance tests
jest.mock('react-chartjs-2', () => ({
  Line: React.memo(() => <div data-testid="line-chart">Line Chart</div>),
  Bar: React.memo(() => <div data-testid="bar-chart">Bar Chart</div>),
  Doughnut: React.memo(() => <div data-testid="doughnut-chart">Doughnut Chart</div>),
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

// Performance test thresholds (in milliseconds)
const PERFORMANCE_THRESHOLDS = {
  COMPONENT_RENDER: 100,
  DATA_LOADING: 500,
  FORM_SUBMISSION: 300,
  SEARCH_RESPONSE: 200,
  LARGE_LIST_RENDER: 1000,
}

describe('Asset Management Performance Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Component Rendering Performance', () => {
    it('renders AssetDashboardPage within performance threshold', async () => {
      // Mock fast API responses
      mockedAssetService.getDashboardStats.mockResolvedValue({
        totalAssets: 150,
        totalArea: 500000,
        totalRentedArea: 425000,
        overallOccupancyRate: 85.0,
        recentAssets: mockAssetData.list(5),
      })
      mockedAssetService.getOccupancyRateStats.mockResolvedValue(mockAssetData.statistics.occupancyRate)
      mockedAssetService.getAreaStats.mockResolvedValue({
        total_area: 500000,
        rented_area: 425000,
        vacant_area: 75000,
        by_property_nature: [],
        by_ownership_entity: [],
      })
      mockedAssetService.getAssetDistribution.mockResolvedValue({
        by_property_nature: [],
        by_ownership_status: [],
        by_usage_status: [],
        by_ownership_entity: [],
      })

      const renderTime = await measurePerformance(async () => {
        renderWithProviders(<AssetDashboardPage />)
        
        await waitFor(() => {
          expect(screen.getByText('资产概览')).toBeInTheDocument()
        })
      })

      expect(renderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.COMPONENT_RENDER)
    })

    it('renders AssetFormPage within performance threshold', async () => {
      const renderTime = await measurePerformance(async () => {
        renderWithProviders(<AssetFormPage />)
        
        await waitFor(() => {
          expect(screen.getByText('新增资产')).toBeInTheDocument()
        })
      })

      expect(renderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.COMPONENT_RENDER)
    })

    it('renders AssetDetailPage within performance threshold', async () => {
      mockedAssetService.getAsset.mockResolvedValue(mockAssetData.basic)
      mockedAssetService.getAssetHistory.mockResolvedValue({
        data: mockAssetData.history,
        total: 2,
      })

      const renderTime = await measurePerformance(async () => {
        renderWithProviders(<AssetDetailPage />)
        
        await waitFor(() => {
          expect(screen.getByText('测试资产')).toBeInTheDocument()
        })
      })

      expect(renderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.COMPONENT_RENDER)
    })
  })

  describe('Data Loading Performance', () => {
    it('loads dashboard data within performance threshold', async () => {
      const mockData = {
        totalAssets: 1000,
        totalArea: 5000000,
        totalRentedArea: 4250000,
        overallOccupancyRate: 85.0,
        recentAssets: mockAssetData.list(10),
      }

      // Simulate realistic API delay
      mockedAssetService.getDashboardStats.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockData), 100))
      )
      mockedAssetService.getOccupancyRateStats.mockResolvedValue(mockAssetData.statistics.occupancyRate)
      mockedAssetService.getAreaStats.mockResolvedValue({
        total_area: 5000000,
        rented_area: 4250000,
        vacant_area: 750000,
        by_property_nature: [],
        by_ownership_entity: [],
      })
      mockedAssetService.getAssetDistribution.mockResolvedValue({
        by_property_nature: [],
        by_ownership_status: [],
        by_usage_status: [],
        by_ownership_entity: [],
      })

      const loadTime = await measurePerformance(async () => {
        renderWithProviders(<AssetDashboardPage />)
        
        await waitFor(() => {
          expect(screen.getByText('1000')).toBeInTheDocument()
        }, { timeout: 1000 })
      })

      expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.DATA_LOADING)
    })

    it('loads asset detail data within performance threshold', async () => {
      // Simulate realistic API delay
      mockedAssetService.getAsset.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockAssetData.basic), 50))
      )
      mockedAssetService.getAssetHistory.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          data: mockAssetData.history,
          total: 2,
        }), 50))
      )

      const loadTime = await measurePerformance(async () => {
        renderWithProviders(<AssetDetailPage />)
        
        await waitFor(() => {
          expect(screen.getByText('测试资产')).toBeInTheDocument()
        }, { timeout: 1000 })
      })

      expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.DATA_LOADING)
    })
  })

  describe('Form Performance', () => {
    it('handles form submission within performance threshold', async () => {
      mockedAssetService.createAsset.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockAssetData.basic), 100))
      )

      renderWithProviders(<AssetFormPage />)

      await waitFor(() => {
        expect(screen.getByText('新增资产')).toBeInTheDocument()
      })

      // Fill form quickly
      const propertyNameInput = screen.getByLabelText(/物业名称/)
      const ownershipEntityInput = screen.getByLabelText(/权属方/)
      const addressInput = screen.getByLabelText(/所在地址/)

      propertyNameInput.focus()
      ;(propertyNameInput as HTMLInputElement).value = '性能测试资产'
      propertyNameInput.dispatchEvent(new Event('input', { bubbles: true }))

      ownershipEntityInput.focus()
      ;(ownershipEntityInput as HTMLInputElement).value = '性能测试公司'
      ownershipEntityInput.dispatchEvent(new Event('input', { bubbles: true }))

      addressInput.focus()
      ;(addressInput as HTMLInputElement).value = '性能测试地址'
      addressInput.dispatchEvent(new Event('input', { bubbles: true }))

      const submitTime = await measurePerformance(async () => {
        const submitButton = screen.getByRole('button', { name: /保存/ })
        submitButton.click()

        await waitFor(() => {
          expect(mockedAssetService.createAsset).toHaveBeenCalled()
        }, { timeout: 1000 })
      })

      expect(submitTime).toBeLessThan(PERFORMANCE_THRESHOLDS.FORM_SUBMISSION)
    })

    it('handles form validation within performance threshold', async () => {
      renderWithProviders(<AssetFormPage />)

      await waitFor(() => {
        expect(screen.getByText('新增资产')).toBeInTheDocument()
      })

      const validationTime = await measurePerformance(async () => {
        const submitButton = screen.getByRole('button', { name: /保存/ })
        submitButton.click()

        await waitFor(() => {
          expect(screen.getByText('请输入物业名称')).toBeInTheDocument()
        })
      })

      expect(validationTime).toBeLessThan(PERFORMANCE_THRESHOLDS.FORM_SUBMISSION)
    })
  })

  describe('Search Performance', () => {
    it('handles search requests within performance threshold', async () => {
      const searchResults = {
        data: mockAssetData.list(20),
        total: 20,
        page: 1,
        limit: 20,
      }

      mockedAssetService.searchAssets.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(searchResults), 50))
      )

      const searchTime = await measurePerformance(async () => {
        renderWithProviders(<AssetSearch onSearch={jest.fn()} />)

        const searchInput = screen.getByPlaceholderText(/搜索资产/)
        searchInput.focus()
        ;(searchInput as HTMLInputElement).value = '测试'
        searchInput.dispatchEvent(new Event('input', { bubbles: true }))

        const searchButton = screen.getByRole('button', { name: /搜索/ })
        searchButton.click()

        await waitFor(() => {
          expect(mockedAssetService.searchAssets).toHaveBeenCalled()
        }, { timeout: 500 })
      })

      expect(searchTime).toBeLessThan(PERFORMANCE_THRESHOLDS.SEARCH_RESPONSE)
    })

    it('handles debounced search within performance threshold', async () => {
      jest.useFakeTimers()

      const searchResults = {
        data: mockAssetData.list(10),
        total: 10,
        page: 1,
        limit: 20,
      }

      mockedAssetService.searchAssets.mockResolvedValue(searchResults)

      renderWithProviders(<AssetSearch onSearch={jest.fn()} />)

      const searchInput = screen.getByPlaceholderText(/搜索资产/)

      const debounceTime = await measurePerformance(async () => {
        // Type multiple characters quickly
        searchInput.focus()
        ;(searchInput as HTMLInputElement).value = 't'
        searchInput.dispatchEvent(new Event('input', { bubbles: true }))

        ;(searchInput as HTMLInputElement).value = 'te'
        searchInput.dispatchEvent(new Event('input', { bubbles: true }))

        ;(searchInput as HTMLInputElement).value = 'tes'
        searchInput.dispatchEvent(new Event('input', { bubbles: true }))

        ;(searchInput as HTMLInputElement).value = 'test'
        searchInput.dispatchEvent(new Event('input', { bubbles: true }))

        // Fast forward debounce delay
        jest.advanceTimersByTime(300)

        await waitFor(() => {
          expect(mockedAssetService.searchAssets).toHaveBeenCalledTimes(1)
        })
      })

      expect(debounceTime).toBeLessThan(PERFORMANCE_THRESHOLDS.SEARCH_RESPONSE)

      jest.useRealTimers()
    })
  })

  describe('Large Dataset Performance', () => {
    it('renders large asset list within performance threshold', async () => {
      const largeDataset = mockAssetData.list(1000)
      const searchResults = {
        data: largeDataset,
        total: 1000,
        page: 1,
        limit: 1000,
      }

      mockedAssetService.searchAssets.mockResolvedValue(searchResults)

      const renderTime = await measurePerformance(async () => {
        renderWithProviders(<AssetSearch onSearch={jest.fn()} />)

        const searchButton = screen.getByRole('button', { name: /搜索/ })
        searchButton.click()

        await waitFor(() => {
          expect(screen.getByText('测试资产1')).toBeInTheDocument()
        }, { timeout: 2000 })
      })

      expect(renderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.LARGE_LIST_RENDER)
    })

    it('handles pagination efficiently', async () => {
      const pageSize = 20
      const totalItems = 1000
      const totalPages = Math.ceil(totalItems / pageSize)

      // Mock paginated responses
      for (let page = 1; page <= Math.min(totalPages, 5); page++) {
        const startIndex = (page - 1) * pageSize
        const endIndex = Math.min(startIndex + pageSize, totalItems)
        const pageData = mockAssetData.list(endIndex - startIndex)

        mockedAssetService.searchAssets.mockResolvedValueOnce({
          data: pageData,
          total: totalItems,
          page,
          limit: pageSize,
        })
      }

      const paginationTime = await measurePerformance(async () => {
        renderWithProviders(<AssetSearch onSearch={jest.fn()} />)

        // Load first page
        const searchButton = screen.getByRole('button', { name: /搜索/ })
        searchButton.click()

        await waitFor(() => {
          expect(screen.getByText('测试资产1')).toBeInTheDocument()
        })

        // Navigate through pages
        for (let page = 2; page <= 5; page++) {
          const nextButton = screen.getByRole('button', { name: /下一页/ })
          nextButton.click()

          await waitFor(() => {
            expect(mockedAssetService.searchAssets).toHaveBeenCalledWith(
              expect.objectContaining({ page })
            )
          })
        }
      })

      expect(paginationTime).toBeLessThan(PERFORMANCE_THRESHOLDS.LARGE_LIST_RENDER)
    })
  })

  describe('Memory Usage Performance', () => {
    it('does not cause memory leaks during component lifecycle', async () => {
      const initialMemory = (performance as any).memory?.usedJSHeapSize || 0

      // Render and unmount components multiple times
      for (let i = 0; i < 10; i++) {
        const { unmount } = renderWithProviders(<AssetFormPage />)
        
        await waitFor(() => {
          expect(screen.getByText('新增资产')).toBeInTheDocument()
        })

        unmount()
      }

      // Allow garbage collection
      await new Promise(resolve => setTimeout(resolve, 100))

      const finalMemory = (performance as any).memory?.usedJSHeapSize || 0
      const memoryIncrease = finalMemory - initialMemory

      // Memory increase should be reasonable (less than 10MB)
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024)
    })

    it('cleans up event listeners properly', async () => {
      const addEventListenerSpy = jest.spyOn(window, 'addEventListener')
      const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener')

      const { unmount } = renderWithProviders(<AssetDashboardPage />)

      await waitFor(() => {
        expect(screen.getByText('资产概览')).toBeInTheDocument()
      })

      const addedListeners = addEventListenerSpy.mock.calls.length
      
      unmount()

      const removedListeners = removeEventListenerSpy.mock.calls.length

      // Should remove at least as many listeners as were added
      expect(removedListeners).toBeGreaterThanOrEqual(addedListeners)

      addEventListenerSpy.mockRestore()
      removeEventListenerSpy.mockRestore()
    })
  })

  describe('Bundle Size Performance', () => {
    it('loads components with code splitting efficiently', async () => {
      // Mock dynamic imports
      const mockImport = jest.fn().mockResolvedValue({
        default: () => <div>Lazy Component</div>
      })

      // Simulate lazy loading
      const loadTime = await measurePerformance(async () => {
        await mockImport()
      })

      expect(loadTime).toBeLessThan(100) // Should load quickly
      expect(mockImport).toHaveBeenCalled()
    })
  })

  describe('Concurrent Operations Performance', () => {
    it('handles multiple simultaneous API calls efficiently', async () => {
      // Mock multiple API endpoints
      mockedAssetService.getDashboardStats.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          totalAssets: 150,
          totalArea: 500000,
          totalRentedArea: 425000,
          overallOccupancyRate: 85.0,
          recentAssets: [],
        }), 100))
      )
      mockedAssetService.getOccupancyRateStats.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockAssetData.statistics.occupancyRate), 100))
      )
      mockedAssetService.getAreaStats.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          total_area: 500000,
          rented_area: 425000,
          vacant_area: 75000,
          by_property_nature: [],
          by_ownership_entity: [],
        }), 100))
      )

      const concurrentTime = await measurePerformance(async () => {
        renderWithProviders(<AssetDashboardPage />)

        // All API calls should complete concurrently
        await waitFor(() => {
          expect(screen.getByText('150')).toBeInTheDocument()
        }, { timeout: 1000 })
      })

      // Should complete in roughly the time of the slowest call (100ms) plus overhead
      expect(concurrentTime).toBeLessThan(300)
    })
  })
})