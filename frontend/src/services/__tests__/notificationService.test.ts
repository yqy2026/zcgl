/**
 * NotificationService 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { notificationService } from '../notificationService';

// Mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
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

describe('NotificationService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getNotifications', () => {
    it('成功获取通知列表', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [
            {
              id: 'notif_1',
              title: '系统通知',
              content: '您有新的待办事项',
              type: 'info',
              is_read: false,
              created_at: '2026-01-30T08:00:00Z',
            },
            {
              id: 'notif_2',
              title: '合同到期提醒',
              content: '合同将在7天后到期',
              type: 'warning',
              is_read: true,
              created_at: '2026-01-29T08:00:00Z',
            },
          ],
          total: 2,
          page: 1,
          page_size: 20,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await notificationService.getNotifications();

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it('带分页参数获取通知', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [],
          total: 0,
          page: 2,
          page_size: 10,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await notificationService.getNotifications({
        page: 2,
        page_size: 10,
      });

      expect(result.page).toBe(2);
    });

    it('获取失败时抛出错误', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '服务器错误',
      });

      await expect(notificationService.getNotifications()).rejects.toThrow('获取通知列表失败');
    });
  });

  describe('getUnreadCount', () => {
    it('成功获取未读数量', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { unread_count: 5 },
      });

      const result = await notificationService.getUnreadCount();

      expect(result).toBe(5);
    });

    it('获取失败时返回0', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('网络错误'));

      const result = await notificationService.getUnreadCount();

      expect(result).toBe(0);
    });

    it('API返回失败时返回0', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '获取失败',
      });

      // 这个方法会捕获错误并返回0
      const result = await notificationService.getUnreadCount();

      expect(result).toBe(0);
    });
  });

  describe('markAsRead', () => {
    it('成功标记通知为已读', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: null,
      });

      await expect(notificationService.markAsRead('notif_1')).resolves.not.toThrow();
    });

    it('标记失败时抛出错误', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '通知不存在',
      });

      await expect(notificationService.markAsRead('notif_invalid')).rejects.toThrow(
        '标记通知已读失败'
      );
    });
  });

  describe('markAllAsRead', () => {
    it('成功标记所有通知为已读', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: null,
      });

      await expect(notificationService.markAllAsRead()).resolves.not.toThrow();
    });

    it('标记失败时抛出错误', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '操作失败',
      });

      await expect(notificationService.markAllAsRead()).rejects.toThrow('标记所有通知已读失败');
    });
  });

  describe('deleteNotification', () => {
    it('成功删除通知', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: true,
        data: null,
      });

      await expect(notificationService.deleteNotification('notif_1')).resolves.not.toThrow();
    });

    it('删除失败时抛出错误', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: false,
        error: '通知不存在',
      });

      await expect(notificationService.deleteNotification('notif_invalid')).rejects.toThrow(
        '删除通知失败'
      );
    });

    it('网络错误时抛出错误', async () => {
      vi.mocked(apiClient.delete).mockRejectedValue(new Error('网络错误'));

      await expect(notificationService.deleteNotification('notif_1')).rejects.toThrow();
    });
  });

  describe('边界情况', () => {
    it('空通知列表', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
        },
      });

      const result = await notificationService.getNotifications();

      expect(result.items).toHaveLength(0);
      expect(result.total).toBe(0);
    });

    it('大量通知分页', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: Array(20).fill({
            id: 'notif',
            title: '通知',
            content: '内容',
          }),
          total: 100,
          page: 1,
          page_size: 20,
        },
      });

      const result = await notificationService.getNotifications({
        page: 1,
        page_size: 20,
      });

      expect(result.items).toHaveLength(20);
      expect(result.total).toBe(100);
    });
  });
});
