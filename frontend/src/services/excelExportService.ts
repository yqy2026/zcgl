/**
 * Excel导出服务 - 导出相关功能
 *
 * @description 从 excelService.ts 拆分出的导出功能模块
 */

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { createLogger } from '@/utils/logger';
import type { ExcelExportRequest, ExcelExportResponse } from '@/types/api';
import type { ImportExportHistory, TaskStatusResponse } from '@/types/common';

import type { ExportTaskInfo, SupportedFormats, ExcelStatistics } from './excelService';

const logger = createLogger('ExcelExportService');

export class ExcelExportService {
  private readonly baseUrl = '/excel';

  // ==================== Excel导出功能 ====================

  /**
   * Excel数据导出
   */
  async exportExcel(request: ExcelExportRequest): Promise<ExcelExportResponse> {
    try {
      const result = await apiClient.post<ExcelExportResponse>(`${this.baseUrl}/export`, request, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

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
      const result = await apiClient.get<ExportTaskInfo>(`${this.baseUrl}/export/tasks/${taskId}`, {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

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

  // ==================== 导出历史记录 ====================

  /**
   * 获取导出历史记录
   */
  async getExportHistory(page = 1, pageSize = 20): Promise<ImportExportHistory[]> {
    try {
      const result = await apiClient.get<ImportExportHistory[]>(`${this.baseUrl}/export/history`, {
        params: { page, page_size: pageSize },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      return result.data ?? [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取导出历史失败', { error: enhancedError.message });
      return [];
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

  // ==================== 统计功能 ====================

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

  // ==================== 批量导出操作 ====================

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

  // ==================== 高级导出功能 ====================

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
export const excelExportService = new ExcelExportService();
