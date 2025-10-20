import { apiClient } from './api'
import {
  convertBackendToFrontend,
  convertFrontendToBackend,
  validateNumericFields
} from '@/utils/dataConversion'
import type {
  Asset,
  AssetSearchParams,
  AssetListResponse,
  AssetCreateRequest,
  AssetUpdateRequest,
  AssetHistory,
  SystemDictionary,
  AssetCustomField,
  CustomFieldValue,
} from '@/types/asset'
import type { ApiResponse, PaginatedResponse } from '@/types/api'

export class AssetService {
  // 获取资产列表
  async getAssets(params?: AssetSearchParams): Promise<AssetListResponse> {
    try {
      const response = await apiClient.get<AssetListResponse>('/assets', {
        params: {
          ...params,
          page: params?.page || 1,
          limit: params?.limit || 20,
        },
      })

      // 转换后端数据为前端格式
      if (response) {
        return convertBackendToFrontend<AssetListResponse>(response)
      }

      return response as AssetListResponse
    } catch (error) {
      console.error('获取资产列表失败:', error)
      // 抛出错误而不是返回空数据，让React Query能够正确处理错误状态
      throw new Error(error instanceof Error ? error.message : '获取资产列表失败')
    }
  }

  // 获取单个资产
  async getAsset(id: string): Promise<Asset> {
    const response = await apiClient.get<Asset>(`/assets/${id}`)
    return convertBackendToFrontend<Asset>(response.data || response as Asset)
  }

  // 创建资产
  async createAsset(data: AssetCreateRequest): Promise<Asset> {
    // 验证数值字段
    const validationErrors = validateNumericFields(data)
    if (validationErrors.length > 0) {
      throw new Error(`数据验证失败: ${validationErrors.join(', ')}`)
    }

    // 转换前端数据为后端格式
    const backendData = convertFrontendToBackend<AssetCreateRequest>(data)
    const response = await apiClient.post<Asset>('/assets', backendData)
    return convertBackendToFrontend<Asset>(response.data || response as Asset)
  }

  // 更新资产
  async updateAsset(id: string, data: AssetUpdateRequest): Promise<Asset> {
    // 验证数值字段
    const validationErrors = validateNumericFields(data)
    if (validationErrors.length > 0) {
      throw new Error(`数据验证失败: ${validationErrors.join(', ')}`)
    }

    // 转换前端数据为后端格式
    const backendData = convertFrontendToBackend<AssetUpdateRequest>(data)
    const response = await apiClient.put<Asset>(`/assets/${id}`, backendData)
    return convertBackendToFrontend<Asset>(response.data || response as Asset)
  }

  // 导出资产
  async exportAssets(params: { format: string, filters?: AssetSearchParams }): Promise<Blob> {
    const response = await apiClient.get('/excel/export', {
      params: {
        export_format: params.format,
        ...params.filters,
      },
      responseType: 'blob',
    })
    return response.data || response
  }

  // 导出选中资产
  async exportSelectedAssets(assetIds: string[], format: string): Promise<Blob> {
    const response = await apiClient.post(
      '/excel/export',
      assetIds,
      {
        params: {
          export_format: format,
        },
        responseType: 'blob',
      }
    )
    return response.data || (response as unknown as Blob)
  }

  // 导入资产
  async importAssets(file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post('/assets/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data || response
  }

  // 批量更新资产
  async batchUpdateAssets(data: { ids: string[], fields: Partial<AssetUpdateRequest> }): Promise<any> {
    const response = await apiClient.post('/assets/batch-update', data)
    return response.data || response
  }

  // 批量删除资产
  async deleteAssets(ids: string[]): Promise<void> {
    // 由于后端没有批量删除接口，逐个删除
    const deletePromises = ids.map(id => this.deleteAsset(id))
    await Promise.all(deletePromises)
  }

  // 删除单个资产
  async deleteAsset(id: string): Promise<void> {
    await apiClient.delete(`/assets/${id}`)
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
    try {
      const response = await apiClient.get('/assets/ownership-entities', {
        timeout: 3000 // 3秒超时
      })
      return response.data || []
    } catch (error) {
      console.warn('获取权属方列表失败:', error)
      throw error // 重新抛出错误，让上层处理
    }
  }

  
  // 获取业态类别列表
  async getBusinessCategories(): Promise<string[]> {
    try {
      const response = await apiClient.get('/assets/business-categories', {
        timeout: 3000
      })
      return response.data || []
    } catch (error) {
      console.warn('获取业态类别列表失败:', error)
      throw error
    }
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

  // 上传资产附件
  async uploadAssetAttachments(assetId: string, files: File[]): Promise<{ success: string[], failed: string[] }> {
    const formData = new FormData()
    files.forEach((file, index) => {
      formData.append(`file_${index}`, file)
    })

    const response = await apiClient.post(`/assets/${assetId}/attachments`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data || { success: [], failed: [] }
  }

  // 获取资产附件列表
  async getAssetAttachments(assetId: string): Promise<Array<{ id: string, name: string, size: number, url: string }>> {
    const response = await apiClient.get(`/assets/${assetId}/attachments`)
    return response.data || []
  }

  // 删除资产附件
  async deleteAssetAttachment(assetId: string, attachmentId: string): Promise<void> {
    await apiClient.delete(`/assets/${assetId}/attachments/${attachmentId}`)
  }

  // 获取出租率统计数据
  async getOccupancyRateStats(filters?: AssetSearchParams): Promise<any> {
    const response = await apiClient.get('/statistics/occupancy-rate/overall', {
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

  // 获取面积汇总统计数据
  async getAreaSummaryStats(): Promise<any> {
    const response = await apiClient.get('/statistics/area-summary')
    return response.data || response
  }

  // 获取财务汇总统计数据
  async getFinancialSummaryStats(): Promise<any> {
    const response = await apiClient.get('/statistics/financial-summary')
    return response.data || response
  }

  // 获取按类别出租率统计数据
  async getOccupancyRateByCategory(categoryField: string = 'business_category'): Promise<any> {
    const response = await apiClient.get('/statistics/occupancy-rate/by-category', {
      params: { category_field: categoryField }
    })
    return response.data || response
  }

  // 获取整体出租率统计数据
  async getOverallOccupancyRate(): Promise<any> {
    const response = await apiClient.get('/statistics/occupancy-rate/overall')
    return response.data || response
  }

  // ===== 系统字典管理 =====
  
  // 获取系统字典列表
  async getSystemDictionaries(dict_type?: string): Promise<SystemDictionary[]> {
    const response = await apiClient.get('/system-dictionaries', {
      params: dict_type ? { dict_type } : undefined,
    })
    return response.data || []
  }

  // 获取单个系统字典
  async getSystemDictionary(id: string): Promise<SystemDictionary> {
    const response = await apiClient.get(`/system-dictionaries/${id}`)
    return response.data
  }

  // 创建系统字典
  async createSystemDictionary(data: Omit<SystemDictionary, 'id' | 'created_at' | 'updated_at'>): Promise<SystemDictionary> {
    const response = await apiClient.post('/system-dictionaries', data)
    return response.data
  }

  // 更新系统字典
  async updateSystemDictionary(id: string, data: Partial<SystemDictionary>): Promise<SystemDictionary> {
    const response = await apiClient.put(`/system-dictionaries/${id}`, data)
    return response.data
  }

  // 删除系统字典
  async deleteSystemDictionary(id: string): Promise<void> {
    await apiClient.delete(`/system-dictionaries/${id}`)
  }

  // 批量更新系统字典
  async batchUpdateSystemDictionaries(updates: Array<{id: string, data: Partial<SystemDictionary>}>): Promise<SystemDictionary[]> {
    const response = await apiClient.post('/system-dictionaries/batch-update', { updates })
    return response.data || []
  }

  // 获取字典类型列表
  async getDictionaryTypes(): Promise<{ types: string[] }> {
    const response = await apiClient.get('/system-dictionaries/types/list')
    return response.data || { types: [] }
  }

  // ===== 自定义字段管理 =====

  // 获取资产自定义字段配置
  async getAssetCustomFields(assetId?: string): Promise<AssetCustomField[]> {
    const response = await apiClient.get('/asset-custom-fields', {
      params: assetId ? { asset_id: assetId } : undefined,
    })
    return response.data || []
  }

  // 获取单个自定义字段配置
  async getAssetCustomField(id: string): Promise<AssetCustomField> {
    const response = await apiClient.get(`/asset-custom-fields/${id}`)
    return response.data
  }

  // 创建自定义字段配置
  async createAssetCustomField(data: Omit<AssetCustomField, 'id' | 'created_at' | 'updated_at'>): Promise<AssetCustomField> {
    const response = await apiClient.post('/asset-custom-fields', data)
    return response.data
  }

  // 更新自定义字段配置
  async updateAssetCustomField(id: string, data: Partial<AssetCustomField>): Promise<AssetCustomField> {
    const response = await apiClient.put(`/asset-custom-fields/${id}`, data)
    return response.data
  }

  // 删除自定义字段配置
  async deleteAssetCustomField(id: string): Promise<void> {
    await apiClient.delete(`/asset-custom-fields/${id}`)
  }

  // 获取资产的自定义字段值
  async getAssetCustomFieldValues(assetId: string): Promise<CustomFieldValue[]> {
    const response = await apiClient.get(`/assets/${assetId}/custom-fields`)
    return response.data || []
  }

  // 更新资产的自定义字段值
  async updateAssetCustomFieldValues(assetId: string, values: CustomFieldValue[]): Promise<CustomFieldValue[]> {
    const response = await apiClient.put(`/assets/${assetId}/custom-fields`, { values })
    return response.data || []
  }

  // 批量设置自定义字段值
  async batchSetCustomFieldValues(updates: Array<{assetId: string, values: CustomFieldValue[]}>): Promise<void> {
    await apiClient.post('/assets/batch-custom-fields', { updates })
  }

  // ===== 数据字典相关的便捷方法 =====

  // 获取权属方字典
  async getOwnershipEntitiesFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries('ownership_status')
  }

  // 获取管理方字典
  async getManagementEntitiesFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries('management_entity')
  }

  // 获取业态类别字典
  async getBusinessCategoriesFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries('business_category')
  }

  // 获取资产状态字典
  async getAssetStatusFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries('property_nature')
  }

  // 获取权属类别字典
  async getOwnershipCategoryFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries('ownership_category')
  }

  // 获取租赁状态字典
  async getLeaseStatusFromDict(): Promise<SystemDictionary[]> {
    return this.getSystemDictionaries('contract_status')
  }

  // ===== 数据验证和转换 =====

  // 验证自定义字段值
  async validateCustomFieldValue(fieldId: string, value: any): Promise<{valid: boolean, error?: string}> {
    try {
      const response = await apiClient.post('/asset-custom-fields/validate', {
        field_id: fieldId,
        value: value,
      })
      return { valid: true }
    } catch (error: any) {
      return {
        valid: false,
        error: error.message || '验证失败',
      }
    }
  }

  // 获取字段选项（用于下拉框等）
  async getFieldOptions(fieldType: string, category?: string): Promise<Array<{label: string, value: any}>> {
    const response = await apiClient.get('/field-options', {
      params: { field_type: fieldType, category },
    })
    return response.data || []
  }
}

// 导出服务实例
export const assetService = new AssetService()