import React from 'react';
import { List, Tag, Space, Button, Typography, Empty } from 'antd';
import {
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { COLORS } from '@/styles/colorMap';

const { Text } = Typography;

interface TodoItem {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  dueDate: string;
  status: 'pending' | 'completed';
}

interface TodoListProps {
  items: TodoItem[];
  loading?: boolean;
}

const TodoList: React.FC<TodoListProps> = ({ items, loading }) => {
  const getPriorityColor = (priority: string) => {
    const colorMap: Record<string, string> = {
      high: 'error',
      medium: 'warning',
      low: 'default',
    };
    return colorMap[priority] || 'default';
  };

  const getPriorityText = (priority: string) => {
    const textMap: Record<string, string> = {
      high: '高',
      medium: '中',
      low: '低',
    };
    return textMap[priority] || priority;
  };

  const handleComplete = (_id: string) => {
    // Task completed
  };

  if (loading === false && items.length === 0) {
    return <Empty description="暂无待办事项" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <List
      loading={loading}
      dataSource={items}
      renderItem={item => (
        <List.Item
          actions={[
            <Button
              key="complete"
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleComplete(item.id)}
            >
              完成
            </Button>,
          ]}
        >
          <List.Item.Meta
            avatar={
              <ExclamationCircleOutlined
                style={{
                  color:
                    item.priority === 'high'
                      ? COLORS.error
                      : item.priority === 'medium'
                        ? COLORS.warning
                        : COLORS.textTertiary,
                  fontSize: '16px',
                }}
              />
            }
            title={
              <Space>
                <span>{item.title}</span>
                <Tag color={getPriorityColor(item.priority)}>
                  {getPriorityText(item.priority)}优先级
                </Tag>
              </Space>
            }
            description={
              <div>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {item.description}
                </Text>
                <br />
                <Space style={{ marginTop: '4px' }}>
                  <ClockCircleOutlined style={{ color: COLORS.textTertiary }} />
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    截止日期: {item.dueDate}
                  </Text>
                </Space>
              </div>
            }
          />
        </List.Item>
      )}
    />
  );
};

export default TodoList;
