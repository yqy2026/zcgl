/**
 * Excel导入导出服务 - 统一响应处理版本
 *
 * @description Excel文件导入导出核心服务，提供完整的Excel数据处理功能
 * @author Claude Code
 */

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '../utils/responseExtractor';
import { createLogger } from '../utils/logger';
import type { ExcelImportResponse, ExcelExportRequest, ExcelExportResponse } from '@/types/api';
import type { ImportExportHistory, TaskStatusResponse, Filters } from '@/types/common';

const logger = createLogger('ExcelService');

// Excel文件验证结果接口
export interface ExcelValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

// Excel字段映射接口
export interface FieldMapping {
  [fieldName: string]: string;
}

// Excel导入任务信息接口
export interface ImportTaskInfo {
  taskId: string;
  fileName: string;
  fileSize: number;
  sheetName: string;
  totalRows: number;
  processedRows: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  startTime: string;
  endTime?: string;
  errors: string[];
  warnings: string[];
  importedRecords?: number;
  skippedRecords?: number;
  errorRecords?: number;
}

// Excel导出任务信息接口
export interface ExportTaskInfo {
  taskId: string;
  fileName: string;
  format: 'xlsx' | 'xls' | 'csv';
  filters?: Filters;
  totalRecords: number;
  exportedRecords: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  startTime: string;
  endTime?: string;
  downloadUrl?: string;
  errors: string[];
}

// Excel模板信息接口
export interface ExcelTemplate {
  name: string;
  displayName: string;
  description: string;
  fileUrl: string;
  fileSize: number;
  lastUpdated: string;
  requiredFields: string[];
  optionalFields: string[];
  fieldMappings: FieldMapping;
}

// Excel支持格式信息接口
export interface SupportedFormats {
  formats: string[];
  maxFileSize: number; // 字节
  allowedExtensions: string[];
  mimeTypes: string[];
}

// Excel统计信息接口
export interface ExcelStatistics {
  totalImports: number;
  totalExports: number;
  successfulImports: number;
  failedImports: number;
  successfulExports: number;
  failedExports: number;
  averageProcessingTime: number; // 秒
  totalDataRecords: number;
  lastImportTime?: string;
  lastExportTime?: string;
}

export class ExcelService {
  private readonly baseUrl = '/excel';

  // ==================== Excel导入功能 ====================

  /**
   * Excel文件导入
   */
  async importExcel(
    file: File,
    sheetName = '物业总表',
    onProgress?: (progress: number) => void
  ): Promise<ExcelImportResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('sheet_name', sheetName);

      const result = await apiClient.post<ExcelImportResponse>(
        `${this.baseUrl}/import`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: onProgress
            ? progressEvent => {
                if (progressEvent.total !== undefined && progressEvent.total > 0) {
                  const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                  onProgress(progress);
                }
              }
            : undefined,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`Excel导入失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取导入任务状态
   */
  async getImportStatus(taskId: string): Promise<TaskStatusResponse> {
    try {
      const result = await apiClient.get<TaskStatusResponse>(
        `${this.baseUrl}/import/status/${taskId}`,
        {
          cache: false, // 需要实时状态
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取导入状态失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取导入任务详细信息
   */
  async getImportTaskInfo(taskId: string): Promise<ImportTaskInfo> {
    try {
      const result = await apiClient.get<ImportTaskInfo>(
        `${this.baseUrl}/import/tasks/${taskId}`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取导入任务详情失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 取消导入任务
   */
  async cancelImport(taskId: string): Promise<{ success: boolean; message: string }> {
    try {
      const result = await apiClient.post<{ success: boolean; message: string }>(
        `${this.baseUrl}/import/cancel/${taskId}`,
        {},
        {
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`取消导入任务失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 重试失败的导入任务
   */
  async retryImport(
    taskId: string
  ): Promise<{ success: boolean; message: string; newTaskId?: string }> {
    try {
      const result = await apiClient.post<{
        success: boolean;
        message: string;
        newTaskId?: string;
      }>(
        `${this.baseUrl}/import/retry/${taskId}`,
        {},
        {
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`重试导入任务失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== Excel导出功能 ====================

  /**
   * Excel数据导出
   */
  async exportExcel(request: ExcelExportRequest): Promise<ExcelExportResponse> {
    try {
      const result = await apiClient.post<ExcelExportResponse>(
        `${this.baseUrl}/export`,
        request,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`Excel导出失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取导出任务状态
   */
  async getExportStatus(taskId: string): Promise<TaskStatusResponse> {
    try {
      const result = await apiClient.get<TaskStatusResponse>(
        `${this.baseUrl}/export/status/${taskId}`,
        {
          cache: false, // 需要实时状态
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取导出状态失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取导出任务详细信息
   */
  async getExportTaskInfo(taskId: string): Promise<ExportTaskInfo> {
    try {
      const result = await apiClient.get<ExportTaskInfo>(
        `${this.baseUrl}/export/tasks/${taskId}`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取导出任务详情失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 取消导出任务
   */
  async cancelExport(taskId: string): Promise<{ success: boolean; message: string }> {
    try {
      const result = await apiClient.post<{ success: boolean; message: string }>(
        `${this.baseUrl}/export/cancel/${taskId}`,
        {},
        {
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`取消导出任务失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 下载导出文件
   */
  async downloadExportFile(filename: string, taskId?: string): Promise<void> {
    try {
      const url =
        taskId !== undefined && taskId !== ''
          ? `${this.baseUrl}/download/${filename}?task_id=${taskId}`
          : `${this.baseUrl}/download/${filename}`;
      const result = await apiClient.get<Blob>(url, {
        responseType: 'blob',
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

      if (!result.success) {
        throw new Error(`下载导出文件失败: ${result.error}`);
      }

      // 创建下载链接
      const downloadUrl = window.URL.createObjectURL(result.data!);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 文件验证与模板功能 ====================

  /**
   * 验证Excel文件
   */
  async validateExcelFile(file: File, sheetName?: string): Promise<ExcelValidationResult> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (sheetName !== undefined && sheetName !== '') {
        formData.append('sheet_name', sheetName);
      }

      const result = await apiClient.post<ExcelValidationResult>(
        `${this.baseUrl}/validate`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`Excel文件验证失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      // 对于验证错误，返回默认错误结果而不是抛出异常
      return {
        valid: false,
        errors: [enhancedError.message],
        warnings: [],
      };
    }
  }

  /**
   * 下载Excel导入模板
   */
  async downloadTemplate(templateName = '资产导入模板.xlsx'): Promise<void> {
    try {
      const result = await apiClient.get<Blob>(`${this.baseUrl}/import/template`, {
        params: { template_name: templateName },
        responseType: 'blob',
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

      if (!result.success) {
        throw new Error(`下载导入模板失败: ${result.error}`);
      }

      // 创建下载链接
      const downloadUrl = window.URL.createObjectURL(result.data!);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = templateName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取可用的Excel模板列表
   */
  async getAvailableTemplates(): Promise<ExcelTemplate[]> {
    try {
      const result = await apiClient.get<ExcelTemplate[]>(`${this.baseUrl}/templates`, {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取Excel模板列表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取Excel模板列表失败', { error: enhancedError.message });
      return [];
    }
  }

  // ==================== 历史记录功能 ====================

  /**
   * 获取导入历史记录
   */
  async getImportHistory(page = 1, limit = 20): Promise<ImportExportHistory[]> {
    try {
      const result = await apiClient.get<ImportExportHistory[]>(
        `${this.baseUrl}/import/history`,
        {
          params: { page, limit },
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      return result.data ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取导入历史失败', { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取导出历史记录
   */
  async getExportHistory(page = 1, limit = 20): Promise<ImportExportHistory[]> {
    try {
      const result = await apiClient.get<ImportExportHistory[]>(
        `${this.baseUrl}/export/history`,
        {
          params: { page, limit },
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      return result.data ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取导出历史失败', { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取所有历史记录
   */
  async getAllHistory(
    page = 1,
    limit = 20
  ): Promise<{
    items: ImportExportHistory[];
    total: number;
    page: number;
    pageSize: number;
  }> {
    try {
      const result = await apiClient.get<{
        items: ImportExportHistory[];
        total: number;
        page: number;
        pageSize: number;
      }>(`${this.baseUrl}/history`, {
        params: { page, limit },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取历史记录失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 字段映射功能 ====================

  /**
   * 获取字段映射配置
   */
  async getFieldMapping(): Promise<FieldMapping> {
    try {
      const result = await apiClient.get<FieldMapping>(`${this.baseUrl}/field-mapping`, {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取字段映射失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取字段映射失败', { error: enhancedError.message });
      return {};
    }
  }

  /**
   * 更新字段映射配置
   */
  async updateFieldMapping(mapping: FieldMapping): Promise<{ success: boolean; message: string }> {
    try {
      const result = await apiClient.post<{ success: boolean; message: string }>(
        `${this.baseUrl}/field-mapping`,
        { mapping },
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`更新字段映射失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 重置字段映射为默认配置
   */
  async resetFieldMapping(): Promise<{
    success: boolean;
    message: string;
    defaultMapping: FieldMapping;
  }> {
    try {
      const result = await apiClient.post<{
        success: boolean;
        message: string;
        defaultMapping: FieldMapping;
      }>(
        `${this.baseUrl}/field-mapping/reset`,
        {},
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`重置字段映射失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 格式与配置功能 ====================

  /**
   * 获取支持的Excel格式
   */
  async getSupportedFormats(): Promise<SupportedFormats> {
    try {
      const result = await apiClient.get<SupportedFormats>(`${this.baseUrl}/formats`, {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取支持格式失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取支持格式失败', { error: enhancedError.message });
      // 返回默认格式
      return {
        formats: ['xlsx', 'xls', 'csv'],
        maxFileSize: 50 * 1024 * 1024, // 50MB
        allowedExtensions: ['.xlsx', '.xls', '.csv'],
        mimeTypes: [
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'application/vnd.ms-excel',
          'text/csv',
        ],
      };
    }
  }

  /**
   * 检查文件格式是否支持
   */
  async isFormatSupported(
    filename: string,
    fileSize: number
  ): Promise<{
    supported: boolean;
    reason?: string;
    recommendedAction?: string;
  }> {
    try {
      const result = await apiClient.post<{
        supported: boolean;
        reason?: string;
        recommendedAction?: string;
      }>(
        `${this.baseUrl}/check-format`,
        { filename, file_size: fileSize },
        {
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`检查文件格式失败: ${result.error}`);
      }

      return result.data!;
    } catch {
      // 本地进行基本检查
      const extension = filename.split('.').pop()?.toLowerCase();
      const supportedExtensions = ['xlsx', 'xls', 'csv'];
      const maxFileSize = 50 * 1024 * 1024; // 50MB

      if (extension === undefined || extension === '' || !supportedExtensions.includes(extension)) {
        return {
          supported: false,
          reason: '不支持的文件格式',
          recommendedAction: '请使用.xlsx、.xls或.csv格式的文件',
        };
      }

      if (fileSize > maxFileSize) {
        return {
          supported: false,
          reason: '文件大小超过限制',
          recommendedAction: '请压缩文件或减少数据量后重新上传',
        };
      }

      return { supported: true };
    }
  }

  // ==================== 统计与分析功能 ====================

  /**
   * 获取Excel处理统计信息
   */
  async getExcelStatistics(): Promise<ExcelStatistics> {
    try {
      const result = await apiClient.get<ExcelStatistics>(`${this.baseUrl}/statistics`, {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取Excel统计失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取导入性能分析
   */
  async getImportPerformanceAnalysis(timeRange: number = 30): Promise<{
    periodDays: number;
    totalImports: number;
    successRate: number;
    averageProcessingTime: number;
    averageFileSize: number;
    performanceTrend: 'improving' | 'stable' | 'declining';
    recommendations: string[];
  }> {
    try {
      const result = await apiClient.get<{
        periodDays: number;
        totalImports: number;
        successRate: number;
        averageProcessingTime: number;
        averageFileSize: number;
        performanceTrend: 'improving' | 'stable' | 'declining';
        recommendations: string[];
      }>(`${this.baseUrl}/analytics/import-performance`, {
        params: { time_range: timeRange },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取导入性能分析失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 批量操作功能 ====================

  /**
   * 批量取消导入任务
   */
  async batchCancelImports(taskIds: string[]): Promise<{
    success: boolean;
    cancelled: string[];
    failed: Array<{ taskId: string; error: string }>;
  }> {
    const cancelled: string[] = [];
    const failed: Array<{ taskId: string; error: string }> = [];

    for (const taskId of taskIds) {
      try {
        const result = await this.cancelImport(taskId);
        if (result.success) {
          cancelled.push(taskId);
        } else {
          failed.push({ taskId, error: result.message });
        }
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        failed.push({ taskId, error: enhancedError.message });
      }
    }

    const totalTasks = taskIds.length;
    const cancelledCount = cancelled.length;

    return {
      success: cancelledCount === totalTasks,
      cancelled,
      failed,
    };
  }

  /**
   * 批量取消导出任务
   */
  async batchCancelExports(taskIds: string[]): Promise<{
    success: boolean;
    cancelled: string[];
    failed: Array<{ taskId: string; error: string }>;
  }> {
    const cancelled: string[] = [];
    const failed: Array<{ taskId: string; error: string }> = [];

    for (const taskId of taskIds) {
      try {
        const result = await this.cancelExport(taskId);
        if (result.success) {
          cancelled.push(taskId);
        } else {
          failed.push({ taskId, error: result.message });
        }
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        failed.push({ taskId, error: enhancedError.message });
      }
    }

    const totalTasks = taskIds.length;
    const cancelledCount = cancelled.length;

    return {
      success: cancelledCount === totalTasks,
      cancelled,
      failed,
    };
  }

  /**
   * 批量下载导出文件
   */
  async batchDownloadExports(fileInfos: Array<{ filename: string; taskId?: string }>): Promise<{
    success: boolean;
    downloaded: string[];
    failed: Array<{ filename: string; error: string }>;
  }> {
    const downloaded: string[] = [];
    const failed: Array<{ filename: string; error: string }> = [];

    for (const fileInfo of fileInfos) {
      try {
        await this.downloadExportFile(fileInfo.filename, fileInfo.taskId);
        downloaded.push(fileInfo.filename);
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        failed.push({ filename: fileInfo.filename, error: enhancedError.message });
      }
    }

    const totalFiles = fileInfos.length;
    const downloadedCount = downloaded.length;

    return {
      success: downloadedCount === totalFiles,
      downloaded,
      failed,
    };
  }

  // ==================== 高级功能 ====================

  /**
   * 预览Excel文件内容
   */
  async previewExcelFile(
    file: File,
    maxRows: number = 10
  ): Promise<{
    headers: string[];
    rows: string[][];
    totalRows: number;
    sheetNames: string[];
  }> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('max_rows', maxRows.toString());

      const result = await apiClient.post<{
        headers: string[];
        rows: string[][];
        totalRows: number;
        sheetNames: string[];
      }>(`${this.baseUrl}/preview`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`预览Excel文件失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 清理过期的导出文件
   */
  async cleanupExpiredFiles(expiredDays: number = 7): Promise<{
    success: boolean;
    message: string;
    cleanedFiles: number;
    freedSpace: number;
  }> {
    try {
      const result = await apiClient.post<{
        success: boolean;
        message: string;
        cleanedFiles: number;
        freedSpace: number;
      }>(
        `${this.baseUrl}/cleanup`,
        { expired_days: expiredDays },
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`清理过期文件失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取系统配置信息
   */
  async getSystemConfiguration(): Promise<{
    maxFileSize: number;
    allowedExtensions: string[];
    maxConcurrentTasks: number;
    taskTimeout: number;
    cleanupInterval: number;
    enableAutoCleanup: boolean;
  }> {
    try {
      const result = await apiClient.get<{
        maxFileSize: number;
        allowedExtensions: string[];
        maxConcurrentTasks: number;
        taskTimeout: number;
        cleanupInterval: number;
        enableAutoCleanup: boolean;
      }>(`${this.baseUrl}/configuration`, {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取系统配置失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

// 导出单例实例
export const excelService = new ExcelService();
