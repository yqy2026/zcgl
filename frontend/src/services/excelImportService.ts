/**
 * Excel导入服务 - 导入相关功能
 *
 * @description 从 excelService.ts 拆分出的导入功能模块
 */

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { createLogger } from '@/utils/logger';
import type { ExcelImportResponse } from '@/types/api';
import type { ImportExportHistory, TaskStatusResponse } from '@/types/common';

import type {
  ExcelValidationResult,
  FieldMapping,
  ImportTaskInfo,
  ExcelTemplate,
} from './excelService';

const logger = createLogger('ExcelImportService');

export class ExcelImportService {
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

      const result = await apiClient.post<ExcelImportResponse>(`${this.baseUrl}/import`, formData, {
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
      });

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
      const result = await apiClient.get<ImportTaskInfo>(`${this.baseUrl}/import/tasks/${taskId}`, {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

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

  // ==================== 导入历史记录 ====================

  /**
   * 获取导入历史记录
   */
  async getImportHistory(page = 1, pageSize = 20): Promise<ImportExportHistory[]> {
    try {
      const result = await apiClient.get<ImportExportHistory[]>(`${this.baseUrl}/import/history`, {
        params: { page, page_size: pageSize },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      return result.data ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取导入历史失败', { error: enhancedError.message });
      return [];
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

  // ==================== 批量导入操作 ====================

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

  // ==================== 导入性能分析 ====================

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

  // ==================== 高级导入功能 ====================

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
}

// 导出单例实例
export const excelImportService = new ExcelImportService();
