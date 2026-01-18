/**
 * PDF导入历史记录标签页组件
 *
 * 展示所有导入历史记录
 */

import React from 'react';
import { Card, Button, Space, Typography, Tag } from 'antd';
import { HistoryOutlined } from '@ant-design/icons';
import { COLORS } from '@/styles/colorMap';
import type { ProcessingSession } from '@/types/enhancedPdfImport';

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
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <HistoryOutlined style={{ fontSize: 48, color: COLORS.textTertiary, marginBottom: 16 }} />
          <Title level={4} style={{ color: COLORS.textTertiary }}>
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
            style={{ marginBottom: 8 }}
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
