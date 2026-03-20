/**
 * Excel导入导出服务 - 统一入口（Re-export Hub）
 *
 * @description 此文件为向后兼容的 re-export hub。
 * 实际实现已拆分到:
 *   - excelImportService.ts (导入功能)
 *   - excelExportService.ts (导出功能)
 *
 * 所有外部消费者可继续从此文件导入，无需修改。
 */

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import type { ExcelImportResponse, ExcelExportRequest, ExcelExportResponse } from '@/types/api';
import type { ImportExportHistory, TaskStatusResponse, Filters } from '@/types/common';

import { ExcelImportService, excelImportService } from './excelImportService';
import { ExcelExportService, excelExportService } from './excelExportService';

// ==================== 共享类型定义 ====================

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

// ==================== 组合服务类（向后兼容） ====================

/**
 * ExcelService 组合类 — 委托给 ExcelImportService 和 ExcelExportService
 *
 * 保持与原始 API 完全一致，所有方法签名不变。
 */
export class ExcelService {
  private readonly importSvc = excelImportService;
  private readonly exportSvc = excelExportService;
  private readonly baseUrl = '/excel';

  // ==================== 导入功能（委托） ====================

  importExcel(
    file: File,
    sheetName?: string,
    onProgress?: (progress: number) => void
  ): Promise<ExcelImportResponse> {
    return this.importSvc.importExcel(file, sheetName, onProgress);
  }

  getImportStatus(taskId: string): Promise<TaskStatusResponse> {
    return this.importSvc.getImportStatus(taskId);
  }

  getImportTaskInfo(taskId: string): Promise<ImportTaskInfo> {
    return this.importSvc.getImportTaskInfo(taskId);
  }

  cancelImport(taskId: string): Promise<{ success: boolean; message: string }> {
    return this.importSvc.cancelImport(taskId);
  }

  retryImport(
    taskId: string
  ): Promise<{ success: boolean; message: string; newTaskId?: string }> {
    return this.importSvc.retryImport(taskId);
  }

  validateExcelFile(file: File, sheetName?: string): Promise<ExcelValidationResult> {
    return this.importSvc.validateExcelFile(file, sheetName);
  }

  downloadTemplate(templateName?: string): Promise<void> {
    return this.importSvc.downloadTemplate(templateName);
  }

  getAvailableTemplates(): Promise<ExcelTemplate[]> {
    return this.importSvc.getAvailableTemplates();
  }

  getImportHistory(page?: number, pageSize?: number): Promise<ImportExportHistory[]> {
    return this.importSvc.getImportHistory(page, pageSize);
  }

  getFieldMapping(): Promise<FieldMapping> {
    return this.importSvc.getFieldMapping();
  }

  updateFieldMapping(mapping: FieldMapping): Promise<{ success: boolean; message: string }> {
    return this.importSvc.updateFieldMapping(mapping);
  }

  resetFieldMapping(): Promise<{
    success: boolean;
    message: string;
    defaultMapping: FieldMapping;
  }> {
    return this.importSvc.resetFieldMapping();
  }

  batchCancelImports(taskIds: string[]): Promise<{
    success: boolean;
    cancelled: string[];
    failed: Array<{ taskId: string; error: string }>;
  }> {
    return this.importSvc.batchCancelImports(taskIds);
  }

  getImportPerformanceAnalysis(timeRange?: number): Promise<{
    periodDays: number;
    totalImports: number;
    successRate: number;
    averageProcessingTime: number;
    averageFileSize: number;
    performanceTrend: 'improving' | 'stable' | 'declining';
    recommendations: string[];
  }> {
    return this.importSvc.getImportPerformanceAnalysis(timeRange);
  }

  previewExcelFile(
    file: File,
    maxRows?: number
  ): Promise<{
    headers: string[];
    rows: string[][];
    totalRows: number;
    sheetNames: string[];
  }> {
    return this.importSvc.previewExcelFile(file, maxRows);
  }

  // ==================== 导出功能（委托） ====================

  exportExcel(request: ExcelExportRequest): Promise<ExcelExportResponse> {
    return this.exportSvc.exportExcel(request);
  }

  getExportStatus(taskId: string): Promise<TaskStatusResponse> {
    return this.exportSvc.getExportStatus(taskId);
  }

  getExportTaskInfo(taskId: string): Promise<ExportTaskInfo> {
    return this.exportSvc.getExportTaskInfo(taskId);
  }

  cancelExport(taskId: string): Promise<{ success: boolean; message: string }> {
    return this.exportSvc.cancelExport(taskId);
  }

  downloadExportFile(filename: string, taskId?: string): Promise<void> {
    return this.exportSvc.downloadExportFile(filename, taskId);
  }

  getExportHistory(page?: number, pageSize?: number): Promise<ImportExportHistory[]> {
    return this.exportSvc.getExportHistory(page, pageSize);
  }

  getSupportedFormats(): Promise<SupportedFormats> {
    return this.exportSvc.getSupportedFormats();
  }

  isFormatSupported(
    filename: string,
    fileSize: number
  ): Promise<{
    supported: boolean;
    reason?: string;
    recommendedAction?: string;
  }> {
    return this.exportSvc.isFormatSupported(filename, fileSize);
  }

  getExcelStatistics(): Promise<ExcelStatistics> {
    return this.exportSvc.getExcelStatistics();
  }

  batchCancelExports(taskIds: string[]): Promise<{
    success: boolean;
    cancelled: string[];
    failed: Array<{ taskId: string; error: string }>;
  }> {
    return this.exportSvc.batchCancelExports(taskIds);
  }

  batchDownloadExports(fileInfos: Array<{ filename: string; taskId?: string }>): Promise<{
    success: boolean;
    downloaded: string[];
    failed: Array<{ filename: string; error: string }>;
  }> {
    return this.exportSvc.batchDownloadExports(fileInfos);
  }

  cleanupExpiredFiles(expiredDays?: number): Promise<{
    success: boolean;
    message: string;
    cleanedFiles: number;
    freedSpace: number;
  }> {
    return this.exportSvc.cleanupExpiredFiles(expiredDays);
  }

  getSystemConfiguration(): Promise<{
    maxFileSize: number;
    allowedExtensions: string[];
    maxConcurrentTasks: number;
    taskTimeout: number;
    cleanupInterval: number;
    enableAutoCleanup: boolean;
  }> {
    return this.exportSvc.getSystemConfiguration();
  }

  // ==================== 共享功能（保留在 hub 中） ====================

  /**
   * 获取所有历史记录
   */
  async getAllHistory(
    page = 1,
    pageSize = 20
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
        params: { page, page_size: pageSize },
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
}

// 导出单例实例
export const excelService = new ExcelService();

// Re-export 子模块类和实例，供直接使用
export { ExcelImportService, excelImportService } from './excelImportService';
export { ExcelExportService, excelExportService } from './excelExportService';
