/**
 * BackupService 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BackupService, backupService } from '../backupService';

// Mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  }),
}));

// Mock ApiErrorHandler
vi.mock('../../utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: (error: unknown) => ({
      message: error instanceof Error ? error.message : '未知错误',
    }),
  },
}));

import { apiClient } from '@/api/client';

describe('BackupService', () => {
  let service: BackupService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new BackupService();
  });

  describe('createBackup', () => {
    it('成功创建备份', async () => {
      const mockResponse = {
        success: true,
        data: {
          success: true,
          message: '备份创建成功',
          backup_info: {
            filename: 'backup_2026-01-30.zip',
            size: 1024000,
            created_at: '2026-01-30T09:00:00Z',
          },
          async_backup: false,
        },
      };

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await service.createBackup({ description: '手动备份' });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/backup/create',
        { description: '手动备份' },
        expect.any(Object)
      );
      expect(result.success).toBe(true);
      expect(result.backup_info?.filename).toBe('backup_2026-01-30.zip');
    });

    it('创建备份失败时抛出错误', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '磁盘空间不足',
      });

      await expect(service.createBackup({})).rejects.toThrow('创建备份失败');
    });
  });

  describe('listBackups', () => {
    it('成功获取备份列表', async () => {
      const mockResponse = {
        success: true,
        data: {
          backups: [
            { filename: 'backup_1.zip', size: 1024 },
            { filename: 'backup_2.zip', size: 2048 },
          ],
          total: 2,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.listBackups();

      expect(apiClient.get).toHaveBeenCalledWith('/backup/list', expect.any(Object));
      expect(result).toBeDefined();
    });

    it('获取列表失败时抛出错误', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '权限不足',
      });

      await expect(service.listBackups()).rejects.toThrow('获取备份列表失败');
    });
  });

  describe('getBackupInfo', () => {
    it('成功获取备份详情', async () => {
      const mockResponse = {
        success: true,
        data: {
          success: true,
          message: '获取成功',
          info: {
            filename: 'backup_test.zip',
            size: 1024000,
            created_at: '2026-01-30T09:00:00Z',
          },
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getBackupInfo('backup_test.zip');

      expect(apiClient.get).toHaveBeenCalledWith(
        '/backup/info/backup_test.zip',
        expect.any(Object)
      );
      expect(result.info?.filename).toBe('backup_test.zip');
    });
  });

  describe('deleteBackup', () => {
    it('成功删除备份', async () => {
      const mockResponse = {
        success: true,
        data: {
          success: true,
          message: '删除成功',
          deleted: true,
        },
      };

      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse);

      const result = await service.deleteBackup('backup_old.zip');

      expect(apiClient.delete).toHaveBeenCalledWith('/backup/backup_old.zip', expect.any(Object));
      expect(result.deleted).toBe(true);
    });
  });

  describe('restoreBackup', () => {
    it('成功恢复备份', async () => {
      const mockResponse = {
        success: true,
        data: {
          success: true,
          message: '恢复成功',
          restored: true,
          safety_backup: 'safety_backup_123.zip',
        },
      };

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await service.restoreBackup({
        backup_filename: 'backup_test.zip',
        confirm: true,
      });

      expect(result.restored).toBe(true);
      expect(result.safety_backup).toBe('safety_backup_123.zip');
    });
  });

  describe('downloadBackup', () => {
    it('成功下载备份文件', async () => {
      const mockBlob = new Blob(['test'], { type: 'application/zip' });
      const mockResponse = {
        success: true,
        data: mockBlob,
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.downloadBackup('backup_test.zip');

      expect(result).toBeInstanceOf(Blob);
    });
  });

  describe('validateBackup', () => {
    it('成功验证备份文件', async () => {
      const mockResponse = {
        success: true,
        data: {
          valid: true,
          message: '备份文件有效',
        },
      };

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await service.validateBackup('backup_test.zip');

      expect(result.valid).toBe(true);
    });

    it('备份文件无效时返回 false', async () => {
      const mockResponse = {
        success: true,
        data: {
          valid: false,
          message: '备份文件损坏',
        },
      };

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await service.validateBackup('corrupted.zip');

      expect(result.valid).toBe(false);
    });
  });

  describe('getSchedulerStatus', () => {
    it('成功获取调度器状态', async () => {
      const mockResponse = {
        success: true,
        data: {
          success: true,
          message: '获取成功',
          status: {
            is_running: true,
            auto_backup_enabled: true,
            backup_interval_hours: 24,
            backup_retention_days: 30,
            max_backups: 10,
          },
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getSchedulerStatus();

      expect(result.status.is_running).toBe(true);
      expect(result.status.auto_backup_enabled).toBe(true);
    });
  });

  describe('batchDeleteBackups', () => {
    it('成功批量删除备份', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
        data: { success: true, deleted: true, message: '删除成功' },
      });

      const result = await service.batchDeleteBackups(['file1.zip', 'file2.zip']);

      expect(result.success).toBe(true);
      expect(result.deleted).toHaveLength(2);
    });

    it('部分删除失败', async () => {
      vi.mocked(apiClient.delete)
        .mockResolvedValueOnce({
          success: true,
          data: { success: true, deleted: true, message: '删除成功' },
        })
        .mockResolvedValueOnce({
          success: false,
          error: '文件不存在',
        });

      const result = await service.batchDeleteBackups(['file1.zip', 'file2.zip']);

      expect(result.success).toBe(false);
      expect(result.deleted).toHaveLength(1);
      expect(result.failed).toHaveLength(1);
    });
  });

  describe('checkBackupExists', () => {
    it('备份存在时返回 true', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { exists: true },
      });

      const result = await service.checkBackupExists('backup_test.zip');

      expect(result).toBe(true);
    });

    it('备份不存在时返回 false', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { exists: false },
      });

      const result = await service.checkBackupExists('nonexistent.zip');

      expect(result).toBe(false);
    });

    it('请求失败时返回 false', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('网络错误'));

      const result = await service.checkBackupExists('backup_test.zip');

      expect(result).toBe(false);
    });
  });

  describe('全局实例', () => {
    it('导出的 backupService 实例存在', () => {
      expect(backupService).toBeDefined();
      expect(backupService).toBeInstanceOf(BackupService);
    });
  });
});
