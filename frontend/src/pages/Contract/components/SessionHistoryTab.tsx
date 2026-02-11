/**
 * PDF导入历史记录标签页组件
 *
 * 展示所有导入历史记录
 */

import React from 'react';
import { Card, Button, Space, Typography, Tag } from 'antd';
import { HistoryOutlined } from '@ant-design/icons';
import type { ProcessingSession } from '@/types/pdfImport';
import styles from './SessionHistoryTab.module.css';

const { Title, Paragraph, Text } = Typography;

interface SessionHistoryTabProps {
  sessionHistory: ProcessingSession[];
  onSwitchToUpload: () => void;
}

export const SessionHistoryTab: React.FC<SessionHistoryTabProps> = ({
  sessionHistory,
  onSwitchToUpload,
}) => {
  if (sessionHistory.length === 0) {
    return (
      <Card title="导入历史记录">
        <div className={styles.emptyStateContainer}>
          <HistoryOutlined className={styles.emptyStateIcon} />
          <Title level={4} className={styles.emptyStateTitle}>
            暂无导入记录
          </Title>
          <Paragraph>开始上传PDF文件以创建导入记录。</Paragraph>
          <Button type="primary" onClick={onSwitchToUpload}>
            开始导入
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card title="导入历史记录">
      <div>
        {sessionHistory.map(session => (
          <Card
            key={session.sessionId}
            size="small"
            className={styles.historyItemCard}
            title={
              <Space>
                <Text>{session.fileInfo.name}</Text>
                <Tag
                  color={
                    session.status === 'completed'
                      ? 'green'
                      : session.status === 'ready'
                        ? 'blue'
                        : session.status === 'failed'
                          ? 'red'
                          : 'orange'
                  }
                >
                  {session.status === 'completed'
                    ? '已完成'
                    : session.status === 'ready'
                      ? '待确认'
                      : session.status === 'failed'
                        ? '失败'
                        : '其他'}
                </Tag>
              </Space>
            }
            extra={
              <Space>
                <Text type="secondary">进度: {session.progress}%</Text>
                <Button size="small" type="text">
                  查看详情
                </Button>
              </Space>
            }
          >
            <Text type="secondary">会话ID: {session.sessionId}</Text>
          </Card>
        ))}
      </div>
    </Card>
  );
};
