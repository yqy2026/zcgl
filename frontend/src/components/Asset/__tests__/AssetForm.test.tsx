import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'

import AssetForm from '../AssetForm'
import { assetService } from '@/services/assetService'
import type { Asset } from '@/types/asset'

// Mock the asset service
vi.mock('@/services/assetService', () => ({
  assetService: {
    createAsset: vi.fn(),
    updateAsset: vi.fn(),
    getOwnershipEntities: vi.fn(),
    getManagementEntities: vi.fn(),
    getBusinessCategories: vi.fn(),
  },
}))

// Mock the form field visibility hook
vi.mock('@/hooks/useFormFieldVisibility', () => ({
  useFormFieldVisibility: () => ({
    isFieldVisible: vi.fn(() => true),
    getVisibleFields: vi.fn(() => []),
  }),
}))

const mockAsset: Asset = {
  id: '1',
  property_name: '测试物业',
  ownership_entity: '测试权属方',
  address: '测试地址',
  ownership_status: '已确权',
  property_nature: '经营类',
  usage_status: '出租',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('AssetForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock service responses
    vi.mocked(assetService.getOwnershipEntities).mockResolvedValue(['权属方1', '权属方2'])
    vi.mocked(assetService.getManagementEntities).mockResolvedValue(['管理方1', '管理方2'])
    vi.mocked(assetService.getBusinessCategories).mockResolvedValue(['商业', '办公'])
  })

  it('renders form fields correctly', async () => {
    renderWithProviders(<AssetForm mode="create" />)

    // Check required fields are present
    expect(screen.getByLabelText(/物业名称/)).toBeInTheDocument()
    expect(screen.getByLabelText(/权属方/)).toBeInTheDocument()
    expect(screen.getByLabelText(/所在地址/)).toBeInTheDocument()
    expect(screen.getByLabelText(/确权状态/)).toBeInTheDocument()
    expect(screen.getByLabelText(/物业性质/)).toBeInTheDocument()
    expect(screen.getByLabelText(/使用状态/)).toBeInTheDocument()
  })

  it('validates required fields', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AssetForm mode="create" />)

    // Try to submit without filling required fields
    const submitButton = screen.getByRole('button', { name: /保存/ })
    await user.click(submitButton)

    // Check validation messages appear
    await waitFor(() => {
      expect(screen.getByText(/物业名称不能为空/)).toBeInTheDocument()
    })
  })

  it('submits form with valid data in create mode', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    
    vi.mocked(assetService.createAsset).mockResolvedValue(mockAsset)

    renderWithProviders(
      <AssetForm mode="create" onSuccess={onSuccess} />
    )

    // Fill in required fields
    await user.type(screen.getByLabelText(/物业名称/), '新物业')
    await user.type(screen.getByLabelText(/权属方/), '新权属方')
    await user.type(screen.getByLabelText(/所在地址/), '新地址')
    
    // Select dropdown values
    await user.click(screen.getByLabelText(/确权状态/))
    await user.click(screen.getByText('已确权'))
    
    await user.click(screen.getByLabelText(/物业性质/))
    await user.click(screen.getByText('经营类'))
    
    await user.click(screen.getByLabelText(/使用状态/))
    await user.click(screen.getByText('出租'))

    // Submit form
    const submitButton = screen.getByRole('button', { name: /保存/ })
    await user.click(submitButton)

    await waitFor(() => {
      expect(assetService.createAsset).toHaveBeenCalledWith(
        expect.objectContaining({
          property_name: '新物业',
          ownership_entity: '新权属方',
          address: '新地址',
          ownership_status: '已确权',
          property_nature: '经营类',
          usage_status: '出租',
        })
      )
      expect(onSuccess).toHaveBeenCalledWith(mockAsset)
    })
  })

  it('submits form with valid data in edit mode', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    
    vi.mocked(assetService.updateAsset).mockResolvedValue(mockAsset)

    renderWithProviders(
      <AssetForm 
        mode="edit" 
        initialData={mockAsset} 
        onSuccess={onSuccess} 
      />
    )

    // Modify a field
    const nameInput = screen.getByDisplayValue('测试物业')
    await user.clear(nameInput)
    await user.type(nameInput, '修改后的物业')

    // Submit form
    const submitButton = screen.getByRole('button', { name: /保存/ })
    await user.click(submitButton)

    await waitFor(() => {
      expect(assetService.updateAsset).toHaveBeenCalledWith(
        '1',
        expect.objectContaining({
          property_name: '修改后的物业',
        })
      )
      expect(onSuccess).toHaveBeenCalledWith(mockAsset)
    })
  })

  it('handles form submission errors', async () => {
    const user = userEvent.setup()
    const error = new Error('提交失败')
    
    vi.mocked(assetService.createAsset).mockRejectedValue(error)

    renderWithProviders(<AssetForm mode="create" />)

    // Fill in required fields
    await user.type(screen.getByLabelText(/物业名称/), '新物业')
    await user.type(screen.getByLabelText(/权属方/), '新权属方')
    await user.type(screen.getByLabelText(/所在地址/), '新地址')

    // Submit form
    const submitButton = screen.getByRole('button', { name: /保存/ })
    await user.click(submitButton)

    // Check error handling
    await waitFor(() => {
      expect(screen.getByText(/提交失败/)).toBeInTheDocument()
    })
  })

  it('shows dynamic fields based on property nature', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(<AssetForm mode="create" />)

    // Select 经营类 property nature
    await user.click(screen.getByLabelText(/物业性质/))
    await user.click(screen.getByText('经营类'))

    // Check that rental-related fields appear
    await waitFor(() => {
      expect(screen.getByLabelText(/可出租面积/)).toBeInTheDocument()
      expect(screen.getByLabelText(/已出租面积/)).toBeInTheDocument()
    })

    // Select 非经营类 property nature
    await user.click(screen.getByLabelText(/物业性质/))
    await user.click(screen.getByText('非经营类'))

    // Check that non-commercial area field appears
    await waitFor(() => {
      expect(screen.getByLabelText(/非经营物业面积/)).toBeInTheDocument()
    })
  })

  it('calculates occupancy rate automatically', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(<AssetForm mode="create" />)

    // Set property nature to 经营类
    await user.click(screen.getByLabelText(/物业性质/))
    await user.click(screen.getByText('经营类'))

    // Fill in area fields
    await user.type(screen.getByLabelText(/可出租面积/), '1000')
    await user.type(screen.getByLabelText(/已出租面积/), '800')

    // Check that occupancy rate is calculated
    await waitFor(() => {
      const occupancyRateField = screen.getByDisplayValue('80.00%')
      expect(occupancyRateField).toBeInTheDocument()
    })
  })

  it('resets form when reset button is clicked', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(<AssetForm mode="create" />)

    // Fill in some fields
    await user.type(screen.getByLabelText(/物业名称/), '测试物业')
    await user.type(screen.getByLabelText(/权属方/), '测试权属方')

    // Click reset button
    const resetButton = screen.getByRole('button', { name: /重置/ })
    await user.click(resetButton)

    // Check that fields are cleared
    expect(screen.getByLabelText(/物业名称/)).toHaveValue('')
    expect(screen.getByLabelText(/权属方/)).toHaveValue('')
  })

  it('shows help information when help button is clicked', async () => {
    const user = userEvent.setup()
    
    renderWithProviders(<AssetForm mode="create" />)

    // Click help button
    const helpButton = screen.getByRole('button', { name: /帮助/ })
    await user.click(helpButton)

    // Check that help modal appears
    await waitFor(() => {
      expect(screen.getByText(/表单填写说明/)).toBeInTheDocument()
    })
  })
})