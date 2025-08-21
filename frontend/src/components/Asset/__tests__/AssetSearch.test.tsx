import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi, describe, it, expect, beforeEach } from 'vitest'

import AssetSearch from '../AssetSearch'
import { assetService } from '@/services/assetService'
import type { AssetSearchParams } from '@/types/asset'

// Mock the asset service
vi.mock('@/services/assetService', () => ({
  assetService: {
    getOwnershipEntities: vi.fn(),
    getManagementEntities: vi.fn(),
    getBusinessCategories: vi.fn(),
  },
}))

// Mock the search history hook
vi.mock('@/hooks/useSearchHistory', () => ({
  useSearchHistory: () => ({
    searchHistory: [],
    addSearchHistory: vi.fn(),
    removeSearchHistory: vi.fn(),
    clearSearchHistory: vi.fn(),
    updateSearchHistoryName: vi.fn(),
  }),
}))

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('AssetSearch', () => {
  const mockOnSearch = vi.fn()
  const mockOnReset = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock service responses
    vi.mocked(assetService.getOwnershipEntities).mockResolvedValue(['权属方1', '权属方2'])
    vi.mocked(assetService.getManagementEntities).mockResolvedValue(['管理方1', '管理方2'])
    vi.mocked(assetService.getBusinessCategories).mockResolvedValue(['商业', '办公'])
  })

  it('renders search form correctly', async () => {
    renderWithProviders(
      <AssetSearch onSearch={mockOnSearch} onReset={mockOnReset} />
    )

    // Check basic search fields are present
    expect(screen.getByPlaceholderText(/物业名称、地址、权属方/)).toBeInTheDocument()
    expect(screen.getByText('确权状态')).toBeInTheDocument()
    expect(screen.getByText('物业性质')).toBeInTheDocument()
    expect(screen.getByText('使用状态')).toBeInTheDocument()
  })

  it('performs basic search', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(
      <AssetSearch onSearch={mockOnSearch} onReset={mockOnReset} />
    )

    // Enter search keyword
    const searchInput = screen.getByPlaceholderText(/物业名称、地址、权属方/)
    await user.type(searchInput, '测试物业')

    // Select ownership status
    await user.click(screen.getByLabelText('确权状态'))
    await user.click(screen.getByText('已确权'))

    // Click search button
    const searchButton = screen.getByRole('button', { name: /搜索/ })
    await user.click(searchButton)

    // Check that onSearch is called with correct parameters
    expect(mockOnSearch).toHaveBeenCalledWith({
      search: '测试物业',
      ownership_status: '已确权',
    })
  })

  it('expands and shows advanced search fields', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(
      <AssetSearch onSearch={mockOnSearch} onReset={mockOnReset} />
    )

    // Click expand button
    const expandButton = screen.getByRole('button', { name: /展开/ })
    await user.click(expandButton)

    // Check that advanced fields appear
    await waitFor(() => {
      expect(screen.getByText('权属方')).toBeInTheDocument()
      expect(screen.getByText('经营管理方')).toBeInTheDocument()
      expect(screen.getByText('业态类别')).toBeInTheDocument()
    })
  })

  it('uses quick filter buttons', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(
      <AssetSearch onSearch={mockOnSearch} onReset={mockOnReset} />
    )

    // Click quick filter button
    const quickFilterButton = screen.getByRole('button', { name: '经营类物业' })
    await user.click(quickFilterButton)

    // Check that search is triggered with correct filter
    expect(mockOnSearch).toHaveBeenCalledWith({
      property_nature: '经营类',
    })
  })

  it('resets search form', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(
      <AssetSearch onSearch={mockOnSearch} onReset={mockOnReset} />
    )

    // Fill in some search criteria
    const searchInput = screen.getByPlaceholderText(/物业名称、地址、权属方/)
    await user.type(searchInput, '测试')

    // Click reset button
    const resetButton = screen.getByRole('button', { name: /重置/ })
    await user.click(resetButton)

    // Check that form is reset and onReset is called
    expect(searchInput).toHaveValue('')
    expect(mockOnReset).toHaveBeenCalled()
  })

  it('handles area range slider', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(
      <AssetSearch onSearch={mockOnSearch} onReset={mockOnReset} />
    )

    // Expand advanced search
    const expandButton = screen.getByRole('button', { name: /展开/ })
    await user.click(expandButton)

    // Find area range inputs
    await waitFor(() => {
      const minAreaInput = screen.getByLabelText('最小面积')
      const maxAreaInput = screen.getByLabelText('最大面积')
      
      expect(minAreaInput).toBeInTheDocument()
      expect(maxAreaInput).toBeInTheDocument()
    })
  })

  it('saves search conditions', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(
      <AssetSearch 
        onSearch={mockOnSearch} 
        onReset={mockOnReset}
        showSaveButton={true}
      />
    )

    // Fill in search criteria
    const searchInput = screen.getByPlaceholderText(/物业名称、地址、权属方/)
    await user.type(searchInput, '测试物业')

    // Click save button
    const saveButton = screen.getByRole('button', { name: /保存条件/ })
    await user.click(saveButton)

    // Check that save modal appears
    await waitFor(() => {
      expect(screen.getByText('保存搜索条件')).toBeInTheDocument()
    })
  })

  it('shows search history', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(
      <AssetSearch 
        onSearch={mockOnSearch} 
        onReset={mockOnReset}
        showHistoryButton={true}
      />
    )

    // Click history button
    const historyButton = screen.getByRole('button', { name: /搜索历史/ })
    await user.click(historyButton)

    // Check that history modal appears
    await waitFor(() => {
      expect(screen.getByText('搜索历史')).toBeInTheDocument()
    })
  })

  it('handles date range selection', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(
      <AssetSearch onSearch={mockOnSearch} onReset={mockOnReset} />
    )

    // Expand advanced search
    const expandButton = screen.getByRole('button', { name: /展开/ })
    await user.click(expandButton)

    // Check that date range picker is available
    await waitFor(() => {
      expect(screen.getByText('创建时间范围')).toBeInTheDocument()
    })
  })

  it('applies initial values correctly', () => {
    const initialValues = {
      search: '初始搜索',
      ownership_status: '已确权',
      property_nature: '经营类',
    }

    renderWithProviders(
      <AssetSearch 
        onSearch={mockOnSearch} 
        onReset={mockOnReset}
        initialValues={initialValues}
      />
    )

    // Check that initial values are applied
    const searchInput = screen.getByDisplayValue('初始搜索')
    expect(searchInput).toBeInTheDocument()
  })

  it('shows loading state during search', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(
      <AssetSearch 
        onSearch={mockOnSearch} 
        onReset={mockOnReset}
        loading={true}
      />
    )

    // Check that search button shows loading state
    const searchButton = screen.getByRole('button', { name: /搜索/ })
    expect(searchButton).toBeDisabled()
  })
})