import React, { useState, useEffect } from 'react';
import {
    List,
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
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
    BellOutlined,
    CheckOutlined,
    DeleteOutlined,
    ExclamationCircleOutlined,
    ClockCircleOutlined,
    InfoCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import { COLORS } from '@/styles/colorMap';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

import { useNavigate } from 'react-router-dom';
import { notificationService } from '@/services/notificationService';
import { Notification, NotificationType, NotificationPriority } from '@/types/notification';

const { Title, Text, Paragraph } = Typography;

const NotificationCenter: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [activeTab, setActiveTab] = useState<string>('all');
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 10,
        total: 0,
    });

    // 加载通知列表
    const loadNotifications = async (page = 1, type?: string) => {
        setLoading(true);
        try {
            const response = await notificationService.getNotifications({
                page,
                limit: pagination.pageSize,
                type: type === 'all' ? undefined : type,
            });

            setNotifications(response.items);
            setPagination({
                ...pagination,
                current: response.page,
                total: response.total,
            });
        } catch (error) {
            console.error('加载通知失败:', error);
            MessageManager.error('加载通知列表失败');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadNotifications(1, activeTab);
    }, [activeTab]);

    // 处理Tab切换
    const handleTabChange = (key: string) => {
        setActiveTab(key);
        setPagination({ ...pagination, current: 1 });
    };

    // 标记为已读
    const handleMarkAsRead = async (id: string) => {
        try {
            await notificationService.markAsRead(id);
            MessageManager.success('已标记为已读');
            // 更新本地状态
            setNotifications(prev =>
                prev.map(item => (item.id === id ? { ...item, is_read: true, read_at: new Date().toISOString() } : item))
            );
            // 触发全局未读数更新（如果有Context的话）
        } catch (error) {
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
                    loadNotifications(1, activeTab);
                } catch (error) {
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
                    loadNotifications(pagination.current, activeTab);
                } catch (error) {
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
        if (item.related_entity_id) {
            if (item.related_entity_type === 'contract' ||
                item.type === NotificationType.CONTRACT_EXPIRING ||
                item.type === NotificationType.CONTRACT_EXPIRED) {
                navigate(`/rental/contracts/${item.related_entity_id}`);
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
                return <ClockCircleOutlined style={{ color: COLORS.warning }} />;
            case NotificationType.PAYMENT_OVERDUE:
                return <ExclamationCircleOutlined style={{ color: COLORS.error }} />;
            case NotificationType.PAYMENT_DUE:
                return <InfoCircleOutlined style={{ color: COLORS.primary }} />;
            case NotificationType.APPROVAL_PENDING:
                return <CheckOutlined style={{ color: COLORS.success }} />;
            default:
                return <BellOutlined style={{ color: COLORS.primary }} />;
        }
    };

    // 获取优先级标签
    const getPriorityTag = (priority: NotificationPriority) => {
        switch (priority) {
            case NotificationPriority.URGENT:
                return <Tag color="red">紧急</Tag>;
            case NotificationPriority.HIGH:
                return <Tag color="orange">重要</Tag>;
            case NotificationPriority.LOW:
                return <Tag color="blue">一般</Tag>;
            default:
                return null;
        }
    };

    return (
        <div style={{ padding: '24px' }}>
            <Card
                title={
                    <Space>
                        <BellOutlined />
                        <span>通知中心</span>
                    </Space>
                }
                extra={
                    <Button icon={<CheckOutlined />} onClick={handleMarkAllAsRead}>
                        全部已读
                    </Button>
                }
            >
                <Tabs
                    activeKey={activeTab}
                    onChange={handleTabChange}
                    items={[
                        { label: '全部消息', key: 'all' },
                        { label: '合同提醒', key: NotificationType.CONTRACT_EXPIRING },
                        { label: '支付提醒', key: NotificationType.PAYMENT_DUE },
                        { label: '待办审批', key: NotificationType.APPROVAL_PENDING },
                        { label: '系统通知', key: NotificationType.SYSTEM_NOTICE },
                    ]}
                />

                {loading ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Spin size="large" />
                    </div>
                ) : (
                    <List
                        dataSource={notifications}
                        pagination={{
                            ...pagination,
                            onChange: (page) => loadNotifications(page, activeTab),
                        }}
                        locale={{ emptyText: <Empty description="暂无通知" /> }}
                        renderItem={(item) => (
                            <List.Item
                                actions={[
                                    <Button
                                        key="read"
                                        type="text"
                                        size="small"
                                        disabled={item.is_read}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleMarkAsRead(item.id);
                                        }}
                                    >
                                        {item.is_read ? '已读' : '标为已读'}
                                    </Button>,
                                    <Button
                                        key="delete"
                                        type="text"
                                        danger
                                        size="small"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDelete(item.id);
                                        }}
                                    >
                                        删除
                                    </Button>,
                                ]}
                                style={{
                                    cursor: 'pointer',
                                    backgroundColor: item.is_read ? 'transparent' : COLORS.infoLight,
                                    padding: '12px 24px',
                                    borderRadius: '4px',
                                    marginBottom: '8px',
                                    transition: 'all 0.3s',
                                }}
                                onClick={() => handleItemClick(item)}
                            >
                                <List.Item.Meta
                                    avatar={
                                        <div
                                            style={{
                                                width: 40,
                                                height: 40,
                                                borderRadius: '50%',
                                                backgroundColor: COLORS.bgPrimary,
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                border: '1px solid ' + COLORS.borderLight,
                                            }}
                                        >
                                            {getIcon(item.type)}
                                        </div>
                                    }
                                    title={
                                        <Space>
                                            {!item.is_read && <Badge status="processing" />}
                                            <Text strong={!item.is_read}>{item.title}</Text>
                                            {getPriorityTag(item.priority)}
                                            <Text type="secondary" style={{ fontSize: '12px' }}>
                                                {dayjs(item.created_at).fromNow()}
                                            </Text>
                                        </Space>
                                    }
                                    description={
                                        <Paragraph
                                            ellipsis={{ rows: 2 }}
                                            style={{ margin: 0, color: item.is_read ? COLORS.textTertiary : COLORS.textPrimary }}
                                        >
                                            {item.content}
                                        </Paragraph>
                                    }
                                />
                            </List.Item>
                        )}
                    />
                )}
            </Card>
        </div>
    );
};

export default NotificationCenter;
