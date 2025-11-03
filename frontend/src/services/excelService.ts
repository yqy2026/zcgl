import { apiClient } from './api'
import type { ExcelImportResponse, ExcelExportRequest, ExcelExportResponse } from '@/types/api'

export class ExcelService {
  // 导入Excel文件
  async importExcel(
    file: File,
    sheetName = '物业总表',
    onProgress?: (progress: number) => void
  ): Promise<ExcelImportResponse> {
    const response = await apiClient.upload<ExcelImportResponse>(
      '/excel/import',
      file,
      onProgress,
      { sheet_name: sheetName }
    )
    return response.data!
  }

  // 导出Excel文件
  async exportExcel(request: ExcelExportRequest): Promise<ExcelExportResponse> {
    const response = await apiClient.post<ExcelExportResponse>('/excel/export', request)
    return response.data!
  }

  // 下载导出的文件
  async downloadExportFile(filename: string): Promise<void> {
  try {
      await apiClient.download(`/excel/download/${filename}`, filename)
  } catch (error) {
    console.error('操作失败:', error)
    throw new Error(error instanceof Error ? error.message : '操作失败')
  }

  // 获取导入模板
  async downloadTemplate(templateName = '资产导入模板.xlsx'): Promise<void> {
    await apiClient.download('/excel/import/template', templateName)
  }

  // 获取导入历史
  async getImportHistory(page = 1, limit = 20): Promise<any> {
    const response = await apiClient.get('/excel/import/history', {
      params: { page, limit },
    })
    return response.data || response
  }

  // 获取导出历史
  async getExportHistory(page = 1, limit = 20): Promise<any> {
    const response = await apiClient.get('/excel/export/history', {
      params: { page, limit },
    })
    return response.data || response
  }

  // 获取导入状态
  async getImportStatus(taskId: string): Promise<any> {
    const response = await apiClient.get(`/excel/import/status/${taskId}`)
    return response.data || response
  }

  // 获取导出状态
  async getExportStatus(taskId: string): Promise<any> {
    const response = await apiClient.get(`/excel/export/status/${taskId}`)
    return response.data || response
  }

  // 取消导入任务
  async cancelImport(taskId: string): Promise<void> {
    await apiClient.post(`/excel/import/cancel/${taskId}`)
  }

  // 取消导出任务
  async cancelExport(taskId: string): Promise<void> {
    await apiClient.post(`/excel/export/cancel/${taskId}`)
  }

  // 验证Excel文件
  async validateExcelFile(file: File): Promise<{
    valid: boolean
    errors: string[]
    warnings: string[]
  }> {
    try {
      const response = await apiClient.upload('/excel/validate', file)
      return response.data || {
        valid: true,
        errors: [],
        warnings: [],
      }
    } catch (error: any) {
      return {
        valid: false,
        errors: [error.message],
        warnings: [],
      }
    }
  }

  // 获取支持的文件格式
  async getSupportedFormats(): Promise<string[]> {
    const response = await apiClient.get('/excel/formats')
    return response.data || ['xlsx', 'xls', 'csv']
  }

  // 获取导入字段映射
  async getFieldMapping(): Promise<Record<string, string>> {
    const response = await apiClient.get('/excel/field-mapping')
    return response.data || {}
  }

  // 更新字段映射
  async updateFieldMapping(mapping: Record<string, string>): Promise<void> {
    await apiClient.post('/excel/field-mapping', { mapping })
  }
}

// 导出服务实例
export const excelService = new ExcelService()