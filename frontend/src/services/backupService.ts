/**
 * 备份服务 - 统一响应处理版本
 *
 * @description 数据备份和恢复核心服务，提供备份管理、恢复、调度等功能
 * @author Claude Code
 * @updated 2025-11-10
 */

import { enhancedApiClient } from '@/api/client';
import { ApiErrorHandler } from '../utils/responseExtractor';
import { createLogger } from '../utils/logger';
import type { BackupInfo, BackupListResponse } from '@/types/api';

const logger = createLogger('BackupService');

export interface BackupRequest {
  description?: string
  async_backup?: boolean
}

export interface RestoreRequest {
  backup_filename: string
  confirm: boolean
}

export interface BackupResponse {
  success: boolean
  message: string
  backup_info?: BackupInfo
  async_backup: boolean
}

export interface RestoreResponse {
  success: boolean
  message: string
  restored: boolean
  safety_backup?: string
}

export interface SchedulerStatus {
  is_running: boolean
  last_backup_time?: string
  auto_backup_enabled: boolean
  backup_interval_hours: number
  backup_retention_days: number
  max_backups: number
}

export interface BackupStatistics {
  total_backups: number
  total_size: number
  oldest_backup: string
  newest_backup: string
  compression_ratio: number
}

export class BackupService {
  // ==================== 备份管理 ====================

  /**
   * 创建备份
   */
  async createBackup(request: BackupRequest): Promise<BackupResponse> {
    try {
      const result = await enhancedApiClient.post<BackupResponse>(
        '/backup/create',
        request,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`创建备份失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 列出所有备份
   */
  async listBackups(): Promise<BackupListResponse> {
    try {
      const result = await enhancedApiClient.get<BackupListResponse>(
        '/backup/list',
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取备份列表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取备份详细信息
   */
  async getBackupInfo(filename: string): Promise<{
    success: boolean
    message: string
    info?: BackupInfo
  }> {
    try {
      const result = await enhancedApiClient.get<{
        success: boolean
        message: string
        info?: BackupInfo
      }>(
        `/backup/info/${filename}`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取备份信息失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 删除备份
   */
  async deleteBackup(filename: string): Promise<{
    success: boolean
    message: string
    deleted: boolean
  }> {
    try {
      const result = await enhancedApiClient.delete<{
        success: boolean
        message: string
        deleted: boolean
      }>(
        `/backup/${filename}`,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`删除备份失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 清理过期备份
   */
  async cleanupOldBackups(): Promise<{
    success: boolean
    message: string
    deleted_count: number
  }> {
    try {
      const result = await enhancedApiClient.post<{
        success: boolean
        message: string
        deleted_count: number
      }>(
        '/backup/cleanup',
        {},
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`清理过期备份失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 备份恢复 ====================

  /**
   * 恢复备份
   */
  async restoreBackup(request: RestoreRequest): Promise<RestoreResponse> {
    try {
      const result = await enhancedApiClient.post<RestoreResponse>(
        '/backup/restore',
        request,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`恢复备份失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 文件操作 ====================

  /**
   * 下载备份文件
   */
  async downloadBackup(filename: string): Promise<Blob> {
    try {
      const result = await enhancedApiClient.get<Blob>(
        `/backup/download/${filename}`,
        {
          responseType: 'blob',
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 }
        }
      );

      if (!result.success) {
        throw new Error(`下载备份文件失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 验证备份文件
   */
  async validateBackup(filename: string): Promise<{
    valid: boolean
    message: string
    details?: Record<string, unknown>
  }> {
    try {
      const result = await enhancedApiClient.post<{
        valid: boolean
        message: string
        details?: Record<string, unknown>
      }>(
        `/backup/validate/${filename}`,
        {},
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`验证备份文件失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 上传备份文件
   */
  async uploadBackup(file: File, description?: string): Promise<{
    success: boolean
    message: string
    backup_info?: BackupInfo
  }> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (description !== null && description !== undefined && description !== '') {
        formData.append('description', description);
      }

      const result = await enhancedApiClient.post<{
        success: boolean
        message: string
        backup_info?: BackupInfo
      }>(
        '/backup/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`上传备份文件失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 调度管理 ====================

  /**
   * 获取调度器状态
   */
  async getSchedulerStatus(): Promise<{
    success: boolean
    message: string
    status: SchedulerStatus
  }> {
    try {
      const result = await enhancedApiClient.get<{
        success: boolean
        message: string
        status: SchedulerStatus
      }>(
        '/backup/scheduler/status',
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取调度器状态失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新调度器配置
   */
  async updateSchedulerConfig(config: {
    auto_backup_enabled?: boolean
    backup_interval_hours?: number
    backup_retention_days?: number
    max_backups?: number
  }): Promise<{
    success: boolean
    message: string
    updated: boolean
  }> {
    try {
      const result = await enhancedApiClient.put<{
        success: boolean
        message: string
        updated: boolean
      }>(
        '/backup/scheduler/config',
        config,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`更新调度器配置失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 启动调度器
   */
  async startScheduler(): Promise<{
    success: boolean
    message: string
    started: boolean
  }> {
    try {
      const result = await enhancedApiClient.post<{
        success: boolean
        message: string
        started: boolean
      }>(
        '/backup/scheduler/start',
        {},
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`启动调度器失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 停止调度器
   */
  async stopScheduler(): Promise<{
    success: boolean
    message: string
    stopped: boolean
  }> {
    try {
      const result = await enhancedApiClient.post<{
        success: boolean
        message: string
        stopped: boolean
      }>(
        '/backup/scheduler/stop',
        {},
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`停止调度器失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 统计信息 ====================

  /**
   * 获取备份统计
   */
  async getBackupStatistics(): Promise<BackupStatistics> {
    try {
      const result = await enhancedApiClient.get<BackupStatistics>(
        '/backup/statistics',
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取备份统计失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取备份历史记录
   */
  async getBackupHistory(limit: number = 50): Promise<Array<{
    timestamp: string
    action: 'created' | 'deleted' | 'restored' | 'uploaded'
    filename: string
    description?: string
    status: 'success' | 'failed'
    message?: string
    size?: number
  }>> {
    try {
      const result = await enhancedApiClient.get<Array<{
        timestamp: string
        action: 'created' | 'deleted' | 'restored' | 'uploaded'
        filename: string
        description?: string
        status: 'success' | 'failed'
        message?: string
        size?: number
      }>>(
        '/backup/history',
        {
          params: { limit },
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取备份历史记录失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取备份历史记录失败', { error: enhancedError.message });
      return [];
    }
  }

  // ==================== 批量操作 ====================

  /**
   * 批量删除备份
   */
  async batchDeleteBackups(filenames: string[]): Promise<{
    success: boolean
    message: string
    deleted: string[]
    failed: Array<{ filename: string; error: string }>
  }> {
    const deleted: string[] = [];
    const failed: Array<{ filename: string; error: string }> = [];

    for (const filename of filenames) {
      try {
        const result = await this.deleteBackup(filename);
        if (result.success && result.deleted) {
          deleted.push(filename);
        } else {
          failed.push({ filename, error: result.message });
        }
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        failed.push({ filename, error: enhancedError.message });
      }
    }

    const totalFiles = filenames.length;
    const deletedCount = deleted.length;

    return {
      success: deletedCount === totalFiles,
      message: `成功删除 ${deletedCount}/${totalFiles} 个备份文件`,
      deleted,
      failed
    };
  }

  /**
   * 批量验证备份
   */
  async batchValidateBackups(filenames: string[]): Promise<{
    success: boolean
    message: string
    valid: string[]
    invalid: Array<{ filename: string; error: string }>
  }> {
    const valid: string[] = [];
    const invalid: Array<{ filename: string; error: string }> = [];

    for (const filename of filenames) {
      try {
        const result = await this.validateBackup(filename);
        if (result.valid) {
          valid.push(filename);
        } else {
          invalid.push({ filename, error: result.message });
        }
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        invalid.push({ filename, error: enhancedError.message });
      }
    }

    const totalFiles = filenames.length;
    const validCount = valid.length;

    return {
      success: validCount === totalFiles,
      message: `验证 ${validCount}/${totalFiles} 个备份文件有效`,
      valid,
      invalid
    };
  }

  // ==================== 高级功能 ====================

  /**
   * 检查备份文件是否存在
   */
  async checkBackupExists(filename: string): Promise<boolean> {
    try {
      const result = await enhancedApiClient.get<{ exists: boolean }>(
        `/backup/check/${filename}`,
        {
          cache: true,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        logger.warn(`检查备份文件存在性失败`, { error: result.error });
        return false;
      }

      return result.data!.exists;
    } catch (error) {
      logger.warn(`检查备份文件存在性失败`, { error });
      return false;
    }
  }

  /**
   * 获取备份存储使用情况
   */
  async getStorageUsage(): Promise<{
    total_space: number
    used_space: number
    available_space: number
    usage_percentage: number
    backup_count: number
  }> {
    try {
      const result = await enhancedApiClient.get<{
        total_space: number
        used_space: number
        available_space: number
        usage_percentage: number
        backup_count: number
      }>(
        '/backup/storage/usage',
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取存储使用情况失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 测试备份功能
   */
  async testBackup(): Promise<{
    success: boolean
    message: string
    test_backup?: string
  }> {
    try {
      const result = await enhancedApiClient.post<{
        success: boolean
        message: string
        test_backup?: string
      }>(
        '/backup/test',
        {},
        {
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`测试备份功能失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

// 导出服务实例
export const backupService = new BackupService();