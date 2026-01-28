import React from 'react';
import { Modal, List, Tag, Space, Button, Typography, Popconfirm } from 'antd';
import { DeleteOutlined, HistoryOutlined } from '@ant-design/icons';
import type { SearchHistoryItem } from '@/hooks/useSearchHistory';

const { Text } = Typography;

interface SearchHistoryModalProps {
  visible: boolean;
  historyItems: SearchHistoryItem[];
  onApply: (item: SearchHistoryItem) => void;
  onDelete: (id: string) => void;
  onClear: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export const SearchHistoryModal: React.FC<SearchHistoryModalProps> = ({
  visible,
  historyItems,
  onApply,
  onDelete,
  onClear,
  onCancel,
}) => {
  const formatSearchParams = (item: SearchHistoryItem): string => {
    const params: string[] = [];

    if (item.conditions.search) {
      params.push(`关键词: ${item.conditions.search}`);
    }
    if (item.conditions.ownership_status) {
      params.push(`确权状态: ${item.conditions.ownership_status}`);
    }
    if (item.conditions.property_nature) {
      params.push(`物业性质: ${item.conditions.property_nature}`);
    }
    if (item.conditions.usage_status) {
      params.push(`使用状态: ${item.conditions.usage_status}`);
    }
    if (item.conditions.area_min || item.conditions.area_max) {
      params.push(
        `面积: ${item.conditions.area_min || 0}-${item.conditions.area_max || '∞'}㎡`
      );
    }
    if (item.conditions.created_start || item.conditions.created_end) {
      params.push(
        `时间: ${item.conditions.created_start || '开始'} - ${
          item.conditions.created_end || '结束'
        }`
      );
    }

    return params.length > 0 ? params.join(' | ') : '无条件';
  };

  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) {
      return '刚刚';
    } else if (minutes < 60) {
      return `${minutes}分钟前`;
    } else if (hours < 24) {
      return `${hours}小时前`;
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN');
    }
  };

  return (
    <Modal
      title={
        <Space>
          <HistoryOutlined />
          搜索历史
        </Space>
      }
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="clear" danger onClick={onClear} disabled={historyItems.length === 0}>
          清空历史
        </Button>,
        <Button key="close" onClick={onCancel}>
          关闭
        </Button>,
      ]}
      width={800}
    >
      {historyItems.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <HistoryOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
          <p style={{ color: '#999', marginTop: 16 }}>暂无搜索历史</p>
        </div>
      ) : (
        <List
          dataSource={historyItems}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Popconfirm
                  key="delete"
                  title="确定删除这条搜索历史吗？"
                  onConfirm={() => onDelete(item.id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    size="small"
                  >
                    删除
                  </Button>
                </Popconfirm>,
                <Button
                  key="apply"
                  type="primary"
                  size="small"
                  onClick={() => onApply(item)}
                >
                  应用
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>{item.name}</Text>
                    <Tag color="blue">{formatTime(item.createdAt)}</Tag>
                  </Space>
                }
                description={
                  <Text type="secondary" ellipsis={{ tooltip: formatSearchParams(item) }}>
                    {formatSearchParams(item)}
                  </Text>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Modal>
  );
};
