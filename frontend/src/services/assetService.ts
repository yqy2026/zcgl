import { apiClient } from './api'
import type {
  Asset,
  AssetSearchParams,
  AssetListResponse,
  AssetCreateRequest,
  AssetUpdateRequest,
  AssetHistory,
} from '@/types/asset'
import type { ApiResponse, PaginatedResponse } from '@/types/api'

export class AssetService {
  // 获取资产列表
  async getAssets(params?: AssetSearchParams): Promise<AssetListResponse> {
    const response = await apiClient.get<AssetListResponse>('/assets', {
      params: {
        ...params,
        page: params?.page || 1,
        limit: params?.limit || 20,
      },
    })
    return response.data || response as AssetListResponse
  }

  // 获取单个资产
  async getAsset(id: string): Promise<Asset> {
    const response = await apiClient.get<Asset>(`/assets/${id}`)
    return response.data || response as Asset
  }

  // 创建资产
  async createAsset(data: AssetCreateRequest): Promise<Asset> {
    const response = await apiClient.post<Asset>('/assets', data)
    return response.data || response as Asset
  }

  // 更新资产
  async updateAsset(id: string, data: AssetUpdateRequest): Promise<Asset> {
    const response = await apiClient.put<Asset>(`/assets/${id}`, data)
    return response.data || response as Asset
  }

  // 删除资产
  async deleteAsset(id: string): Promise<void> {
    await apiClient.delete(`/assets/${id}`)
  }

  // 批量删除资产
  async deleteAssets(ids: string[]): Promise<void> {
    await apiClient.post('/assets/batch-delete', { ids })
  }

  // 获取资产变更历史
  async getAssetHistory(
    assetId: string,
    page = 1,
    limit = 20,
    changeType?: string
  ): Promise<PaginatedResponse<AssetHistory>> {
    const response = await apiClient.get<PaginatedResponse<AssetHistory>>(
      `/assets/${assetId}/history`,
      {
        params: { page, limit, change_type: changeType },
      }
    )
    return response.data || response as PaginatedResponse<AssetHistory>
  }

  // 获取历史记录详情
  async getHistoryDetail(historyId: string): Promise<AssetHistory> {
    const response = await apiClient.get<AssetHistory>(`/history/${historyId}`)
    return response.data || response as AssetHistory
  }

  // 比较历史记录
  async compareHistory(historyId1: string, historyId2: string): Promise<any> {
    const response = await apiClient.get(
      `/history/compare/${historyId1}/${historyId2}`
    )
    return response.data || response
  }

  // 获取字段变更历史
  async getFieldHistory(
    assetId: string,
    fieldName: string,
    limit = 10
  ): Promise<any[]> {
    const response = await apiClient.get(
      `/assets/${assetId}/field-history/${fieldName}`,
      { params: { limit } }
    )
    return response.data?.history || []
  }

  // 搜索资产
  async searchAssets(
    query: string,
    filters?: Record<string, any>
  ): Promise<AssetListResponse> {
    return this.getAssets({
      search: query,
      ...filters,
    })
  }

  // 获取资产统计信息
  async getAssetStats(filters?: Record<string, any>): Promise<any> {
    const response = await apiClient.get('/statistics/basic', {
      params: filters,
    })
    return response.data || response
  }

  // 获取权属方列表
  async getOwnershipEntities(): Promise<string[]> {
    const response = await apiClient.get('/assets/ownership-entities')
    return response.data || []
  }

  // 获取管理方列表
  async getManagementEntities(): Promise<string[]> {
    const response = await apiClient.get('/assets/management-entities')
    return response.data || []
  }

  // 获取业态类别列表
  async getBusinessCategories(): Promise<string[]> {
    const response = await apiClient.get('/assets/business-categories')
    return response.data || []
  }

  // 验证资产数据
  async validateAsset(data: AssetCreateRequest | AssetUpdateRequest): Promise<{
    valid: boolean
    errors: string[]
  }> {
    try {
      const response = await apiClient.post('/assets/validate', data)
      return {
        valid: true,
        errors: [],
      }
    } catch (error: any) {
      return {
        valid: false,
        errors: error.details?.map((d: any) => d.msg) || [error.message],
      }
    }
  }

  // 导出资产数据
  async exportAssets(
    filters?: Record<string, any>,
    options?: {
      format?: 'xlsx' | 'csv'
      includeHeaders?: boolean
      selectedFields?: string[]
    }
  ): Promise<any> {
    const response = await apiClient.post('/excel/export', {
      filters,
      format: options?.format || 'xlsx',
      include_headers: options?.includeHeaders !== false,
      selected_fields: options?.selectedFields,
    })
    return response.data || response
  }

  // 导出选中的资产
  async exportSelectedAssets(
    assetIds: string[],
    options?: {
      format?: 'xlsx' | 'csv'
      includeHeaders?: boolean
      selectedFields?: string[]
    }
  ): Promise<any> {
    const response = await apiClient.post('/excel/export-selected', {
      asset_ids: assetIds,
      format: options?.format || 'xlsx',
      include_headers: options?.includeHeaders !== false,
      selected_fields: options?.selectedFields,
    })
    return response.data || response
  }

  // 获取导出状态
  async getExportStatus(taskId: string): Promise<any> {
    const response = await apiClient.get(`/excel/export-status/${taskId}`)
    return response.data || response
  }

  // 获取导出历史
  async getExportHistory(): Promise<any[]> {
    const response = await apiClient.get('/excel/export-history')
    return response.data || []
  }

  // 删除导出记录
  async deleteExportRecord(id: string): Promise<void> {
    await apiClient.delete(`/excel/export-history/${id}`)
  }

  // 下载导出文件
  async downloadExportFile(downloadUrl: string): Promise<void> {
    // 创建一个隐藏的链接来触发下载
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = ''
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // 上传导入文件
  async uploadImportFile(file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await apiClient.post('/excel/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data || response
  }

  // 预览导入文件
  async previewImportFile(file: File): Promise<any[]> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await apiClient.post('/excel/preview', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data || []
  }

  // 下载导入模板
  async downloadImportTemplate(): Promise<void> {
    const response = await apiClient.get('/excel/template', {
      responseType: 'blob',
    })
    
    // 创建下载链接
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'asset_import_template.xlsx'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  // 获取导入状态
  async getImportStatus(importId: string): Promise<any> {
    const response = await apiClient.get(`/excel/import-status/${importId}`)
    return response.data || response
  }

  // 获取导入历史
  async getImportHistory(): Promise<any[]> {
    const response = await apiClient.get('/excel/import-history')
    return response.data || []
  }

  // 删除导入记录
  async deleteImportRecord(id: string): Promise<void> {
    await apiClient.delete(`/excel/import-history/${id}`)
  }

  // 获取出租率统计数据
  async getOccupancyRateStats(filters?: AssetSearchParams): Promise<any> {
    const response = await apiClient.get('/statistics/occupancy-rate', {
      params: filters,
    })
    return response.data || response
  }

  // 获取资产分布统计数据
  async getAssetDistributionStats(filters?: AssetSearchParams): Promise<any> {
    const response = await apiClient.get('/statistics/asset-distribution', {
      params: filters,
    })
    return response.data || response
  }

  // 获取面积统计数据
  async getAreaStatistics(filters?: AssetSearchParams): Promise<any> {
    const response = await apiClient.get('/statistics/area-statistics', {
      params: filters,
    })
    return response.data || response
  }

  // 获取综合统计数据
  async getComprehensiveStats(filters?: AssetSearchParams): Promise<any> {
    const response = await apiClient.get('/statistics/comprehensive', {
      params: filters,
    })
    return response.data || response
  }
}

// 导出服务实例
export const assetService = new AssetService()