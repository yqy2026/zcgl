import { apiClient } from './api'
import type { BackupInfo, BackupListResponse } from '@/types/api'

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

export class BackupService {
  // 创建备份
  async createBackup(request: BackupRequest): Promise<BackupResponse> {
    const response = await apiClient.post<BackupResponse>('/backup/create', request)
    return response.data || response as BackupResponse
  }

  // 列出所有备份
  async listBackups(): Promise<BackupListResponse> {
    const response = await apiClient.get<BackupListResponse>('/backup/list')
    return response.data || response as BackupListResponse
  }

  // 获取备份详细信息
  async getBackupInfo(filename: string): Promise<{
    success: boolean
    message: string
    info?: BackupInfo
  }> {
    try {
      const response = await apiClient.get(`/backup/info/${filename}`)
      return response.data || response
    } catch (error) {
      console.error('获取备份信息失败:', error)
      throw new Error(error instanceof Error ? error.message : '获取备份信息失败')
    }
  }

  // 恢复备份
  async restoreBackup(request: RestoreRequest): Promise<RestoreResponse> {
    const response = await apiClient.post<RestoreResponse>('/backup/restore', request)
    return response.data || response as RestoreResponse
  }

  // 删除备份
  async deleteBackup(filename: string): Promise<{
    success: boolean
    message: string
    deleted: boolean
  }> {
    const response = await apiClient.delete(`/backup/${filename}`)
    return response.data || response
  }

  // 清理过期备份
  async cleanupOldBackups(): Promise<{
    success: boolean
    message: string
    deleted_count: number
  }> {
    const response = await apiClient.post('/backup/cleanup')
    return response.data || response
  }

  // 获取调度器状态
  async getSchedulerStatus(): Promise<{
    success: boolean
    message: string
    status: {
      is_running: boolean
      last_backup_time?: string
      auto_backup_enabled: boolean
      backup_interval_hours: number
      backup_retention_days: number
      max_backups: number
    }
  }> {
    const response = await apiClient.get('/backup/scheduler/status')
    return response.data || response
  }

  // 下载备份文件
  async downloadBackup(filename: string): Promise<void> {
    await apiClient.download(`/backup/download/${filename}`, filename)
  }

  // 验证备份文件
  async validateBackup(filename: string): Promise<{
    valid: boolean
    message: string
    details?: Record<string, unknown>
  }> {
    const response = await apiClient.post(`/backup/validate/${filename}`)
    return response.data || response
  }

  // 获取备份统计
  async getBackupStatistics(): Promise<{
    total_backups: number
    total_size: number
    oldest_backup: string
    newest_backup: string
    compression_ratio: number
  }> {
    const response = await apiClient.get('/backup/statistics')
    return response.data || response
  }
}

// 导出服务实例
export const backupService = new BackupService()