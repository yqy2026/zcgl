/**
 * 通知中心组件
 *
 * @description 显示用户通知列表的铃铛图标和下拉菜单
 */

import React, { useState } from 'react';
import { Badge, Dropdown, List, Empty, Spin, Button, Tag, Typography } from 'antd';
import { BellOutlined, CheckOutlined, DeleteOutlined } from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { notificationService } from '@/services/notificationService';
import { Notification, NotificationType } from '@/types/notification';
import { useNavigate } from 'react-router-dom';
import styles from './NotificationCenter.module.css';

const { Text } = Typography;

type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';

interface NotificationTypeMeta {
  label: string;
  tone: Tone;
}

const NOTIFICATION_TYPE_META_MAP: Record<NotificationType, NotificationTypeMeta> = {
  [NotificationType.CONTRACT_EXPIRING]: { label: '合同即将到期', tone: 'warning' },
  [NotificationType.CONTRACT_EXPIRED]: { label: '合同已到期', tone: 'error' },
  [NotificationType.PAYMENT_OVERDUE]: { label: '付款逾期', tone: 'error' },
  [NotificationType.PAYMENT_DUE]: { label: '付款到期提醒', tone: 'warning' },
  [NotificationType.APPROVAL_PENDING]: { label: '审批待办', tone: 'primary' },
  [NotificationType.SYSTEM_NOTICE]: { label: '系统通知', tone: 'neutral' },
};

interface NotificationCenterProps {
  onClick?: () => void;
}

/**
 * NotificationCenter - 通知中心组件
 *
 * 功能：
 * - 显示未读通知数量的铃铛图标
 * - 下拉显示通知列表
 * - 支持标记已读、删除通知
 */
const NotificationCenter: React.FC<NotificationCenterProps> = ({ onClick }) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  // 获取通知列表
  const { data: notificationsData, isLoading } = useQuery({
    queryKey: ['notifications', 'list'],
    queryFn: () => notificationService.getNotifications({ page_size: 10 }),
    refetchInterval: 60000, // 每分钟刷新一次
  });

  // 获取未读数量
  const { data: unreadCountData } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: () => notificationService.getUnreadCount(),
    refetchInterval: 30000, // 每30秒刷新一次
  });

  const unreadCount = unreadCountData ?? 0;
  const notifications = notificationsData?.items ?? [];

  // 标记已读
  const handleMarkAsRead = async (notificationId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await notificationService.markAsRead(notificationId);
      // 刷新通知列表和未读数量
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('标记已读失败:', error);
    }
  };

  // 标记全部已读
  const handleMarkAllAsRead = async () => {
    try {
      await notificationService.markAllAsRead();
      // 刷新通知列表和未读数量
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('标记全部已读失败:', error);
    }
  };

  // 删除通知
  const handleDelete = async (notificationId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await notificationService.deleteNotification(notificationId);
      // 刷新通知列表和未读数量
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('删除通知失败:', error);
    }
  };

  const getToneClassName = (tone: Tone): string => {
    if (tone === 'primary') {
      return styles.tonePrimary;
    }
    if (tone === 'success') {
      return styles.toneSuccess;
    }
    if (tone === 'warning') {
      return styles.toneWarning;
    }
    if (tone === 'error') {
      return styles.toneError;
    }
    return styles.toneNeutral;
  };

  const getNotificationTypeMeta = (type: string): NotificationTypeMeta => {
    const typedType = type as NotificationType;
    return NOTIFICATION_TYPE_META_MAP[typedType] ?? { label: '通知', tone: 'neutral' };
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      void handleMarkAsRead(notification.id);
    }
  };

  // 下拉菜单内容
  const content = (
    <div className={styles.panel}>
      <div className={styles.panelHeader}>
        <div className={styles.panelHeaderRow}>
          <Text strong>消息通知</Text>
          {unreadCount > 0 && (
            <Button
              type="link"
              size="small"
              onClick={handleMarkAllAsRead}
              className={styles.markAllButton}
              aria-label="将所有通知标记为已读"
            >
              全部已读
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className={styles.loadingState}>
          <Spin />
        </div>
      ) : notifications.length === 0 ? (
        <div className={styles.emptyState}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无通知" />
        </div>
      ) : (
        <List
          className={styles.notificationList}
          dataSource={notifications}
          renderItem={(notification: Notification) => (
            <List.Item
              key={notification.id}
              className={`${styles.notificationItem} ${
                notification.is_read ? styles.notificationRead : styles.notificationUnread
              }`}
              onClick={() => handleNotificationClick(notification)}
              role="button"
              tabIndex={0}
              onKeyDown={event => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  handleNotificationClick(notification);
                }
              }}
            >
              <div className={styles.notificationContent}>
                <div className={styles.notificationHeader}>
                  <div className={styles.notificationMeta}>
                    {!notification.is_read && (
                      <span className={styles.unreadDot} aria-hidden="true" />
                    )}
                    <Tag
                      className={`${styles.typeTag} ${getToneClassName(
                        getNotificationTypeMeta(notification.type).tone
                      )}`}
                    >
                      {getNotificationTypeMeta(notification.type).label}
                    </Tag>
                  </div>
                  <div className={styles.itemActions}>
                    {!notification.is_read && (
                      <Button
                        type="text"
                        icon={<CheckOutlined />}
                        onClick={e => handleMarkAsRead(notification.id, e)}
                        className={styles.itemActionButton}
                        aria-label="标记为已读"
                      />
                    )}
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={e => handleDelete(notification.id, e)}
                      className={`${styles.itemActionButton} ${styles.itemActionDanger}`}
                      aria-label="删除通知"
                    />
                  </div>
                </div>
                <div className={styles.notificationTitle}>
                  <Text
                    strong={notification.priority === 'high' || notification.priority === 'urgent'}
                  >
                    {notification.title}
                  </Text>
                </div>
                <div className={styles.notificationBody}>
                  <Text type="secondary" className={styles.notificationBodyText}>
                    {notification.content}
                  </Text>
                </div>
                <div className={styles.notificationFooter}>
                  <Text type="secondary" className={styles.notificationTime}>
                    {new Date(notification.created_at).toLocaleString('zh-CN')}
                  </Text>
                </div>
              </div>
            </List.Item>
          )}
        />
      )}
      <div className={styles.panelFooter}>
        <Button
          type="link"
          size="small"
          className={styles.viewAllButton}
          onClick={() => {
            setOpen(false);
            navigate('/system/notifications');
          }}
        >
          查看全部通知
        </Button>
      </div>
    </div>
  );

  return (
    <Dropdown
      open={open}
      onOpenChange={setOpen}
      popupRender={() => content}
      trigger={['click']}
      placement="bottomRight"
    >
      <Badge count={unreadCount} overflowCount={99}>
        <Button
          type="text"
          icon={<BellOutlined className={styles.bellIcon} />}
          className={styles.triggerButton}
          aria-label="通知中心"
          aria-expanded={open}
          onClick={() => {
            onClick?.();
          }}
        />
      </Badge>
    </Dropdown>
  );
};

export default NotificationCenter;
