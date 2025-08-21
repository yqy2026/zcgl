import React from 'react'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockFile } from '@/__tests__/utils/testUtils'
import AssetImport from '../AssetImport'
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

// Mock file reader
const mockFileReader = {
  readAsArrayBuffer: jest.fn(),
  result: null,
  onload: null,
  onerror: null,
}

global.FileReader = jest.fn(() => mockFileReader) as any

describe('AssetImport', () => {
  const user = userEvent.setup()
  const mockOnSuccess = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders import component correctly', () => {
    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    expect(screen.getByText('批量导入资产')).toBeInTheDocument()
    expect(screen.getByText('选择Excel文件')).toBeInTheDocument()
    expect(screen.getByText('下载模板')).toBeInTheDocument()
  })

  it('shows file upload area', () => {
    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    expect(screen.getByText('点击或拖拽文件到此区域上传')).toBeInTheDocument()
    expect(screen.getByText('支持扩展名：.xlsx, .xls')).toBeInTheDocument()
  })

  it('handles file selection correctly', async () => {
    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const file = createMockFile('test-assets.xlsx')
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    // Simulate file drop
    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    expect(screen.getByText('test-assets.xlsx')).toBeInTheDocument()
  })

  it('validates file type correctly', async () => {
    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const invalidFile = createMockFile('test.txt', 'text/plain')
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [invalidFile],
      },
    })

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('只支持Excel文件格式')
    })
  })

  it('validates file size correctly', async () => {
    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const largeFile = createMockFile('large-file.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 10 * 1024 * 1024) // 10MB
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [largeFile],
      },
    })

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('文件大小不能超过5MB')
    })
  })

  it('processes file upload successfully', async () => {
    const mockImportResult = {
      success: 10,
      failed: 0,
      errors: [],
    }

    mockedAssetService.importAssets.mockResolvedValue(mockImportResult)

    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const file = createMockFile('test-assets.xlsx')
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    // Simulate file selection
    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    // Mock FileReader success
    setTimeout(() => {
      mockFileReader.result = new ArrayBuffer(1024)
      if (mockFileReader.onload) {
        mockFileReader.onload({} as any)
      }
    }, 0)

    // Click import button
    const importButton = screen.getByRole('button', { name: /开始导入/ })
    await user.click(importButton)

    await waitFor(() => {
      expect(mockedAssetService.importAssets).toHaveBeenCalledWith(
        expect.any(ArrayBuffer)
      )
    })

    expect(message.success).toHaveBeenCalledWith('成功导入10条资产数据')
    expect(mockOnSuccess).toHaveBeenCalled()
  })

  it('handles import errors correctly', async () => {
    const mockImportResult = {
      success: 5,
      failed: 3,
      errors: [
        { row: 2, message: '物业名称不能为空' },
        { row: 4, message: '权属方不能为空' },
        { row: 6, message: '地址格式不正确' },
      ],
    }

    mockedAssetService.importAssets.mockResolvedValue(mockImportResult)

    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const file = createMockFile('test-assets.xlsx')
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    // Mock FileReader success
    setTimeout(() => {
      mockFileReader.result = new ArrayBuffer(1024)
      if (mockFileReader.onload) {
        mockFileReader.onload({} as any)
      }
    }, 0)

    const importButton = screen.getByRole('button', { name: /开始导入/ })
    await user.click(importButton)

    await waitFor(() => {
      expect(screen.getByText('导入完成，但有部分数据失败')).toBeInTheDocument()
    })

    expect(screen.getByText('成功：5条')).toBeInTheDocument()
    expect(screen.getByText('失败：3条')).toBeInTheDocument()
    expect(screen.getByText('第2行：物业名称不能为空')).toBeInTheDocument()
    expect(screen.getByText('第4行：权属方不能为空')).toBeInTheDocument()
    expect(screen.getByText('第6行：地址格式不正确')).toBeInTheDocument()
  })

  it('handles API errors during import', async () => {
    mockedAssetService.importAssets.mockRejectedValue(
      new Error('服务器错误')
    )

    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const file = createMockFile('test-assets.xlsx')
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    // Mock FileReader success
    setTimeout(() => {
      mockFileReader.result = new ArrayBuffer(1024)
      if (mockFileReader.onload) {
        mockFileReader.onload({} as any)
      }
    }, 0)

    const importButton = screen.getByRole('button', { name: /开始导入/ })
    await user.click(importButton)

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith(
        expect.stringContaining('导入失败')
      )
    })
  })

  it('downloads template file correctly', async () => {
    // Mock URL.createObjectURL
    const mockCreateObjectURL = jest.fn(() => 'mock-url')
    global.URL.createObjectURL = mockCreateObjectURL

    // Mock link click
    const mockClick = jest.fn()
    const mockLink = {
      href: '',
      download: '',
      click: mockClick,
    }
    jest.spyOn(document, 'createElement').mockReturnValue(mockLink as any)

    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const downloadButton = screen.getByRole('button', { name: /下载模板/ })
    await user.click(downloadButton)

    expect(mockCreateObjectURL).toHaveBeenCalled()
    expect(mockLink.download).toBe('资产导入模板.xlsx')
    expect(mockClick).toHaveBeenCalled()
  })

  it('shows loading state during import', async () => {
    mockedAssetService.importAssets.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({
        success: 10,
        failed: 0,
        errors: [],
      }), 1000))
    )

    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const file = createMockFile('test-assets.xlsx')
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    // Mock FileReader success
    setTimeout(() => {
      mockFileReader.result = new ArrayBuffer(1024)
      if (mockFileReader.onload) {
        mockFileReader.onload({} as any)
      }
    }, 0)

    const importButton = screen.getByRole('button', { name: /开始导入/ })
    await user.click(importButton)

    expect(screen.getByText('导入中...')).toBeInTheDocument()
    expect(importButton).toBeDisabled()
  })

  it('allows file removal before import', async () => {
    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const file = createMockFile('test-assets.xlsx')
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    expect(screen.getByText('test-assets.xlsx')).toBeInTheDocument()

    const removeButton = screen.getByRole('button', { name: /删除/ })
    await user.click(removeButton)

    expect(screen.queryByText('test-assets.xlsx')).not.toBeInTheDocument()
    expect(screen.getByText('点击或拖拽文件到此区域上传')).toBeInTheDocument()
  })

  it('shows import progress correctly', async () => {
    const mockImportResult = {
      success: 100,
      failed: 0,
      errors: [],
    }

    mockedAssetService.importAssets.mockImplementation(
      () => new Promise(resolve => {
        // Simulate progress updates
        setTimeout(() => resolve(mockImportResult), 500)
      })
    )

    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const file = createMockFile('test-assets.xlsx')
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    // Mock FileReader success
    setTimeout(() => {
      mockFileReader.result = new ArrayBuffer(1024)
      if (mockFileReader.onload) {
        mockFileReader.onload({} as any)
      }
    }, 0)

    const importButton = screen.getByRole('button', { name: /开始导入/ })
    await user.click(importButton)

    // Should show progress indicator
    expect(screen.getByRole('progressbar')).toBeInTheDocument()

    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('成功导入100条资产数据')
    })
  })

  it('handles file reader errors', async () => {
    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const file = createMockFile('corrupted-file.xlsx')
    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })

    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    // Mock FileReader error
    setTimeout(() => {
      if (mockFileReader.onerror) {
        mockFileReader.onerror({} as any)
      }
    }, 0)

    const importButton = screen.getByRole('button', { name: /开始导入/ })
    await user.click(importButton)

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('文件读取失败，请检查文件是否损坏')
    })
  })

  it('supports drag and drop functionality', async () => {
    renderWithProviders(<AssetImport onSuccess={mockOnSuccess} />)

    const uploadArea = screen.getByRole('button', { name: /选择Excel文件/ })
    const file = createMockFile('drag-drop-file.xlsx')

    // Simulate drag enter
    fireEvent.dragEnter(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    expect(uploadArea).toHaveClass('ant-upload-drag-hover')

    // Simulate drag leave
    fireEvent.dragLeave(uploadArea)

    expect(uploadArea).not.toHaveClass('ant-upload-drag-hover')

    // Simulate drop
    fireEvent.drop(uploadArea, {
      dataTransfer: {
        files: [file],
      },
    })

    expect(screen.getByText('drag-drop-file.xlsx')).toBeInTheDocument()
  })
})