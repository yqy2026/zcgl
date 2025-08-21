import { vi, describe, it, expect, beforeEach } from 'vitest'
import { assetService } from '../assetService'
import type { Asset, AssetCreateRequest, AssetUpdateRequest } from '@/types/asset'

// Mock the API client
const mockApiClient = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  download: vi.fn(),
}

vi.mock('../api', () => ({
  apiClient: mockApiClient,
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

describe('AssetService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAssets', () => {
    it('fetches assets list with default parameters', async () => {
      const mockResponse = {
        data: [mockAsset],
        total: 1,
        page: 1,
        limit: 20,
        has_next: false,
        has_prev: false,
      }

      mockApiClient.get.mockResolvedValue({ data: mockResponse })

      const result = await assetService.getAssets()

      expect(mockApiClient.get).toHaveBeenCalledWith('/assets', {
        params: {
          page: 1,
          limit: 20,
        },
      })
      expect(result).toEqual(mockResponse)
    })

    it('fetches assets with search parameters', async () => {
      const searchParams = {
        search: '测试',
        ownership_status: '已确权',
        page: 2,
        limit: 50,
      }

      mockApiClient.get.mockResolvedValue({ data: [] })

      await assetService.getAssets(searchParams)

      expect(mockApiClient.get).toHaveBeenCalledWith('/assets', {
        params: searchParams,
      })
    })
  })

  describe('getAsset', () => {
    it('fetches single asset by id', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockAsset })

      const result = await assetService.getAsset('1')

      expect(mockApiClient.get).toHaveBeenCalledWith('/assets/1')
      expect(result).toEqual(mockAsset)
    })
  })

  describe('createAsset', () => {
    it('creates new asset', async () => {
      const createData: AssetCreateRequest = {
        property_name: '新物业',
        ownership_entity: '新权属方',
        address: '新地址',
        ownership_status: '已确权',
        property_nature: '经营类',
        usage_status: '出租',
      }

      mockApiClient.post.mockResolvedValue({ data: mockAsset })

      const result = await assetService.createAsset(createData)

      expect(mockApiClient.post).toHaveBeenCalledWith('/assets', createData)
      expect(result).toEqual(mockAsset)
    })
  })

  describe('updateAsset', () => {
    it('updates existing asset', async () => {
      const updateData: AssetUpdateRequest = {
        property_name: '更新后的物业',
      }

      mockApiClient.put.mockResolvedValue({ data: mockAsset })

      const result = await assetService.updateAsset('1', updateData)

      expect(mockApiClient.put).toHaveBeenCalledWith('/assets/1', updateData)
      expect(result).toEqual(mockAsset)
    })
  })

  describe('deleteAsset', () => {
    it('deletes asset by id', async () => {
      mockApiClient.delete.mockResolvedValue({})

      await assetService.deleteAsset('1')

      expect(mockApiClient.delete).toHaveBeenCalledWith('/assets/1')
    })
  })

  describe('getAssetHistory', () => {
    it('fetches asset history with default parameters', async () => {
      const mockHistory = {
        data: [],
        total: 0,
        page: 1,
        limit: 20,
      }

      mockApiClient.get.mockResolvedValue({ data: mockHistory })

      const result = await assetService.getAssetHistory('1')

      expect(mockApiClient.get).toHaveBeenCalledWith('/assets/1/history', {
        params: { page: 1, limit: 20, change_type: undefined },
      })
      expect(result).toEqual(mockHistory)
    })

    it('fetches asset history with filters', async () => {
      mockApiClient.get.mockResolvedValue({ data: { data: [] } })

      await assetService.getAssetHistory('1', 2, 50, 'update')

      expect(mockApiClient.get).toHaveBeenCalledWith('/assets/1/history', {
        params: { page: 2, limit: 50, change_type: 'update' },
      })
    })
  })

  describe('getOwnershipEntities', () => {
    it('fetches ownership entities list', async () => {
      const mockEntities = ['权属方1', '权属方2']
      mockApiClient.get.mockResolvedValue({ data: mockEntities })

      const result = await assetService.getOwnershipEntities()

      expect(mockApiClient.get).toHaveBeenCalledWith('/assets/ownership-entities')
      expect(result).toEqual(mockEntities)
    })
  })

  describe('exportAssets', () => {
    it('exports assets with default options', async () => {
      const mockExportResult = { file_url: 'http://example.com/file.xlsx' }
      mockApiClient.post.mockResolvedValue({ data: mockExportResult })

      const result = await assetService.exportAssets()

      expect(mockApiClient.post).toHaveBeenCalledWith('/excel/export', {
        filters: undefined,
        format: 'xlsx',
        include_headers: true,
        selected_fields: undefined,
      })
      expect(result).toEqual(mockExportResult)
    })

    it('exports assets with custom options', async () => {
      const filters = { ownership_status: '已确权' }
      const options = {
        format: 'csv' as const,
        includeHeaders: false,
        selectedFields: ['property_name', 'address'],
      }

      mockApiClient.post.mockResolvedValue({ data: {} })

      await assetService.exportAssets(filters, options)

      expect(mockApiClient.post).toHaveBeenCalledWith('/excel/export', {
        filters,
        format: 'csv',
        include_headers: false,
        selected_fields: ['property_name', 'address'],
      })
    })
  })

  describe('uploadImportFile', () => {
    it('uploads import file', async () => {
      const mockFile = new File(['content'], 'test.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const mockResult = { id: 'import-123', status: 'processing' }

      mockApiClient.post.mockResolvedValue({ data: mockResult })

      const result = await assetService.uploadImportFile(mockFile)

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/excel/import',
        expect.any(FormData),
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )
      expect(result).toEqual(mockResult)
    })
  })

  describe('downloadImportTemplate', () => {
    it('downloads import template', async () => {
      const mockBlob = new Blob(['template content'])
      mockApiClient.get.mockResolvedValue({ data: mockBlob })

      // Mock URL.createObjectURL and related methods
      const mockUrl = 'blob:http://localhost/template'
      global.URL.createObjectURL = vi.fn(() => mockUrl)
      global.URL.revokeObjectURL = vi.fn()

      // Mock document.createElement and appendChild/removeChild
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
      }
      const mockAppendChild = vi.fn()
      const mockRemoveChild = vi.fn()

      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)
      vi.spyOn(document.body, 'appendChild').mockImplementation(mockAppendChild)
      vi.spyOn(document.body, 'removeChild').mockImplementation(mockRemoveChild)

      await assetService.downloadImportTemplate()

      expect(mockApiClient.get).toHaveBeenCalledWith('/excel/template', {
        responseType: 'blob',
      })
      expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob)
      expect(mockLink.href).toBe(mockUrl)
      expect(mockLink.download).toBe('asset_import_template.xlsx')
      expect(mockLink.click).toHaveBeenCalled()
      expect(mockAppendChild).toHaveBeenCalledWith(mockLink)
      expect(mockRemoveChild).toHaveBeenCalledWith(mockLink)
      expect(global.URL.revokeObjectURL).toHaveBeenCalledWith(mockUrl)
    })
  })

  describe('getOccupancyRateStats', () => {
    it('fetches occupancy rate statistics', async () => {
      const mockStats = {
        overall_rate: 75.5,
        trend: 'up',
        by_property_nature: [],
      }

      mockApiClient.get.mockResolvedValue({ data: mockStats })

      const result = await assetService.getOccupancyRateStats()

      expect(mockApiClient.get).toHaveBeenCalledWith('/statistics/occupancy-rate', {
        params: undefined,
      })
      expect(result).toEqual(mockStats)
    })

    it('fetches occupancy rate statistics with filters', async () => {
      const filters = { property_nature: '经营类' }
      mockApiClient.get.mockResolvedValue({ data: {} })

      await assetService.getOccupancyRateStats(filters)

      expect(mockApiClient.get).toHaveBeenCalledWith('/statistics/occupancy-rate', {
        params: filters,
      })
    })
  })

  describe('validateAsset', () => {
    it('validates asset data successfully', async () => {
      const assetData: AssetCreateRequest = {
        property_name: '测试物业',
        ownership_entity: '测试权属方',
        address: '测试地址',
        ownership_status: '已确权',
        property_nature: '经营类',
        usage_status: '出租',
      }

      mockApiClient.post.mockResolvedValue({})

      const result = await assetService.validateAsset(assetData)

      expect(mockApiClient.post).toHaveBeenCalledWith('/assets/validate', assetData)
      expect(result).toEqual({
        valid: true,
        errors: [],
      })
    })

    it('handles validation errors', async () => {
      const assetData: AssetCreateRequest = {
        property_name: '',
        ownership_entity: '',
        address: '',
        ownership_status: '已确权',
        property_nature: '经营类',
        usage_status: '出租',
      }

      const validationError = {
        message: 'Validation failed',
        details: [
          { msg: '物业名称不能为空' },
          { msg: '权属方不能为空' },
        ],
      }

      mockApiClient.post.mockRejectedValue(validationError)

      const result = await assetService.validateAsset(assetData)

      expect(result).toEqual({
        valid: false,
        errors: ['物业名称不能为空', '权属方不能为空'],
      })
    })
  })

  describe('error handling', () => {
    it('handles API response without data property', async () => {
      const mockResponse = { id: '1', name: 'test' }
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await assetService.getAsset('1')

      expect(result).toEqual(mockResponse)
    })

    it('handles empty response arrays', async () => {
      mockApiClient.get.mockResolvedValue({ data: null })

      const result = await assetService.getOwnershipEntities()

      expect(result).toEqual([])
    })
  })
})