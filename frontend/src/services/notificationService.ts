/**
 * 通知相关API服务
 */

import { enhancedApiClient } from '@/api/client';
import { ApiErrorHandler } from '../utils/responseExtractor';
import { API_ENDPOINTS } from '@/constants/api';
import {
  Notification,
  NotificationQueryParams,
  NotificationListResponse,
} from '../types/notification';

class NotificationService {
  /**
   * 获取通知列表
   */
  async getNotifications(params?: NotificationQueryParams): Promise<NotificationListResponse> {
    try {
      const result = await enhancedApiClient.get<NotificationListResponse>(
        API_ENDPOINTS.NOTIFICATION.LIST,
        {
          params,
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 1 },
        }
      );

      if (!result.success) {
        throw new Error(`获取通知列表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取未读通知数量
   */
  async getUnreadCount(): Promise<number> {
    try {
      const result = await enhancedApiClient.get<{ count: number }>(
        API_ENDPOINTS.NOTIFICATION.UNREAD_COUNT,
        {
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 1 },
        }
      );

      if (!result.success) {
        throw new Error(`获取未读通知数量失败: ${result.error}`);
      }

      return result.data!.count;
    } catch (error) {
      // 这里的错误可以忽略，返回0即可，避免影响主流程
      console.warn('获取未读通知数量失败', error);
      return 0;
    }
  }

  /**
   * 标记通知为已读
   */
  async markAsRead(id: string): Promise<void> {
    try {
      const result = await enhancedApiClient.post<void>(
        API_ENDPOINTS.NOTIFICATION.MARK_READ(id),
        {},
        {
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 1 },
        }
      );

      if (!result.success) {
        throw new Error(`标记通知已读失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 标记所有通知为已读
   */
  async markAllAsRead(): Promise<void> {
    try {
      const result = await enhancedApiClient.post<void>(
        API_ENDPOINTS.NOTIFICATION.MARK_ALL_READ,
        {},
        {
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 1 },
        }
      );

      if (!result.success) {
        throw new Error(`标记所有通知已读失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 删除通知
   */
  async deleteNotification(id: string): Promise<void> {
    try {
      const result = await enhancedApiClient.delete<void>(
        API_ENDPOINTS.NOTIFICATION.DELETE(id),
        {
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 1 },
        }
      );

      if (!result.success) {
        throw new Error(`删除通知失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

export const notificationService = new NotificationService();
