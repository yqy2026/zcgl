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
import { Notification } from '@/types/notification';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

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
  const {
    data: notificationsData,
    isLoading,
  } = useQuery({
    queryKey: ['notifications', 'list'],
    queryFn: () => notificationService.getNotifications({ limit: 10 }),
    refetchInterval: 60000, // 每分钟刷新一次
  });

  // 获取未读数量
  const {
    data: unreadCountData,
  } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: () => notificationService.getUnreadCount(),
    refetchInterval: 30000, // 每30秒刷新一次
  });

  const unreadCount = unreadCountData ?? 0;
  const notifications = notificationsData?.items ?? [];

  // 标记已读
  const handleMarkAsRead = async (notificationId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationService.markAsRead(notificationId);
      // 刷新通知列表和未读数量
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    } catch (error) {
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
      console.error('标记全部已读失败:', error);
    }
  };

  // 删除通知
  const handleDelete = async (notificationId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationService.deleteNotification(notificationId);
      // 刷新通知列表和未读数量
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    } catch (error) {
      console.error('删除通知失败:', error);
    }
  };

  // 获取通知类型标签颜色
  const getNotificationTypeColor = (type: string) => {
    const colorMap: Record<string, string> = {
      'contract_expiring': 'orange',
      'contract_expired': 'red',
      'payment_overdue': 'red',
      'payment_due': 'orange',
      'approval_pending': 'blue',
      'system_notice': 'default',
    };
    return colorMap[type] || 'default';
  };

  // 获取通知类型文本
  const getNotificationTypeText = (type: string) => {
    const textMap: Record<string, string> = {
      'contract_expiring': '合同即将到期',
      'contract_expired': '合同已到期',
      'payment_overdue': '付款逾期',
      'payment_due': '付款到期提醒',
      'approval_pending': '审批待办',
      'system_notice': '系统通知',
    };
    return textMap[type] || '通知';
  };

  // 下拉菜单内容
  const content = (
    <div style={{ width: 400, maxHeight: 500, overflow: 'auto' }}>
      <div style={{ padding: '12px', borderBottom: '1px solid #f0f0f0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text strong>消息通知</Text>
          {unreadCount > 0 && (
            <Button
              type="link"
              size="small"
              onClick={handleMarkAllAsRead}
              style={{ padding: 0 }}
            >
              全部已读
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div style={{ padding: '40px', textAlign: 'center' }}>
          <Spin />
        </div>
      ) : notifications.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center' }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无通知"
          />
        </div>
      ) : (
        <List
          dataSource={notifications}
          renderItem={(notification: Notification) => (
            <List.Item
              key={notification.id}
              style={{
                padding: '12px',
                backgroundColor: notification.is_read ? 'transparent' : '#f6ffed',
                cursor: 'pointer',
              }}
              onClick={() => {
                if (!notification.is_read) {
                  handleMarkAsRead(notification.id, {} as any);
                }
              }}
            >
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {!notification.is_read && <div style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#52c41a' }} />}
                    <Tag color={getNotificationTypeColor(notification.type)}>
                      {getNotificationTypeText(notification.type)}
                    </Tag>
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {!notification.is_read && (
                      <Button
                        type="text"
                        size="small"
                        icon={<CheckOutlined />}
                        onClick={(e) => handleMarkAsRead(notification.id, e)}
                        style={{ padding: '0 4px' }}
                      />
                    )}
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => handleDelete(notification.id, e)}
                      style={{ padding: '0 4px' }}
                    />
                  </div>
                </div>
                <div style={{ marginBottom: 4 }}>
                  <Text strong={notification.priority === 'high' || notification.priority === 'urgent'}>
                    {notification.title}
                  </Text>
                </div>
                <div style={{ marginBottom: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {notification.content}
                  </Text>
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {new Date(notification.created_at).toLocaleString('zh-CN')}
                  </Text>
                </div>
              </div>
            </List.Item>
          )}
        />
      )}
      <div style={{ padding: '8px 12px', borderTop: '1px solid #f0f0f0', textAlign: 'center' }}>
        <Button
          type="link"
          size="small"
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
        <BellOutlined
          style={{ fontSize: 18, cursor: 'pointer' }}
          onClick={(e) => {
            e.preventDefault();
            setOpen(!open);
            onClick?.();
          }}
        />
      </Badge>
    </Dropdown>
  );
};

export default NotificationCenter;
