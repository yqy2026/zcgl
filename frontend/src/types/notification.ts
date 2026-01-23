/**
 * 通知相关类型定义
 */

export interface Notification {
  id: string;
  recipient_id: string;
  type: NotificationType;
  priority: NotificationPriority;
  title: string;
  content: string;
  related_entity_type?: string;
  related_entity_id?: string;
  is_read: boolean;
  read_at?: string;
  is_sent_wecom?: boolean;
  wecom_sent_at?: string;
  created_at: string;
  updated_at: string;
}

export enum NotificationType {
  CONTRACT_EXPIRING = 'contract_expiring',
  CONTRACT_EXPIRED = 'contract_expired',
  PAYMENT_OVERDUE = 'payment_overdue',
  PAYMENT_DUE = 'payment_due',
  APPROVAL_PENDING = 'approval_pending',
  SYSTEM_NOTICE = 'system_notice',
}

export enum NotificationPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

export interface NotificationQueryParams {
  page?: number;
  limit?: number;
  is_read?: boolean;
  type?: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
  unread_count: number;
}
