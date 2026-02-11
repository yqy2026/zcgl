import React from 'react';
import { List, Tag, Space, Button, Typography, Empty } from 'antd';
import {
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import styles from './TodoList.module.css';

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
  const getPriorityIconClassName = (priority: TodoItem['priority']) => {
    const classMap: Record<TodoItem['priority'], string> = {
      high: styles.priorityHigh,
      medium: styles.priorityMedium,
      low: styles.priorityLow,
    };
    return `${styles.priorityIcon} ${classMap[priority]}`;
  };

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
      className={styles.todoList}
      loading={loading}
      dataSource={items}
      renderItem={item => (
        <List.Item
          className={styles.todoItem}
          actions={[
            <Button
              key="complete"
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              className={styles.completeButton}
              onClick={() => handleComplete(item.id)}
            >
              完成
            </Button>,
          ]}
        >
          <List.Item.Meta
            avatar={
              <ExclamationCircleOutlined className={getPriorityIconClassName(item.priority)} />
            }
            title={
              <Space className={styles.titleRow}>
                <span
                  className={
                    item.status === 'completed'
                      ? `${styles.titleText} ${styles.completedTitle}`
                      : styles.titleText
                  }
                >
                  {item.title}
                </span>
                <Tag color={getPriorityColor(item.priority)} className={styles.priorityTag}>
                  {getPriorityText(item.priority)}优先级
                </Tag>
              </Space>
            }
            description={
              <div className={styles.descriptionBlock}>
                <Text type="secondary" className={styles.descriptionText}>
                  {item.description}
                </Text>
                <br />
                <Space className={styles.dueRow}>
                  <ClockCircleOutlined className={styles.dueIcon} />
                  <Text type="secondary" className={styles.dueText}>
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
