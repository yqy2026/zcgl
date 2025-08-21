import React from 'react'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, mockAssetData } from '@/__tests__/utils/testUtils'
import AssetFormPage from '../AssetFormPage'
import { assetService } from '@/services/assetService'
import { message } from 'antd'

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

// Mock react-router-dom
const mockNavigate = jest.fn()
const mockParams = { id: undefined }

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => mockParams,
}))

describe('AssetFormPage', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
    mockParams.id = undefined
    mockNavigate.mockClear()
  })

  describe('Create Mode', () => {
    it('renders create form correctly', () => {
      renderWithProviders(<AssetFormPage />)

      expect(screen.getByText('新增资产')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /保存/ })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /取消/ })).toBeInTheDocument()
    })

    it('shows all required form fields', () => {
      renderWithProviders(<AssetFormPage />)

      // Check for required fields
      expect(screen.getByLabelText(/物业名称/)).toBeInTheDocument()
      expect(screen.getByLabelText(/权属方/)).toBeInTheDocument()
      expect(screen.getByLabelText(/所在地址/)).toBeInTheDocument()
      expect(screen.getByLabelText(/确权状态/)).toBeInTheDocument()
      expect(screen.getByLabelText(/物业性质/)).toBeInTheDocument()
      expect(screen.getByLabelText(/使用状态/)).toBeInTheDocument()
    })

    it('creates asset successfully with valid data', async () => {
      mockedAssetService.createAsset.mockResolvedValue(mockAssetData.basic)

      renderWithProviders(<AssetFormPage />)

      // Fill in required fields
      await user.type(screen.getByLabelText(/物业名称/), '新测试资产')
      await user.type(screen.getByLabelText(/权属方/), '新测试公司')
      await user.type(screen.getByLabelText(/所在地址/), '新测试地址456号')

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

      // Submit form
      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockedAssetService.createAsset).toHaveBeenCalledWith(
          expect.objectContaining({
            property_name: '新测试资产',
            ownership_entity: '新测试公司',
            address: '新测试地址456号',
            ownership_status: '已确权',
            property_nature: '经营类',
            usage_status: '出租',
          })
        )
      })

      expect(message.success).toHaveBeenCalledWith('资产创建成功')
      expect(mockNavigate).toHaveBeenCalledWith('/assets')
    })

    it('shows validation errors for empty required fields', async () => {
      renderWithProviders(<AssetFormPage />)

      // Try to submit without filling required fields
      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('请输入物业名称')).toBeInTheDocument()
        expect(screen.getByText('请输入权属方')).toBeInTheDocument()
        expect(screen.getByText('请输入所在地址')).toBeInTheDocument()
      })

      // Should not call API
      expect(mockedAssetService.createAsset).not.toHaveBeenCalled()
    })

    it('handles API errors during creation', async () => {
      mockedAssetService.createAsset.mockRejectedValue(
        new Error('创建失败')
      )

      renderWithProviders(<AssetFormPage />)

      // Fill in valid data
      await user.type(screen.getByLabelText(/物业名称/), '测试资产')
      await user.type(screen.getByLabelText(/权属方/), '测试公司')
      await user.type(screen.getByLabelText(/所在地址/), '测试地址')

      // Submit form
      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      await waitFor(() => {
        expect(message.error).toHaveBeenCalledWith(
          expect.stringContaining('创建失败')
        )
      })
    })

    it('navigates back when cancel button is clicked', async () => {
      renderWithProviders(<AssetFormPage />)

      const cancelButton = screen.getByRole('button', { name: /取消/ })
      await user.click(cancelButton)

      expect(mockNavigate).toHaveBeenCalledWith(-1)
    })
  })

  describe('Edit Mode', () => {
    beforeEach(() => {
      mockParams.id = '1'
    })

    it('renders edit form correctly', async () => {
      mockedAssetService.getAsset.mockResolvedValue(mockAssetData.basic)

      renderWithProviders(<AssetFormPage />)

      await waitFor(() => {
        expect(screen.getByText('编辑资产')).toBeInTheDocument()
      })

      expect(screen.getByRole('button', { name: /保存/ })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /取消/ })).toBeInTheDocument()
    })

    it('loads existing asset data', async () => {
      mockedAssetService.getAsset.mockResolvedValue(mockAssetData.basic)

      renderWithProviders(<AssetFormPage />)

      await waitFor(() => {
        expect(mockedAssetService.getAsset).toHaveBeenCalledWith('1')
      })

      // Check if form is populated with existing data
      expect(screen.getByDisplayValue('测试资产')).toBeInTheDocument()
      expect(screen.getByDisplayValue('测试公司')).toBeInTheDocument()
      expect(screen.getByDisplayValue('测试地址123号')).toBeInTheDocument()
    })

    it('updates asset successfully', async () => {
      const updatedAsset = { ...mockAssetData.basic, property_name: '更新后的资产' }
      
      mockedAssetService.getAsset.mockResolvedValue(mockAssetData.basic)
      mockedAssetService.updateAsset.mockResolvedValue(updatedAsset)

      renderWithProviders(<AssetFormPage />)

      await waitFor(() => {
        expect(screen.getByDisplayValue('测试资产')).toBeInTheDocument()
      })

      // Update property name
      const propertyNameInput = screen.getByDisplayValue('测试资产')
      await user.clear(propertyNameInput)
      await user.type(propertyNameInput, '更新后的资产')

      // Submit form
      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockedAssetService.updateAsset).toHaveBeenCalledWith(
          '1',
          expect.objectContaining({
            property_name: '更新后的资产',
          })
        )
      })

      expect(message.success).toHaveBeenCalledWith('资产更新成功')
      expect(mockNavigate).toHaveBeenCalledWith('/assets/1')
    })

    it('handles loading state when fetching asset data', () => {
      mockedAssetService.getAsset.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      renderWithProviders(<AssetFormPage />)

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
    })

    it('handles error when loading asset data', async () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {})
      mockedAssetService.getAsset.mockRejectedValue(
        new Error('加载失败')
      )

      renderWithProviders(<AssetFormPage />)

      await waitFor(() => {
        expect(screen.getByText('加载失败')).toBeInTheDocument()
      })

      expect(screen.getByText('无法加载资产数据，请稍后重试')).toBeInTheDocument()
      
      consoleError.mockRestore()
    })

    it('handles API errors during update', async () => {
      mockedAssetService.getAsset.mockResolvedValue(mockAssetData.basic)
      mockedAssetService.updateAsset.mockRejectedValue(
        new Error('更新失败')
      )

      renderWithProviders(<AssetFormPage />)

      await waitFor(() => {
        expect(screen.getByDisplayValue('测试资产')).toBeInTheDocument()
      })

      // Make a change and submit
      const propertyNameInput = screen.getByDisplayValue('测试资产')
      await user.clear(propertyNameInput)
      await user.type(propertyNameInput, '更新后的资产')

      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      await waitFor(() => {
        expect(message.error).toHaveBeenCalledWith(
          expect.stringContaining('更新失败')
        )
      })
    })
  })

  describe('Form Validation', () => {
    it('validates numeric fields correctly', async () => {
      renderWithProviders(<AssetFormPage />)

      // Enter invalid numeric value
      const areaInput = screen.getByLabelText(/实际物业面积/)
      await user.type(areaInput, 'invalid')

      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('请输入有效的数字')).toBeInTheDocument()
      })
    })

    it('validates area relationships correctly', async () => {
      renderWithProviders(<AssetFormPage />)

      // Set rented area larger than rentable area
      await user.type(screen.getByLabelText(/可出租面积/), '100')
      await user.type(screen.getByLabelText(/已出租面积/), '200')

      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('已出租面积不能大于可出租面积')).toBeInTheDocument()
      })
    })

    it('shows field help text when focused', async () => {
      renderWithProviders(<AssetFormPage />)

      const propertyNameInput = screen.getByLabelText(/物业名称/)
      await user.click(propertyNameInput)

      expect(screen.getByText('请输入完整的物业名称')).toBeInTheDocument()
    })
  })

  describe('Form Features', () => {
    it('shows conditional fields based on selections', async () => {
      renderWithProviders(<AssetFormPage />)

      // Select "出租" usage status
      const usageStatusSelect = screen.getByLabelText(/使用状态/)
      await user.click(usageStatusSelect)
      await user.click(screen.getByText('出租'))

      // Tenant name field should appear
      await waitFor(() => {
        expect(screen.getByLabelText(/承租方名称/)).toBeInTheDocument()
      })
    })

    it('calculates occupancy rate automatically', async () => {
      renderWithProviders(<AssetFormPage />)

      // Enter area values
      await user.type(screen.getByLabelText(/可出租面积/), '1000')
      await user.type(screen.getByLabelText(/已出租面积/), '750')

      // Occupancy rate should be calculated
      await waitFor(() => {
        expect(screen.getByDisplayValue('75.00%')).toBeInTheDocument()
      })
    })

    it('supports form reset functionality', async () => {
      renderWithProviders(<AssetFormPage />)

      // Fill in some data
      await user.type(screen.getByLabelText(/物业名称/), '测试资产')
      await user.type(screen.getByLabelText(/权属方/), '测试公司')

      // Reset form
      const resetButton = screen.getByRole('button', { name: /重置/ })
      await user.click(resetButton)

      // Fields should be cleared
      expect(screen.getByLabelText(/物业名称/)).toHaveValue('')
      expect(screen.getByLabelText(/权属方/)).toHaveValue('')
    })

    it('shows unsaved changes warning', async () => {
      renderWithProviders(<AssetFormPage />)

      // Make changes to form
      await user.type(screen.getByLabelText(/物业名称/), '测试资产')

      // Try to navigate away
      const cancelButton = screen.getByRole('button', { name: /取消/ })
      await user.click(cancelButton)

      // Should show confirmation dialog
      expect(screen.getByText('确认离开')).toBeInTheDocument()
      expect(screen.getByText('您有未保存的更改，确定要离开吗？')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels and ARIA attributes', () => {
      renderWithProviders(<AssetFormPage />)

      // Check for proper labeling
      const propertyNameInput = screen.getByLabelText(/物业名称/)
      expect(propertyNameInput).toHaveAttribute('aria-required', 'true')

      const ownershipEntityInput = screen.getByLabelText(/权属方/)
      expect(ownershipEntityInput).toHaveAttribute('aria-required', 'true')
    })

    it('supports keyboard navigation', async () => {
      renderWithProviders(<AssetFormPage />)

      const propertyNameInput = screen.getByLabelText(/物业名称/)
      propertyNameInput.focus()

      // Tab to next field
      await user.tab()
      expect(screen.getByLabelText(/权属方/)).toHaveFocus()

      // Tab to next field
      await user.tab()
      expect(screen.getByLabelText(/管理方/)).toHaveFocus()
    })

    it('announces form errors to screen readers', async () => {
      renderWithProviders(<AssetFormPage />)

      const submitButton = screen.getByRole('button', { name: /保存/ })
      await user.click(submitButton)

      await waitFor(() => {
        const errorMessage = screen.getByText('请输入物业名称')
        expect(errorMessage).toHaveAttribute('role', 'alert')
      })
    })
  })
})