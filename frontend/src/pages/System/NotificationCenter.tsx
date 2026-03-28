import React, { useEffect, useCallback, useMemo, useState } from 'react';
import {
  Card,
  Typography,
  Tag,
  Button,
  Space,
  Empty,
  Tabs,
  Badge,
  Spin,
  Modal,
  Pagination,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  BellOutlined,
  CheckOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { notificationService } from '@/services/notificationService';
import PageContainer from '@/components/Common/PageContainer';
import styles from './NotificationCenter.module.css';
import {
  Notification,
  NotificationType,
  NotificationPriority,
  NotificationListResponse,
} from '@/types/notification';

const { Text, Paragraph } = Typography;

interface NotificationFilters {
  type: string;
}

type Tone = 'primary' | 'success' | 'warning' | 'error';

const PRIORITY_META_MAP: Record<
  NotificationPriority,
  {
    label: string;
    tone: Tone;
  }
> = {
  [NotificationPriority.URGENT]: { label: '紧急', tone: 'error' },
  [NotificationPriority.HIGH]: { label: '重要', tone: 'warning' },
  [NotificationPriority.NORMAL]: { label: '普通', tone: 'primary' },
  [NotificationPriority.LOW]: { label: '一般', tone: 'success' },
};

const TYPE_META_MAP: Record<
  NotificationType,
  {
    label: string;
    tone: Tone;
  }
> = {
  [NotificationType.CONTRACT_EXPIRING]: { label: '合同提醒', tone: 'warning' },
  [NotificationType.CONTRACT_EXPIRED]: { label: '合同到期', tone: 'error' },
  [NotificationType.PAYMENT_OVERDUE]: { label: '逾期提醒', tone: 'error' },
  [NotificationType.PAYMENT_DUE]: { label: '支付提醒', tone: 'primary' },
  [NotificationType.APPROVAL_PENDING]: { label: '待办审批', tone: 'warning' },
  [NotificationType.SYSTEM_NOTICE]: { label: '系统通知', tone: 'success' },
};

const NotificationCenter: React.FC = () => {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<NotificationFilters>({
    type: 'all',
  });
  const [paginationState, setPaginationState] = useState({
    current: 1,
    pageSize: 10,
  });

  const fetchNotifications = useCallback(async (): Promise<NotificationListResponse> => {
    return await notificationService.getNotifications({
      page: paginationState.current,
      page_size: paginationState.pageSize,
      type: filters.type === 'all' ? undefined : filters.type,
    });
  }, [filters.type, paginationState.current, paginationState.pageSize]);

  const {
    data: notificationsResponse,
    error: notificationsError,
    isLoading: isNotificationsLoading,
    isFetching: isNotificationsFetching,
    refetch: refetchNotifications,
  } = useQuery<NotificationListResponse>({
    queryKey: [
      'notification-list',
      paginationState.current,
      paginationState.pageSize,
      filters.type,
    ],
    queryFn: fetchNotifications,
    retry: 1,
  });

  useEffect(() => {
    if (notificationsError != null) {
      MessageManager.error('加载通知列表失败');
    }
  }, [notificationsError]);

  const notifications = notificationsResponse?.items ?? [];
  const unreadCount = notificationsResponse?.unread_count ?? 0;
  const loading = isNotificationsLoading || isNotificationsFetching;
  const pagination = useMemo(
    () => ({
      current: paginationState.current,
      pageSize: paginationState.pageSize,
      total: notificationsResponse?.total ?? 0,
    }),
    [notificationsResponse?.total, paginationState.current, paginationState.pageSize]
  );

  const refreshNotifications = useCallback(() => {
    void refetchNotifications();
  }, [refetchNotifications]);
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

  // 处理Tab切换
  const handleTabChange = useCallback((key: string) => {
    setFilters({ type: key });
    setPaginationState(prev => ({ ...prev, current: 1 }));
  }, []);

  const handlePageChange = useCallback((page: number, pageSize: number) => {
    setPaginationState({
      current: page,
      pageSize,
    });
  }, []);

  // 标记为已读
  const handleMarkAsRead = async (id: string) => {
    try {
      await notificationService.markAsRead(id);
      MessageManager.success('已标记为已读');
      refreshNotifications();
    } catch {
      MessageManager.error('操作失败');
    }
  };

  // 全部已读
  const handleMarkAllAsRead = () => {
    Modal.confirm({
      title: '确认操作',
      content: '确定要将所有通知标记为已读吗？',
      onOk: async () => {
        try {
          await notificationService.markAllAsRead();
          MessageManager.success('全部已读成功');
          setPaginationState(prev => ({ ...prev, current: 1 }));
          refreshNotifications();
        } catch {
          MessageManager.error('操作失败');
        }
      },
    });
  };

  // 删除通知
  const handleDelete = (id: string) => {
    Modal.confirm({
      title: '删除通知',
      content: '确定要删除这条通知吗？',
      okType: 'danger',
      onOk: async () => {
        try {
          await notificationService.deleteNotification(id);
          MessageManager.success('删除成功');
          refreshNotifications();
        } catch {
          MessageManager.error('删除失败');
        }
      },
    });
  };

  // 处理点击通知
  const handleItemClick = (item: Notification) => {
    if (!item.is_read) {
      handleMarkAsRead(item.id);
    }

    // 根据类型跳转
    if (item.related_entity_id != null) {
      if (
        item.related_entity_type === 'contract' ||
        item.type === NotificationType.CONTRACT_EXPIRING ||
        item.type === NotificationType.CONTRACT_EXPIRED
      ) {
        MessageManager.info('合同通知详情入口迁移中，请改从新 contract/contract-group 页面处理');
      } else if (item.related_entity_type === 'asset') {
        navigate(`/assets/${item.related_entity_id}`);
      }
    }
  };

  // 获取图标
  const getIcon = (type: NotificationType) => {
    switch (type) {
      case NotificationType.CONTRACT_EXPIRING:
      case NotificationType.CONTRACT_EXPIRED:
        return (
          <ClockCircleOutlined className={`${styles.notificationTypeIcon} ${styles.warningIcon}`} />
        );
      case NotificationType.PAYMENT_OVERDUE:
        return (
          <ExclamationCircleOutlined
            className={`${styles.notificationTypeIcon} ${styles.errorIcon}`}
          />
        );
      case NotificationType.PAYMENT_DUE:
        return (
          <InfoCircleOutlined className={`${styles.notificationTypeIcon} ${styles.infoIcon}`} />
        );
      case NotificationType.APPROVAL_PENDING:
        return <CheckOutlined className={`${styles.notificationTypeIcon} ${styles.successIcon}`} />;
      default:
        return <BellOutlined className={`${styles.notificationTypeIcon} ${styles.infoIcon}`} />;
    }
  };

  // 获取优先级标签
  const getPriorityTag = (priority: NotificationPriority) => {
    const meta = PRIORITY_META_MAP[priority] ?? PRIORITY_META_MAP[NotificationPriority.NORMAL];
    return (
      <Tag className={[styles.priorityTag, toneClassMap[meta.tone]].join(' ')}>{meta.label}</Tag>
    );
  };

  const getTypeTag = (type: NotificationType) => {
    const meta = TYPE_META_MAP[type] ?? TYPE_META_MAP[NotificationType.SYSTEM_NOTICE];
    return <Tag className={[styles.typeTag, toneClassMap[meta.tone]].join(' ')}>{meta.label}</Tag>;
  };

  return (
    <PageContainer title="通知中心" subTitle="集中查看业务提醒、系统通知与待办消息">
      <Card
        className={styles.notificationCard}
        title={
          <Space size={8} className={styles.headerTitle}>
            <Badge count={unreadCount} size="small">
              <BellOutlined className={styles.headerIcon} />
            </Badge>
            <span>通知中心</span>
            <Text type="secondary" className={styles.headerMeta}>
              共 {pagination.total} 条
            </Text>
          </Space>
        }
        extra={
          <Button
            icon={<CheckOutlined />}
            onClick={handleMarkAllAsRead}
            className={styles.headerActionButton}
            disabled={unreadCount === 0}
          >
            全部已读
          </Button>
        }
      >
        <Tabs
          activeKey={filters.type}
          onChange={handleTabChange}
          className={styles.tabs}
          items={[
            { label: '全部消息', key: 'all' },
            { label: '合同提醒', key: NotificationType.CONTRACT_EXPIRING },
            { label: '支付提醒', key: NotificationType.PAYMENT_DUE },
            { label: '待办审批', key: NotificationType.APPROVAL_PENDING },
            { label: '系统通知', key: NotificationType.SYSTEM_NOTICE },
          ]}
        />

        {loading ? (
          <div className={styles.loadingContainer}>
            <Spin size="large" />
          </div>
        ) : notifications.length === 0 ? (
          <div className={styles.notificationEmptyState}>
            <Empty description="暂无通知" />
          </div>
        ) : (
          <div className={styles.notificationList} role="list">
            {notifications.map(item => (
              <div key={item.id} role="listitem">
                <div
                  className={[
                    styles.notificationItem,
                    item.is_read ? '' : styles.notificationItemUnread,
                  ].join(' ')}
                  role="button"
                  tabIndex={0}
                  onClick={() => handleItemClick(item)}
                  onKeyDown={event => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      handleItemClick(item);
                    }
                  }}
                >
                  <div className={styles.notificationItemContent}>
                    <div className={styles.notificationMain}>
                      <div className={styles.notificationAvatar}>{getIcon(item.type)}</div>
                      <div className={styles.notificationCopy}>
                        <Space size={8} className={styles.notificationTitle}>
                          {item.is_read === false && (
                            <Tag className={[styles.statusTag, styles.tonePrimary].join(' ')}>
                              未读
                            </Tag>
                          )}
                          <Text strong={!item.is_read} className={styles.notificationTitleText}>
                            {item.title}
                          </Text>
                          {getTypeTag(item.type)}
                          {getPriorityTag(item.priority)}
                          <Text type="secondary" className={styles.notificationTime}>
                            {dayjs(item.created_at).fromNow()}
                          </Text>
                        </Space>
                        <Paragraph
                          ellipsis={{ rows: 2 }}
                          className={[
                            styles.notificationDescription,
                            item.is_read
                              ? styles.notificationDescriptionRead
                              : styles.notificationDescriptionUnread,
                          ].join(' ')}
                        >
                          {item.content}
                        </Paragraph>
                      </div>
                    </div>
                    <Space size={8} className={styles.notificationActions}>
                      <Button
                        type="text"
                        className={styles.listActionButton}
                        disabled={item.is_read}
                        onClick={e => {
                          e.stopPropagation();
                          handleMarkAsRead(item.id);
                        }}
                        aria-label={`标记通知 ${item.title} 为已读`}
                      >
                        {item.is_read ? '已读' : '标为已读'}
                      </Button>
                      <Button
                        type="text"
                        danger
                        className={styles.listActionButton}
                        onClick={e => {
                          e.stopPropagation();
                          handleDelete(item.id);
                        }}
                        aria-label={`删除通知 ${item.title}`}
                      >
                        删除
                      </Button>
                    </Space>
                  </div>
                </div>
              </div>
            ))}
            {pagination.total > pagination.pageSize && (
              <div className={styles.notificationPagination}>
                <Pagination
                  current={pagination.current}
                  pageSize={pagination.pageSize}
                  total={pagination.total}
                  onChange={handlePageChange}
                />
              </div>
            )}
          </div>
        )}
      </Card>
    </PageContainer>
  );
};

export default NotificationCenter;
