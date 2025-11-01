import React from 'react'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../../__tests__/utils/testUtils'
import AssetExport from '../AssetExport'
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

// Mock XLSX library
jest.mock('xlsx', () => ({
  utils: {
    json_to_sheet: jest.fn(() => ({})),
    book_new: jest.fn(() => ({})),
    book_append_sheet: jest.fn(),
  },
  write: jest.fn(() => new ArrayBuffer(1024)),
}))

describe('AssetExport', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
    
    // Mock URL.createObjectURL and revokeObjectURL
    global.URL.createObjectURL = jest.fn(() => 'mock-blob-url')
    global.URL.revokeObjectURL = jest.fn()
  })

  it('renders export component correctly', () => {
    renderWithProviders(<AssetExport />)

    expect(screen.getByText('导出资产数据')).toBeInTheDocument()
    expect(screen.getByText('选择导出格式')).toBeInTheDocument()
    expect(screen.getByText('选择导出范围')).toBeInTheDocument()
  })

  it('shows export format options', () => {
    renderWithProviders(<AssetExport />)

    expect(screen.getByLabelText('Excel (.xlsx)')).toBeInTheDocument()
    expect(screen.getByLabelText('CSV (.csv)')).toBeInTheDocument()
    expect(screen.getByLabelText('PDF (.pdf)')).toBeInTheDocument()
  })

  it('shows export range options', () => {
    renderWithProviders(<AssetExport />)

    expect(screen.getByLabelText('全部资产')).toBeInTheDocument()
    expect(screen.getByLabelText('当前筛选结果')).toBeInTheDocument()
    expect(screen.getByLabelText('自定义选择')).toBeInTheDocument()
  })

  it('exports all assets successfully', async () => {
    const mockAssets = mockAssetData.list(10)
    mockedAssetService.getAllAssets.mockResolvedValue({
      data: mockAssets,
      total: 10,
    })

    // Mock link click for download
    const mockClick = jest.fn()
    const mockLink = {
      href: '',
      download: '',
      click: mockClick,
    }
    jest.spyOn(document, 'createElement').mockReturnValue(mockLink)

    renderWithProviders(<AssetExport />)

    // Select Excel format (default)
    expect(screen.getByLabelText('Excel (.xlsx)')).toBeChecked()

    // Select all assets (default)
    expect(screen.getByLabelText('全部资产')).toBeChecked()

    // Click export button
    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    await waitFor(() => {
      expect(mockedAssetService.getAllAssets).toHaveBeenCalled()
    })

    expect(message.success).toHaveBeenCalledWith('导出成功')
    expect(mockClick).toHaveBeenCalled()
    expect(mockLink.download).toContain('资产数据')
    expect(mockLink.download).toContain('.xlsx')
  })

  it('exports filtered assets successfully', async () => {
    const mockFilteredAssets = mockAssetData.list(5)
    const filters = {
      property_nature: PropertyNature.COMMERCIAL_CLASS,
      ownership_status: OwnershipStatus.CONFIRMED,
    }

    mockedAssetService.searchAssets.mockResolvedValue({
      data: mockFilteredAssets,
      total: 5,
      page: 1,
      limit: 1000,
    })

    renderWithProviders(<AssetExport filters={filters} />)

    // Select filtered results
    const filteredRadio = screen.getByLabelText('当前筛选结果')
    await user.click(filteredRadio)

    // Click export button
    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    await waitFor(() => {
      expect(mockedAssetService.searchAssets).toHaveBeenCalledWith({
        ...filters,
        page: 1,
        limit: 1000,
      })
    })

    expect(message.success).toHaveBeenCalledWith('导出成功')
  })

  it('exports selected assets successfully', async () => {
    const selectedAssets = ['1', '2', '3']
    const mockSelectedAssetsData = mockAssetData.list(3)

    mockedAssetService.getAssetsByIds.mockResolvedValue(mockSelectedAssetsData)

    renderWithProviders(<AssetExport selectedAssetIds={selectedAssets} />)

    // Select custom selection
    const customRadio = screen.getByLabelText('自定义选择')
    await user.click(customRadio)

    expect(screen.getByText('已选择 3 项资产')).toBeInTheDocument()

    // Click export button
    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    await waitFor(() => {
      expect(mockedAssetService.getAssetsByIds).toHaveBeenCalledWith(selectedAssets)
    })

    expect(message.success).toHaveBeenCalledWith('导出成功')
  })

  it('exports CSV format correctly', async () => {
    const mockAssets = mockAssetData.list(5)
    mockedAssetService.getAllAssets.mockResolvedValue({
      data: mockAssets,
      total: 5,
    })

    const mockClick = jest.fn()
    const mockLink = {
      href: '',
      download: '',
      click: mockClick,
    }
    jest.spyOn(document, 'createElement').mockReturnValue(mockLink)

    renderWithProviders(<AssetExport />)

    // Select CSV format
    const csvRadio = screen.getByLabelText('CSV (.csv)')
    await user.click(csvRadio)

    // Click export button
    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('导出成功')
    })

    expect(mockLink.download).toContain('.csv')
  })

  it('exports PDF format correctly', async () => {
    const mockAssets = mockAssetData.list(5)
    mockedAssetService.getAllAssets.mockResolvedValue({
      data: mockAssets,
      total: 5,
    })

    const mockClick = jest.fn()
    const mockLink = {
      href: '',
      download: '',
      click: mockClick,
    }
    jest.spyOn(document, 'createElement').mockReturnValue(mockLink)

    renderWithProviders(<AssetExport />)

    // Select PDF format
    const pdfRadio = screen.getByLabelText('PDF (.pdf)')
    await user.click(pdfRadio)

    // Click export button
    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('导出成功')
    })

    expect(mockLink.download).toContain('.pdf')
  })

  it('shows loading state during export', async () => {
    mockedAssetService.getAllAssets.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({
        data: mockAssetData.list(10),
        total: 10,
      }), 1000))
    )

    renderWithProviders(<AssetExport />)

    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    expect(screen.getByText('导出中...')).toBeInTheDocument()
    expect(exportButton).toBeDisabled()
  })

  it('handles export errors gracefully', async () => {
    mockedAssetService.getAllAssets.mockRejectedValue(
      new Error('导出失败')
    )

    renderWithProviders(<AssetExport />)

    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith(
        expect.stringContaining('导出失败')
      )
    })
  })

  it('shows export progress for large datasets', async () => {
    const largeDataset = mockAssetData.list(1000)
    mockedAssetService.getAllAssets.mockImplementation(
      () => new Promise(resolve => {
        setTimeout(() => resolve({
          data: largeDataset,
          total: 1000,
        }), 500)
      })
    )

    renderWithProviders(<AssetExport />)

    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    // Should show progress bar for large datasets
    expect(screen.getByRole('progressbar')).toBeInTheDocument()

    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('导出成功')
    })
  })

  it('allows customizing export columns', async () => {
    renderWithProviders(<AssetExport />)

    // Click advanced options
    const advancedButton = screen.getByRole('button', { name: /高级选项/ })
    await user.click(advancedButton)

    // Should show column selection
    expect(screen.getByText('选择导出字段')).toBeInTheDocument()
    expect(screen.getByLabelText('物业名称')).toBeInTheDocument()
    expect(screen.getByLabelText('权属方')).toBeInTheDocument()
    expect(screen.getByLabelText('所在地址')).toBeInTheDocument()

    // Uncheck some columns
    const addressCheckbox = screen.getByLabelText('所在地址')
    await user.click(addressCheckbox)

    expect(addressCheckbox).not.toBeChecked()
  })

  it('validates export selection', async () => {
    renderWithProviders(<AssetExport selectedAssets={[]} />)

    // Select custom selection with no assets selected
    const customRadio = screen.getByLabelText('自定义选择')
    await user.click(customRadio)

    expect(screen.getByText('未选择任何资产')).toBeInTheDocument()

    // Export button should be disabled
    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    expect(exportButton).toBeDisabled()
  })

  it('shows export statistics', async () => {
    const mockAssets = mockAssetData.list(100)
    mockedAssetService.getAllAssets.mockResolvedValue({
      data: mockAssets,
      total: 100,
    })

    renderWithProviders(<AssetExport />)

    // Should show estimated export size
    expect(screen.getByText(/预计导出 100 条记录/)).toBeInTheDocument()
    expect(screen.getByText(/文件大小约/)).toBeInTheDocument()
  })

  it('supports export scheduling', async () => {
    renderWithProviders(<AssetExport />)

    // Click schedule export
    const scheduleButton = screen.getByRole('button', { name: /定时导出/ })
    await user.click(scheduleButton)

    // Should show scheduling options
    expect(screen.getByText('设置导出计划')).toBeInTheDocument()
    expect(screen.getByLabelText('每日')).toBeInTheDocument()
    expect(screen.getByLabelText('每周')).toBeInTheDocument()
    expect(screen.getByLabelText('每月')).toBeInTheDocument()
  })

  it('handles large file export with chunking', async () => {
    const largeDataset = mockAssetData.list(10000)
    
    // Mock chunked API calls
    mockedAssetService.getAllAssets
      .mockResolvedValueOnce({
        data: largeDataset.slice(0, 1000),
        total: 10000,
        hasMore: true,
      })
      .mockResolvedValueOnce({
        data: largeDataset.slice(1000, 2000),
        total: 10000,
        hasMore: true,
      })
      .mockResolvedValueOnce({
        data: largeDataset.slice(2000, 3000),
        total: 10000,
        hasMore: false,
      })

    renderWithProviders(<AssetExport />)

    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    // Should show chunking progress
    await waitFor(() => {
      expect(screen.getByText(/正在处理第 1 批数据/)).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('导出成功')
    })
  })

  it('cleans up blob URLs after export', async () => {
    const mockAssets = mockAssetData.list(5)
    mockedAssetService.getAllAssets.mockResolvedValue({
      data: mockAssets,
      total: 5,
    })

    const mockClick = jest.fn()
    const mockLink = {
      href: '',
      download: '',
      click: mockClick,
    }
    jest.spyOn(document, 'createElement').mockReturnValue(mockLink)

    renderWithProviders(<AssetExport />)

    const exportButton = screen.getByRole('button', { name: /开始导出/ })
    await user.click(exportButton)

    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('导出成功')
    })

    // Should clean up blob URL
    expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('mock-blob-url')
  })
})